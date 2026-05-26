from pathlib import Path

import pandas as pd

# /sfacg_metadata_crawler/meta_spider/
p = Path(__file__).parent.parent.parent

df = pd.read_json(p / "tag.jsonl", lines=True)
df = df.tags
all_tags = df.explode().dropna().unique()

print(all_tags.tolist())