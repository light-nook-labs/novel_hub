"""Scrapy pipelines for meta_spider."""

import csv
import json

from models import Meta


class CSVPipeline:
    """Write Meta items to CSV file.

    Enabled via -o output.csv or FEEDS config.
    Field names follow Meta model (the standard format).
    """

    def open_spider(self, spider):
        self.file = open("o.csv", "w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(
            self.file, fieldnames=list(Meta.model_fields.keys())
        )
        self.writer.writeheader()

    def close_spider(self, spider):
        self.file.close()

    def process_item(self, item, spider):
        if isinstance(item, Meta):
            row = item.model_dump()
            row["tags"] = json.dumps(row["tags"], ensure_ascii=False)
            row["last_update"] = (
                row["last_update"].isoformat() if row["last_update"] else ""
            )
            self.writer.writerow(row)
        return item
