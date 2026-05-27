from pathlib import Path
import pandas as pd

from .common import compress_cover_url
from database.mappings import STATUS, GENRE, PTYPE


def prep_jsonl(filepath: Path, inplace: bool = True) -> pd.DataFrame:
    """Clean novel data from JSONL file.
    Deduplicate by nid (keep the latest record by update time), handle missing values,
    convert data types, parse datetime, compress cover url and map label to enum number.
    Missing values will be stored as NULL in database.
    """
    df = pd.read_json(filepath, lines=True)

    # Convert empty string and blank content to pd.NA
    text_fill_cols = ["author", "contest", "cover"]
    for col in text_fill_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace("", pd.NA)

    # Parse datetime, set invalid value to NaT
    df["last_update"] = pd.to_datetime(df["last_update"], errors="coerce")

    # Deduplicate by nid, keep the latest record
    df = df.loc[df.groupby("nid")["last_update"].idxmax()].reset_index(drop=True)

    # Backup original text if not inplace mode
    if not inplace:
        df["genre_raw"] = df["genre"]
        df["status_raw"] = df["status"]
        df["ptype_raw"] = df["ptype"]

    # Map text label to enum value
    df["genre"] = df["genre"].apply(lambda x: GENRE.get_enum_from_label(x, lang="zh").value)
    df["status"] = df["status"].apply(lambda x: STATUS.get_enum_from_label(x, lang="zh").value)
    df["ptype"] = df["ptype"].apply(lambda x: PTYPE.get_enum_from_label(x, lang="zh").value)

    # Convert columns to nullable integer type
    int_cols = [
        "word_num",
        "click_num",
        "praise_num",
        "like_num",
        "review_num",
        "comment_num",
    ]
    for col in int_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    # Process cover image url
    df["cover"] = df["cover"].apply(compress_cover_url)

    return df


__all__ = ["prep_jsonl"]


if __name__ == '__main__':
    workplace = Path(__file__).parent.parent
    jsonl_file = workplace / "o.jsonl"
    csv_with_raw = workplace / "data_with_raw.csv"
    csv_only_enum = workplace / "data_with_enum.csv"

    print(list(STATUS.enum))
    print(list(PTYPE.enum))
    print(list(GENRE.enum))
    print("-" * 80)

    # Non-inplace mode
    df = prep_jsonl(jsonl_file, inplace=False)
    compare_cols = [
        "nid",
        "ptype_raw", "ptype",
        "genre_raw", "genre",
        "status_raw", "status",
        "title",
        "author", "contest"
    ]
    print("=== Non-inplace mode (raw data with _raw suffix) ===")
    print(df[compare_cols].head(10))
    print("-" * 80)
    df.to_csv(csv_with_raw, index=False, encoding="utf-8-sig")

    # Inplace mode
    df = prep_jsonl(jsonl_file)
    compare_cols = [
        "nid",
        "ptype",
        "genre",
        "status",
        "title",
        "author", "contest"
    ]
    print("=== Inplace mode ===")
    print(df[compare_cols].head(10))
    df.to_csv(csv_only_enum, index=False, encoding="utf-8-sig")