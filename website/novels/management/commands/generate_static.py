"""Generate static HTML pages for GitHub Pages deployment."""

import math
import re
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

    def _render_page(self, view_cls, url, page=None):
        factory = RequestFactory()
        params = {"page": page} if page else {}
        req = factory.get(url, params)
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

    def handle(self, *args, **options):
        out = Path(options["output"])
        index_pages = options["index_pages"]
        rank_pages = options["rank_pages"]
        base_path = options["base_path"].strip("/")

        self.stdout.write("Generating static pages...")

        pages = []

        for page in range(1, index_pages + 1):
            html = self._render_page(NovelListView, "/", page)
            if not html:
                self.stdout.write(f"  index page {page} — empty, stopping")
                break
            fname = "index.html" if page == 1 else f"page{page}.html"
            pages.append((Path(fname), html))
            self.stdout.write(f"  index page {page}")

        for page in range(1, rank_pages + 1):
            html = self._render_page(NovelRankView, "/rank/", page)
            if not html:
                self.stdout.write(f"  rank page {page} — empty, stopping")
                break
            fname = "index.html" if page == 1 else f"page{page}.html"
            pages.append((Path("rank") / fname, html))
            self.stdout.write(f"  rank page {page}")

        banner_count = Novel.objects.filter(has_banner=True).count()
        banner_total = max(1, math.ceil(banner_count / 12))
        for page in range(1, banner_total + 1):
            html = self._render_page(BannerListView, "/banners/", page)
            if not html:
                break
            fname = "index.html" if page == 1 else f"page{page}.html"
            pages.append((Path("banners") / fname, html))
            self.stdout.write(f"  banner page {page}")

        html = self._render_page(AboutView, "/about/")
        if html:
            pages.append((Path("about") / "index.html", html))
            self.stdout.write("  about page")

        for rel_path, content in pages:
            if base_path:
                depth = self._page_depth(rel_path)
                content = self._fix_paths(content, depth)
            self._write(out / rel_path, content)

        staticfiles_dirs = settings.STATICFILES_DIRS
        static_src = staticfiles_dirs[0] if staticfiles_dirs else None
        if static_src:
            import shutil

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

        self.stdout.write(self.style.SUCCESS(f"Done! Output: {out}"))

    def _write(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
