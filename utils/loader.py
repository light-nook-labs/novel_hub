"""Data loader — pandas-based dataset processing for load/dump pipelines.

Public API:
    load_jsonl(path) — read JSONL files into DataFrame
    load_csv(path) — read CSV file into DataFrame
    df_to_meta_list(df) — DataFrame → list[Meta] (validated)
    meta_list_to_df(meta_list) — list[Meta] → DataFrame
    normalize_df(df) — normalize DataFrame columns to proper types
    denormalize_df(df) — convert DataFrame back to JSONL/CSV format
    extract_authors(df) — extract unique authors
    extract_tags(df) — extract unique tags
    extract_contests(df) — extract unique contests
"""

from pathlib import Path

import pandas as pd

from .config import COVER_PREFIX, DEFAULT_COVER, TIMEZONE
from .logger import get_logger, log_time, progress
from .mappings import GENRE, PTYPE, STATUS
from .models import Meta

logger = get_logger(__name__)

# Fixed chunk size for JSONL/CSV files
CHUNK_SIZE = 20000

# Status variants → core values (from spider output)
STATUS_NORMALIZE = {
    "断更": "断更",
    "已完结": "已完结",
    "连载中": "连载中",
}


@log_time
def load_jsonl(path: str | Path) -> pd.DataFrame:
    """Read JSONL files into DataFrame.

    Validates that each file has exactly CHUNK_SIZE records (except the last file).

    Args:
        path: Path to JSONL file or directory containing meta_*.jsonl files.

    Returns:
        Combined DataFrame from all JSONL files.
    """
    path = Path(path)
    if path.is_dir():
        files = sorted(path.glob("meta_*.jsonl"))
        if not files:
            raise FileNotFoundError(f"No meta_*.jsonl files found in {path}")
        logger.info("Found %d JSONL files in %s", len(files), path)
        dfs = []
        for f in progress(files, desc="Loading JSONL"):
            df = pd.read_json(f, lines=True)
            _validate_chunk_size(f, len(df), len(files) > 1)
            dfs.append(df)
        return pd.concat(dfs, ignore_index=True)
    logger.info("Loading single JSONL: %s", path)
    return pd.read_json(path, lines=True)


def _validate_chunk_size(filepath: Path, count: int, multi_file: bool):
    """Validate that JSONL file has correct number of records.

    Args:
        filepath: Path to JSONL file.
        count: Number of records in file.
        multi_file: True if loading multiple files (enforces CHUNK_SIZE).
    """
    if not multi_file:
        return
    if count > CHUNK_SIZE:
        logger.warning(
            "%s has %d records (expected max %d)", filepath.name, count, CHUNK_SIZE
        )


@log_time
def load_csv(path: str | Path) -> pd.DataFrame:
    """Read CSV file into DataFrame.

    Args:
        path: Path to CSV file.

    Returns:
        DataFrame from CSV file.
    """
    logger.info("Loading CSV: %s", path)
    return pd.read_csv(path)


def compress_cover(url: str | None) -> str | None:
    """Compress cover URL to suffix, default cover → None.

    Args:
        url: Full cover URL or suffix.

    Returns:
        Compressed suffix or None for default cover.
    """
    if not url or pd.isna(url):
        return None
    url = str(url)
    if url.startswith(COVER_PREFIX):
        suffix = url[len(COVER_PREFIX) :]
    else:
        suffix = url
    if suffix == DEFAULT_COVER:
        return None
    return suffix


def expand_cover(suffix: str | None) -> str | None:
    """Expand cover suffix to full URL, None → None.

    Args:
        suffix: Compressed suffix or None.

    Returns:
        Full URL or None.
    """
    if not suffix or pd.isna(suffix):
        return None
    suffix = str(suffix)
    if suffix.startswith("http"):
        return suffix
    return COVER_PREFIX + suffix


@log_time
def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize DataFrame columns to proper types for database insertion.

    Converts Pydantic model field names (nid, author, genre, status, ptype)
    to Django model field names (id, author_id, genre_int, status_int, ptype_int).

    Args:
        df: Raw DataFrame from JSONL/CSV.

    Returns:
        Normalized DataFrame with proper dtypes.
    """
    df = df.copy()

    # 1. Rename nid → id (Pydantic → Django)
    if "nid" in df.columns:
        df = df.rename(columns={"nid": "id"})

    # 2. Integer columns → Int64 (nullable)
    int_cols = [
        "id",
        "word_num",
        "click_num",
        "praise_num",
        "like_num",
        "review_num",
        "comment_num",
    ]
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    # 3. Boolean column → boolean (nullable)
    if "has_banner" in df.columns:
        df["has_banner"] = df["has_banner"].astype("boolean")

    # 4. String columns → StringDtype (more efficient than object)
    str_cols = ["title", "author", "genre", "status", "ptype", "contest", "cover"]
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].astype("string")

    # 5. Enum mapping → vectorized .map()
    if "genre" in df.columns:
        genre_map = GENRE.zh_to_value_dict()
        df["genre"] = (
            df["genre"].map(genre_map).fillna(GENRE.fallback()).astype("Int64")
        )

    if "status" in df.columns:
        status_map = STATUS.zh_to_value_dict()
        df["status"] = (
            df["status"].map(status_map).fillna(STATUS.fallback()).astype("Int64")
        )

    if "ptype" in df.columns:
        ptype_map = PTYPE.zh_to_value_dict()
        df["ptype"] = (
            df["ptype"].map(ptype_map).fillna(PTYPE.fallback()).astype("Int64")
        )

    # 6. Time column → datetime64[ns, Asia/Shanghai]
    if "last_update" in df.columns:
        df["last_update"] = pd.to_datetime(df["last_update"], utc=True)
        if df["last_update"].dt.tz is None:
            df["last_update"] = df["last_update"].dt.tz_localize(TIMEZONE)

    # 7. Cover URL → compressed suffix (default cover → None)
    if "cover" in df.columns:
        df["cover"] = df["cover"].apply(compress_cover)

    # 8. Empty string contest → pd.NA
    if "contest" in df.columns:
        df["contest"] = df["contest"].replace("", pd.NA)

    # 9. Tags column → ensure list type
    if "tags" in df.columns:
        df["tags"] = df["tags"].apply(lambda x: x if isinstance(x, list) else [])

    return df


@log_time
def df_to_meta_list(df: pd.DataFrame) -> list[Meta]:
    """Convert DataFrame to list of validated Meta objects.

    Handles pandas NaN → None conversion before Meta validation.

    Args:
        df: Raw DataFrame from JSONL/CSV (with Pydantic field names).

    Returns:
        List of validated Meta objects.
    """
    # Replace NaN/NaT with None for Pydantic compatibility
    df = df.where(pd.notna(df), None)
    # Convert numpy types to Python native types
    records = df.to_dict("records")
    records = [{k: _to_python(v) for k, v in row.items()} for row in records]

    meta_list = []
    failed = []
    for row in progress(records, desc="Validating Meta"):
        try:
            meta_list.append(Meta(**row))
        except Exception as e:
            failed.append(
                {"nid": row.get("nid"), "title": row.get("title"), "error": str(e)}
            )
            logger.debug("Validation error for nid=%s: %s", row.get("nid"), e)

    logger.info(
        "Validated %d/%d records (%d errors)", len(meta_list), len(records), len(failed)
    )
    if failed:
        failed_path = Path("failed_records.json")
        pd.DataFrame(failed).to_json(
            failed_path, orient="records", force_ascii=False, indent=2
        )
        logger.warning("Saved %d failed records to %s", len(failed), failed_path)
    return meta_list


def _to_python(value):
    """Convert numpy/pandas types to Python native types."""
    if value is None:
        return None
    if hasattr(value, "item"):  # numpy scalar
        return value.item()
    if isinstance(value, float) and pd.isna(value):
        return None
    return value


def meta_list_to_df(meta_list: list[Meta]) -> pd.DataFrame:
    """Convert list of Meta objects to DataFrame.

    Args:
        meta_list: List of Meta objects.

    Returns:
        DataFrame with Pydantic field names.
    """
    return pd.DataFrame([m.model_dump() for m in meta_list])


@log_time
def denormalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Convert DataFrame back to JSONL/CSV format.

    Converts Django model field names back to Pydantic model field names
    (id → nid, author__name → author, contest__name → contest).

    Args:
        df: DataFrame from database (with Django field names).

    Returns:
        DataFrame with Pydantic model field names and Python native types.
    """
    df = df.copy()

    # 1. Enum reverse mapping
    if "genre" in df.columns:
        genre_map = GENRE.value_to_zh_dict()
        df["genre"] = df["genre"].map(genre_map).fillna("其他")

    if "status" in df.columns:
        status_map = STATUS.value_to_zh_dict()
        df["status"] = df["status"].map(status_map).fillna("其他")

    if "ptype" in df.columns:
        ptype_map = PTYPE.value_to_zh_dict()
        df["ptype"] = df["ptype"].map(ptype_map).fillna("免费")

    # 2. Time column → Asia/Shanghai string
    if "last_update" in df.columns:
        df["last_update"] = (
            df["last_update"]
            .dt.tz_convert(TIMEZONE)
            .dt.strftime("%Y-%m-%d %H:%M:%S+08:00")
        )

    # 3. Cover URL → expand to full URL
    if "cover" in df.columns:
        df["cover"] = df["cover"].apply(expand_cover)

    # 4. Rename columns to match Pydantic model
    rename_map = {}
    if "id" in df.columns:
        rename_map["id"] = "nid"
    if "author__name" in df.columns:
        rename_map["author__name"] = "author"
    if "contest__name" in df.columns:
        rename_map["contest__name"] = "contest"
    if rename_map:
        df = df.rename(columns=rename_map)

    return df


def django_dict_to_meta(data: dict) -> Meta:
    """Convert Django query dict to validated Meta object.

    Args:
        data: Dict from QuerySet.values() with Django field names.

    Returns:
        Validated Meta object.
    """
    return Meta.from_django_dict(data)


def meta_to_django_dict(meta: Meta) -> dict:
    """Convert Meta object to Django-ready dict.

    Args:
        meta: Validated Meta object.

    Returns:
        Dict with Django field names and types.
    """
    return meta.to_django_dict()


def df_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to list of dicts with Python native types.

    Handles pandas type conversion issues:
    - Int64 with NA → int | None
    - boolean with NA → bool | None
    - NaN → None

    Args:
        df: DataFrame from denormalize_df().

    Returns:
        List of dictionaries with Python native types.
    """
    records = df.to_dict("records")
    return [_convert_record(r) for r in records]


def _convert_record(record: dict) -> dict:
    """Convert a single record to Python native types."""
    result = {}
    for k, v in record.items():
        if v is None or (isinstance(v, float) and pd.isna(v)):
            result[k] = None
        elif isinstance(v, (int,)):
            result[k] = v
        elif isinstance(v, float):
            # Check if it's actually an integer
            if v == int(v) and not pd.isna(v):
                result[k] = int(v)
            else:
                result[k] = v
        elif hasattr(v, "item"):  # numpy scalar
            val = v.item()
            if isinstance(val, float) and val == int(val) and not pd.isna(val):
                result[k] = int(val)
            else:
                result[k] = val
        else:
            result[k] = v
    return result


def extract_authors(df: pd.DataFrame) -> pd.Series:
    """Extract unique authors from DataFrame.

    Args:
        df: Normalized DataFrame.

    Returns:
        Series of unique author names.
    """
    authors = df["author"].dropna().unique()
    logger.info("Extracted %d unique authors", len(authors))
    return authors


def extract_tags(df: pd.DataFrame) -> pd.Series:
    """Extract unique tags from DataFrame.

    Args:
        df: Normalized DataFrame.

    Returns:
        Series of unique tag names.
    """
    tags = df["tags"].explode().dropna().unique()
    logger.info("Extracted %d unique tags", len(tags))
    return tags


def extract_contests(df: pd.DataFrame) -> pd.Series:
    """Extract unique contests from DataFrame.

    Args:
        df: Normalized DataFrame.

    Returns:
        Series of unique contest names.
    """
    contests = df["contest"].dropna().unique()
    logger.info("Extracted %d unique contests", len(contests))
    return contests
