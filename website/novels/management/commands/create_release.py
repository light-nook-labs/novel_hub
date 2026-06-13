"""Create GitHub release tar from dump_dataset output.

Runs dump_dataset, then packages release/ into a tar.gz file.

Usage:
    uv run python manage.py create_release
    uv run python manage.py create_release --output ../release
    uv run python manage.py create_release --tag v20260613
"""

import shutil
import time
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create release tar.gz from dump_dataset output"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="release",
            help="Output directory (default: release)",
        )
        parser.add_argument(
            "--tag",
            default="",
            help="Release tag for filename (e.g. v20260613)",
        )

    def handle(self, *args, **options):
        t0 = time.time()
        out_dir = Path(options["output"])
        tag = options["tag"]

        self.stdout.write("Step 1: Dump dataset")
        call_command("dump_dataset", output=out_dir)

        self.stdout.write("Step 2: Package tar.gz")
        if tag:
            tar_name = f"dataset-{tag}"
        else:
            tar_name = "dataset"

        project_root = settings.BASE_DIR.parent
        tar_path = project_root / tar_name
        shutil.make_archive(str(tar_path), "gztar", root_dir=out_dir)

        tar_file = project_root / f"{tar_name}.tar.gz"

        elapsed = time.time() - t0
        size_mb = tar_file.stat().st_size / 1024 / 1024
        self.stdout.write(
            self.style.SUCCESS(
                f"Done in {elapsed:.1f}s — {tar_file} ({size_mb:.1f} MB)"
            )
        )
