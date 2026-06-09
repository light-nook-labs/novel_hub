"""Generate static HTML pages for GitHub Pages deployment."""

import math
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template import loader
from django.test import RequestFactory

from novels.models import Novel, Author, Tag, Contest
from novels.views import (
    NovelListView,
    NovelRankView,
    BannerListView,
    AboutView,
)
from novels.mappings import GENRE, STATUS, PTYPE


class Command(BaseCommand):
    help = "Generate static HTML for GitHub Pages"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="static_build",
            help="Output directory (default: static_build)",
        )
        parser.add_argument("--index-pages", type=int, default=10)
        parser.add_argument("--rank-pages", type=int, default=50)

    def handle(self, *args, **options):
        out = Path(options["output"])
        index_pages = options["index_pages"]
        rank_pages = options["rank_pages"]
        factory = RequestFactory()

        self.stdout.write("Generating static pages...")

        # ── Index pages ───────────────────────────────────────────
        for page in range(1, index_pages + 1):
            req = factory.get("/", {"page": page})
            resp = NovelListView.as_view()(req)
            resp.render()
            if page == 1:
                self._write(out / "index.html", resp.content.decode())
            else:
                self._write(out / f"page{page}.html", resp.content.decode())
            self.stdout.write(f"  index page {page}")

        # ── Rank pages ────────────────────────────────────────────
        for page in range(1, rank_pages + 1):
            req = factory.get("/rank/", {"page": page})
            resp = NovelRankView.as_view()(req)
            resp.render()
            if page == 1:
                self._write(out / "rank" / "index.html", resp.content.decode())
            else:
                self._write(out / "rank" / f"page{page}.html", resp.content.decode())
            self.stdout.write(f"  rank page {page}")

        # ── Banner pages ──────────────────────────────────────────
        banner_count = Novel.objects.filter(has_banner=True).count()
        banner_per_page = 12
        banner_total = max(1, math.ceil(banner_count / banner_per_page))
        for page in range(1, banner_total + 1):
            req = factory.get("/banners/", {"page": page})
            resp = BannerListView.as_view()(req)
            resp.render()
            if page == 1:
                self._write(
                    out / "banners" / "index.html", resp.content.decode()
                )
            else:
                self._write(
                    out / "banners" / f"page{page}.html", resp.content.decode()
                )
            self.stdout.write(f"  banner page {page}")

        # ── About page ────────────────────────────────────────────
        req = factory.get("/about/")
        resp = AboutView.as_view()(req)
        resp.render()
        self._write(out / "about" / "index.html", resp.content.decode())
        self.stdout.write("  about page")

        # ── Copy static assets ────────────────────────────────────
        static_src = settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else None
        if static_src:
            import shutil
            static_dst = out / "static"
            if static_dst.exists():
                shutil.rmtree(static_dst)
            static_dst.mkdir(parents=True, exist_ok=True)
            for item in Path(static_src).iterdir():
                if item.name == "node_modules":
                    # Only copy htmx dist, not all node_modules
                    htmx_src = item / "htmx.org" / "dist"
                    if htmx_src.exists():
                        shutil.copytree(htmx_src, static_dst / "node_modules" / "htmx.org" / "dist")
                else:
                    if item.is_dir():
                        shutil.copytree(item, static_dst / item.name)
                    else:
                        shutil.copy2(item, static_dst / item.name)
            self.stdout.write("  static assets copied")

        self.stdout.write(self.style.SUCCESS(f"Done! Output: {out}"))

    def _write(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
