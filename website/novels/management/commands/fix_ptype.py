"""Fix ptype: upgrade only (free → sign → VIP), never downgrade.

Usage:
    uv run python manage.py fix_ptype ../release/dataset/
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = "Fix ptype from JSONL (upgrade only, never downgrade)"

    def add_arguments(self, parser):
        parser.add_argument("path", type=str, help="Path to JSONL file or directory")

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.exists():
            raise CommandError(f"Path does not exist: {path}")

        # Load only nid and ptype from JSONL
        if path.is_dir():
            files = sorted(path.glob("meta_*.jsonl"))
        else:
            files = [path]

        # Collect VIP and 签约 nids
        vip_nids = []
        sign_nids = []

        for f in files:
            with open(f, encoding="utf-8") as fp:
                for line in fp:
                    d = json.loads(line)
                    if d.get("ptype") == "VIP":
                        vip_nids.append(d["nid"])
                    elif d.get("ptype") == "签约":
                        sign_nids.append(d["nid"])

        self.stdout.write(f"Found {len(vip_nids)} VIP, {len(sign_nids)} 签约 novels")

        # Batch update: only upgrade, never downgrade
        updated = 0
        with connection.cursor() as cursor:
            # VIP (ptype=4): upgrade from free(2) or sign(3)
            if vip_nids:
                cursor.execute(
                    "UPDATE novels_novel SET ptype = 4 WHERE id = ANY(%s) AND ptype < 4",
                    [vip_nids],
                )
                updated += cursor.rowcount
                self.stdout.write(f"  VIP: upgraded {cursor.rowcount}")

            # 签约 (ptype=3): upgrade from free(2) only
            if sign_nids:
                cursor.execute(
                    "UPDATE novels_novel SET ptype = 3 WHERE id = ANY(%s) AND ptype < 3",
                    [sign_nids],
                )
                updated += cursor.rowcount
                self.stdout.write(f"  签约: upgraded {cursor.rowcount}")

        self.stdout.write(self.style.SUCCESS(f"Total upgraded: {updated}"))
