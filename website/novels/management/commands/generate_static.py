"""Generate static HTML pages for GitHub Pages deployment."""

import math
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

    def handle(self, *args, **options):
        out = Path(options["output"])
        index_pages = options["index_pages"]
        rank_pages = options["rank_pages"]

        self.stdout.write("Generating static pages...")

        # ── Index pages ───────────────────────────────────────────
        for page in range(1, index_pages + 1):
            html = self._render_page(NovelListView, "/", page)
            if not html:
                self.stdout.write(f"  index page {page} — empty, stopping")
                break
            fname = "index.html" if page == 1 else f"page{page}.html"
            self._write(out / fname, html)
            self.stdout.write(f"  index page {page}")

        # ── Rank pages ────────────────────────────────────────────
        for page in range(1, rank_pages + 1):
            html = self._render_page(NovelRankView, "/rank/", page)
            if not html:
                self.stdout.write(f"  rank page {page} — empty, stopping")
                break
            fname = "index.html" if page == 1 else f"page{page}.html"
            self._write(out / "rank" / fname, html)
            self.stdout.write(f"  rank page {page}")

        # ── Banner pages ──────────────────────────────────────────
        banner_count = Novel.objects.filter(has_banner=True).count()
        banner_total = max(1, math.ceil(banner_count / 12))
        for page in range(1, banner_total + 1):
            html = self._render_page(BannerListView, "/banners/", page)
            if not html:
                break
            fname = "index.html" if page == 1 else f"page{page}.html"
            self._write(out / "banners" / fname, html)
            self.stdout.write(f"  banner page {page}")

        # ── About page ────────────────────────────────────────────
        html = self._render_page(AboutView, "/about/")
        if html:
            self._write(out / "about" / "index.html", html)
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
