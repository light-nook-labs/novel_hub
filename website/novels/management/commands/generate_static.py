"""Generate static HTML pages for GitHub Pages deployment."""

import math
import re
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.http import Http404
from django.test import RequestFactory

from novels.models import Novel
from novels.views import (
    NovelListView,
    NovelRankView,
    BannerListView,
    AboutView,
)


class Command(BaseCommand):
    help = "Generate static HTML for GitHub Pages"

    def add_arguments(self, parser):
        parser.add_argument("--output", default="static_build")
        parser.add_argument("--index-pages", type=int, default=10)
        parser.add_argument("--rank-pages", type=int, default=50)
        parser.add_argument(
            "--base-path",
            default="",
            help="Base path for subdirectory deploy (e.g. 'novel_hub')",
        )
        parser.add_argument(
            "--workers",
            type=int,
            default=4,
            help="Number of parallel workers (default: 4)",
        )

    def _render_page(self, view_cls, url, page=None):
        from django.db import close_old_connections

        close_old_connections()
        factory = RequestFactory()
        params = {"page": page} if page else {}
        req = factory.get(url, params)
        req.static_mode = True
        try:
            resp = view_cls.as_view()(req)
            resp.render()
            return resp.content.decode()
        except Http404:
            return None

    def _fix_paths(self, html, depth):
        """Convert absolute paths to relative paths for subdirectory deploy."""
        prefix = "../" * depth if depth > 0 else ""
        html = re.sub(
            r'(href|src)="/static/',
            rf'\1="{prefix}static/',
            html,
        )
        html = re.sub(
            r'(href|src)="/',
            rf'\1="{prefix}',
            html,
        )
        return html

    def _page_depth(self, rel_path):
        """Calculate directory depth of a file relative to output root."""
        return len(rel_path.parts) - 1

    def _build_tasks(self, index_pages, rank_pages):
        """Build list of (view_cls, url, page, rel_path) tuples."""
        tasks = []

        for page in range(1, index_pages + 1):
            fname = "index.html" if page == 1 else f"page{page}.html"
            tasks.append((NovelListView, "/", page, Path(fname)))

        for page in range(1, rank_pages + 1):
            fname = "index.html" if page == 1 else f"page{page}.html"
            tasks.append((NovelRankView, "/rank/", page, Path("rank") / fname))

        banner_count = Novel.objects.filter(has_banner=True).count()
        banner_total = max(1, math.ceil(banner_count / 12))
        for page in range(1, banner_total + 1):
            fname = "index.html" if page == 1 else f"page{page}.html"
            tasks.append(
                (BannerListView, "/banners/", page, Path("banners") / fname)
            )

        tasks.append((AboutView, "/about/", None, Path("about") / "index.html"))

        return tasks

    def handle(self, *args, **options):
        out = Path(options["output"])
        index_pages = options["index_pages"]
        rank_pages = options["rank_pages"]
        base_path = options["base_path"].strip("/")
        workers = options["workers"]

        t0 = time.time()
        self.stdout.write("Generating static pages...")

        tasks = self._build_tasks(index_pages, rank_pages)
        total = len(tasks)
        self.stdout.write(f"  {total} pages to render with {workers} workers")

        pages = []
        done = 0

        def render_one(task):
            view_cls, url, page, rel_path = task
            html = self._render_page(view_cls, url, page)
            return (rel_path, html, page is None)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(render_one, t): t for t in tasks}
            for future in as_completed(futures):
                rel_path, html, is_single = future.result()
                if html:
                    pages.append((rel_path, html))
                done += 1
                if done % 20 == 0 or done == total:
                    self.stdout.write(f"  {done}/{total} rendered")

        for rel_path, content in pages:
            if base_path:
                depth = self._page_depth(rel_path)
                content = self._fix_paths(content, depth)
            self._write(out / rel_path, content)

        staticfiles_dirs = settings.STATICFILES_DIRS
        static_src = staticfiles_dirs[0] if staticfiles_dirs else None
        if static_src:
            static_dst = out / "static"
            if static_dst.exists():
                shutil.rmtree(static_dst)
            static_dst.mkdir(parents=True, exist_ok=True)
            for item in Path(static_src).iterdir():
                if item.name == "node_modules":
                    htmx_src = item / "htmx.org" / "dist"
                    if htmx_src.exists():
                        shutil.copytree(
                            htmx_src,
                            static_dst / "node_modules" / "htmx.org" / "dist",
                        )
                else:
                    if item.is_dir():
                        shutil.copytree(item, static_dst / item.name)
                    else:
                        shutil.copy2(item, static_dst / item.name)
            self.stdout.write("  static assets copied")

        elapsed = time.time() - t0
        self.stdout.write(
            self.style.SUCCESS(f"Done! {len(pages)} pages in {elapsed:.1f}s → {out}")
        )

    def _write(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
