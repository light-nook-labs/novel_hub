"""Scrapy pipelines for meta_spider."""

import csv
import json
from datetime import date

from utils.models import Meta


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


class SnapshotPipeline:
    """Create snapshot for each ON_GOING novel crawled.

    Only processes novels with status '连载中' (ON_GOING on sfacg.com).
    Skips novels that don't exist in DB.
    """

    def process_item(self, item, spider):
        if not isinstance(item, Meta):
            return item

        # Only ON_GOING (sfacg shows as '连载中')
        if item.status != "连载中":
            return item

        try:
            from novels.models import Novel, NovelSnapshot

            novel = Novel.objects.get(id=item.nid)
            today = date.today()

            NovelSnapshot.objects.update_or_create(
                novel=novel,
                snapshot_date=today,
                defaults={
                    "click_num": item.click_num,
                    "like_num": item.like_num,
                    "praise_num": item.praise_num,
                    "word_num": item.word_num,
                    "review_num": item.review_num,
                    "comment_num": item.comment_num,
                },
            )
        except Exception as e:
            spider.logger.warning(f"SnapshotPipeline: failed for {item.nid}: {e}")

        return item
