from pathlib import Path

import pandas as pd


from .utils import compress_cover_url


def prep_jsonl(filepath: Path) -> pd.DataFrame:
    """JSON Line preprocesser
    Clean novel data from JSONL file.
    Deduplicate by nid (keep the latest record by update time), handle missing values,
    convert data types, parse datetime and compress cover url.
    Missing values will be stored as NULL in database.

    Args:
        filepath: Path object of the target JSONL file
    """
    # Load data from jsonl file
    df = pd.read_json(filepath, lines=True)

    # Convert update time column to datetime type, set invalid values to NaT
    df["last_update"] = pd.to_datetime(df["last_update"], errors="coerce")

    # Deduplicate by nid, keep the record with the latest last_update
    df = df.loc[df.groupby("nid")["last_update"].idxmax()].reset_index(
        drop=True
    )

    # Replace empty string with pd.NA for database NULL
    df["contest"] = df["contest"].replace("", pd.NA)

    # Define numeric columns to convert to nullable integer type(Int64)
    int_cols = [
        "word_num",
        "click_num",
        "praise_num",
        "like_num",
        "review_num",
        "comment_num",
    ]
    for col in int_cols:
        # Convert to numeric, set invalid data to NA, then cast to nullable integer
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    # Compress cover image url
    df["cover"] = df["cover"].apply(compress_cover_url)

    return df


__all__ = ["prep_jsonl"]


if __name__ == '__main__':
    from pathlib import Path
    p = Path(__file__).parent.parent / "o.jsonl"
    df = prep_jsonl(p)
    print(df.head(10))