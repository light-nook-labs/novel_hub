from pathlib import Path
import pandas as pd

# Import global log & decorator from current package
from . import log_elapsed
from database import COVER_BASE, DEFAULT_COVER
from database.mappings import STATUS, GENRE, PTYPE

# Pre-build label-to-enum-value mapping by official API
# Cover all valid chinese labels, fallback to OTHER for unknown values
GENRE_ZH2VAL = {
    zh: GENRE.get_enum_from_label(zh, lang="zh").value
    for zh in GENRE.zh_en_mapping.keys()
}
STATUS_ZH2VAL = {
    zh: STATUS.get_enum_from_label(zh, lang="zh").value
    for zh in STATUS.zh_en_mapping.keys()
}
PTYPE_ZH2VAL = {
    zh: PTYPE.get_enum_from_label(zh, lang="zh").value
    for zh in PTYPE.zh_en_mapping.keys()
}

# Fallback value for missing / unknown labels
GENRE_FALLBACK = GENRE.enum["OTHER"].value
STATUS_FALLBACK = STATUS.enum["OTHER"].value
PTYPE_FALLBACK = PTYPE.enum["OTHER"].value


@log_elapsed
def prep_jsonl(filepath: Path, inplace: bool = True) -> pd.DataFrame:
    """Clean novel data from JSONL file.
    Deduplicate by nid (keep the latest record by update time), handle missing values,
    convert data types, parse datetime, compress cover url and map label to enum number.
    Missing values will be stored as NULL in database.
    """
    df = pd.read_json(filepath, lines=True, dtype_backend="numpy_nullable")

    # Convert text columns to nullable string type, replace empty string with pd.NA
    text_cols = ["author", "contest", "cover"]
    exist_text = [c for c in text_cols if c in df.columns]
    if exist_text:
        df[exist_text] = df[exist_text].astype("string").replace("", pd.NA)

    # Parse datetime, set unparsable entries to NaT
    df["last_update"] = pd.to_datetime(df["last_update"], errors="coerce")

    # Deduplicate records, keep the latest one per nid
    df = df.loc[df.groupby("nid")["last_update"].idxmax()].reset_index(drop=True)

    # Preserve original label columns if not inplace mode
    if not inplace:
        df[["genre_raw", "status_raw", "ptype_raw"]] = df[
            ["genre", "status", "ptype"]
        ].astype("string")

    # Vectorized mapping: chinese label -> enum value, fill unknown with fallback
    df["genre"] = df["genre"].map(GENRE_ZH2VAL).fillna(GENRE_FALLBACK)
    df["status"] = df["status"].map(STATUS_ZH2VAL).fillna(STATUS_FALLBACK)
    df["ptype"] = df["ptype"].map(PTYPE_ZH2VAL).fillna(PTYPE_FALLBACK)
    df[["genre", "status", "ptype"]] = df[["genre", "status", "ptype"]].astype("Int64")

    # Process numeric columns in batch
    int_cols = [
        "word_num",
        "click_num",
        "praise_num",
        "like_num",
        "review_num",
        "comment_num",
    ]
    miss_cols = [col for col in int_cols if col not in df.columns]
    if miss_cols:
        df[miss_cols] = pd.NA
    df[int_cols] = df[int_cols].apply(pd.to_numeric, errors="coerce").astype("Int64")

    # Vectorized cover url compression, align with original function logic
    if "cover" in df.columns:
        base_len = len(COVER_BASE)
        s = df["cover"]
        suffix = s.str[base_len:].where(s.str.startswith(COVER_BASE, na=False), pd.NA)
        df["cover"] = suffix.where(suffix != DEFAULT_COVER, pd.NA)

    return df


__all__ = ["prep_jsonl"]


if __name__ == "__main__":
    # Temporary log config for local debugging only
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    workplace = Path(__file__).parent.parent
    jsonl_file = workplace / "data.jsonl"
    csv_with_raw = workplace / "data_with_raw.csv"
    csv_with_enum = workplace / "data_with_enum.csv"

    print(list(STATUS.enum))
    print(list(PTYPE.enum))
    print(list(GENRE.enum))
    print("-" * 80)

    df = prep_jsonl(jsonl_file, inplace=False)
    compare_cols = [
        "nid",
        "ptype_raw",
        "ptype",
        "genre_raw",
        "genre",
        "status_raw",
        "status",
        "title",
        "author",
        "contest",
    ]
    print("=== Non-inplace mode (raw data with _raw suffix) ===")
    print(df[compare_cols].head(10))
    print("-" * 80)
    df.to_csv(csv_with_raw, index=False, encoding="utf-8-sig")

    df = prep_jsonl(jsonl_file)
    compare_cols = [
        "nid",
        "ptype",
        "genre",
        "status",
        "title",
        "author",
        "contest",
    ]
    print("=== Inplace mode ===")
    print(df[compare_cols].head(10))
    print("-" * 80)
    df.to_csv(csv_with_enum, index=False, encoding="utf-8-sig")
