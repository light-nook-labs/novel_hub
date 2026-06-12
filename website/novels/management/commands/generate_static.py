"""Generate static HTML pages for GitHub Pages deployment."""

import math
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
    AuthorListView,
    AboutView,
)

# Global precomputed data for SSG
_SSG_DATA = {}


def _precompute_all(index_pages, rank_pages, authors_pages):
    """Precompute all data needed for SSG in one pass."""
    from django.db.models import Sum, Count, Max, Subquery, OuterRef, Q

    data = {}

    # Get real counts from DB (fast COUNT query)
    data["novel_count"] = Novel.objects.count()
    data["banner_count"] = Novel.objects.filter(has_banner=True).count()

    # Compute how many items we need per view type
    rank_paginate_by = 100
    index_paginate_by = 24
    authors_paginate_by = 100
    banner_paginate_by = 12

    rank_needed = rank_pages * rank_paginate_by
    index_needed = index_pages * index_paginate_by
    authors_needed = authors_pages * authors_paginate_by

    max_novels_needed = max(rank_needed, index_needed) + 100

    # Load novels (top by click for rank/index) - only what we need
    novels = list(
        Novel.objects.select_related("author", "contest")
        .only(
            "id", "title", "ptype", "genre", "status",
            "click_num", "word_num", "praise_num", "like_num",
            "review_num", "comment_num", "has_banner", "cover",
            "last_update", "author__name", "contest__name",
        )
        .order_by("-click_num")[:max_novels_needed]
    )

    # Prefetch tags using Django's built-in mechanism (batched)
    from django.db.models import Prefetch
    from novels.models import Tag
    Novel.objects.prefetch_related(
        Prefetch("tags", queryset=Tag.objects.only("id", "name"))
    ).filter(id__in=[n.id for n in novels]).all()
    # Actually use prefetch_related_objects on the already-loaded list
    from django.db.models import prefetch_related_objects
    prefetch_related_objects(novels, Prefetch("tags", queryset=Tag.objects.only("id", "name")))

    data["novels"] = novels

    # Authors with aggregations
    from novels.models import Author
    top_novel = (
        Novel.objects.filter(author=OuterRef("pk"))
        .order_by("-click_num")
        .values("id", "title", "click_num")[:1]
    )
    authors = list(
        Author.objects.annotate(
            novel_count=Count("novels"),
            total_click=Sum("novels__click_num"),
            total_word=Sum("novels__word_num"),
            total_like=Sum("novels__like_num"),
            total_praise=Sum("novels__praise_num"),
            total_review=Sum("novels__review_num"),
            total_comment=Sum("novels__comment_num"),
            banner_count=Count("novels", filter=Q(novels__has_banner=True)),
            latest_update=Max("novels__last_update"),
            top_novel_id=Subquery(top_novel.values("id")),
            top_novel_title=Subquery(top_novel.values("title")),
            top_novel_click=Subquery(top_novel.values("click_num")),
        )
        .order_by("-total_click")[:authors_needed + 200]
    )
    data["authors"] = authors
    data["author_count"] = len(authors)

    # Banners (filter from already-loaded novels)
    banners = [n for n in novels if n.has_banner]
    data["banners"] = banners
    data["banner_count"] = len(banners)

    return data


def _render_page_static(view_cls, url, page, data):
    """Render a page using precomputed data."""
    from django.db import close_old_connections
    from django.template.loader import render_to_string

    close_old_connections()

    paginate_by = getattr(view_cls, "paginate_by", None) or 24
    request = RequestFactory().get(url, {"page": page} if page else {})
    request.static_mode = True

    # Determine which dataset to use
    if view_cls == NovelListView:
        items = data["novels"]
        total = data["novel_count"]
    elif view_cls == NovelRankView:
        items = data["novels"]
        total = data["novel_count"]
    elif view_cls == AuthorListView:
        items = data["authors"]
        total = data["author_count"]
    elif view_cls == BannerListView:
        items = data["banners"]
        total = data["banner_count"]
    else:
        # AboutView or unknown - render normally
        try:
            resp = view_cls.as_view()(request)
            resp.render()
            return resp.content.decode()
        except Http404:
            return None

    # Compute pagination
    total_pages = max(1, math.ceil(total / paginate_by))
    if page and page > total_pages:
        return None

    page_num = page or 1
    start = (page_num - 1) * paginate_by
    end = start + paginate_by
    page_items = items[start:end]

    # Build page object
    class FakePage:
        def __init__(self, number, num_pages, has_next, has_previous):
            self.number = number
            self.num_pages = num_pages
            self.has_next = has_next
            self.has_previous = has_previous

    class FakePaginator:
        def __init__(self, count, num_pages):
            self.count = count
            self.num_pages = num_pages

    fake_page = FakePage(
        page_num, total_pages,
        page_num < total_pages,
        page_num > 1,
    )
    fake_paginator = FakePaginator(total, total_pages)

    # Build context
    context = {
        "novels" if view_cls != AuthorListView else "authors": page_items,
        "page_obj": fake_page,
        "paginator": fake_paginator,
        "is_paginated": total_pages > 1,
        "request": request,
        "static_mode": True,
    }

    # Add view-specific context
    if view_cls == NovelListView:
        context["novels"] = page_items
        context["query"] = ""
        context["genres"] = []
        context["statuses"] = []
        context["ptypes"] = []
        context["current_genre"] = ""
        context["current_status"] = ""
        context["current_ptype"] = ""
        context["current_sort"] = ""
        context["sort_options"] = NovelListView.SORT_OPTIONS
        context["latest_banner"] = next(
            (n for n in data["novels"] if n.has_banner), None
        )
        context["querystring"] = ""
    elif view_cls == NovelRankView:
        context["novels"] = page_items
        context["current_sort"] = "click_num"
        context["current_dir"] = "desc"
        context["page_start"] = start + 1
        from novels.views import COLUMNS
        context["columns"] = COLUMNS
        context["querystring"] = ""
    elif view_cls == AuthorListView:
        context["authors"] = page_items
        context["sort_options"] = AuthorListView.SORT_OPTIONS
        context["current_sort"] = "total_click"
        context["current_dir"] = "desc"
        context["page_start"] = start + 1
        context["querystring"] = ""
    elif view_cls == BannerListView:
        context["novels"] = page_items
        context["querystring"] = ""

    # Render template
    template_name = view_cls.template_name
    try:
        html = render_to_string(template_name, context, request=request)
        return html
    except Exception:
        # Fallback to normal rendering
        try:
            resp = view_cls.as_view()(request)
            resp.render()
            return resp.content.decode()
        except Http404:
            return None


class Command(BaseCommand):
    help = "Generate static HTML for GitHub Pages"

    def add_arguments(self, parser):
        parser.add_argument("--output", default="build")
        parser.add_argument("--index-pages", type=int, default=1)
        parser.add_argument("--rank-pages", type=int, default=100)
        parser.add_argument("--authors-pages", type=int, default=10)
        parser.add_argument(
            "--base-path",
            default="",
            help="Base path for subdirectory deploy (e.g. 'novel_hub')",
        )
        parser.add_argument(
            "--workers",
            type=int,
            default=32,
            help="Number of parallel workers (default: 32)",
        )

    @staticmethod
    def _fix_paths(html, depth):
        """Convert absolute paths to relative paths for subdirectory deploy."""
        if depth <= 0:
            return html
        prefix = "../" * depth
        html = html.replace('href="/static/', f'href="{prefix}static/')
        html = html.replace('src="/static/', f'src="{prefix}static/')
        html = html.replace('href="/', f'href="{prefix}')
        html = html.replace('src="/', f'src="{prefix}')
        return html

    @staticmethod
    def _page_depth(rel_path):
        """Calculate directory depth of a file relative to output root."""
        return len(rel_path.parts) - 1

    def _build_tasks(self, index_pages, rank_pages, authors_pages):
        """Build list of (view_cls, url, page, rel_path) tuples."""
        tasks = []

        for page in range(1, index_pages + 1):
            fname = "index.html" if page == 1 else f"page{page}.html"
            tasks.append((NovelListView, "/", page, Path(fname)))

        for page in range(1, rank_pages + 1):
            fname = "index.html" if page == 1 else f"page{page}.html"
            tasks.append((NovelRankView, "/rank/", page, Path("rank") / fname))

        for page in range(1, authors_pages + 1):
            fname = "index.html" if page == 1 else f"page{page}.html"
            tasks.append(
                (AuthorListView, "/authors/", page, Path("authors") / fname)
            )

        banner_count = _SSG_DATA.get("banner_count", 0)
        banner_total = max(1, math.ceil(banner_count / 12))
        for page in range(1, banner_total + 1):
            fname = "index.html" if page == 1 else f"page{page}.html"
            tasks.append(
                (BannerListView, "/banners/", page, Path("banners") / fname)
            )

        tasks.append((AboutView, "/about/", None, Path("about") / "index.html"))

        # 404 page (rendered via view, not template directly)
        tasks.append((None, "/404/", None, Path("404.html")))

        return tasks

    def handle(self, *args, **options):
        global _SSG_DATA

        out = Path(options["output"])
        index_pages = options["index_pages"]
        rank_pages = options["rank_pages"]
        authors_pages = options["authors_pages"]
        base_path = options["base_path"].strip("/")
        workers = options["workers"]

        t0 = time.time()
        self.stdout.write("Generating static pages...")

        # Precompute all data
        t_pre = time.time()
        _SSG_DATA = _precompute_all(index_pages, rank_pages, authors_pages)
        self.stdout.write(
            f"  preload: {time.time() - t_pre:.1f}s "
            f"({_SSG_DATA['novel_count']} novels, {_SSG_DATA['author_count']} authors, "
            f"{_SSG_DATA['banner_count']} banners)"
        )

        tasks = self._build_tasks(index_pages, rank_pages, authors_pages)
        total = len(tasks)
        self.stdout.write(f"  {total} pages, {workers} workers")

        pages = []
        done = 0

        def render_one(task):
            view_cls, url, page, rel_path = task
            if view_cls is None:
                # 404 page - render directly
                from django.template.loader import render_to_string
                from django.test import RequestFactory
                request = RequestFactory().get(url)
                request.static_mode = True
                html = render_to_string("novels/404.html", request=request)
            else:
                html = _render_page_static(view_cls, url, page, _SSG_DATA)
            return (rel_path, html)

        t_render = time.time()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(render_one, t): t for t in tasks}
            for future in as_completed(futures):
                rel_path, html = future.result()
                if html:
                    pages.append((rel_path, html))
                done += 1
                if done % 20 == 0 or done == total:
                    self.stdout.write(f"  {done}/{total} rendered")
        render_time = time.time() - t_render

        t_write = time.time()
        for rel_path, content in pages:
            if base_path:
                depth = self._page_depth(rel_path)
                content = self._fix_paths(content, depth)
            self._write(out / rel_path, content)
        write_time = time.time() - t_write

        staticfiles_dirs = settings.STATICFILES_DIRS
        static_src = staticfiles_dirs[0] if staticfiles_dirs else None
        if static_src:
            t_static = time.time()
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
            self.stdout.write(f"  static: {time.time() - t_static:.1f}s")

        elapsed = time.time() - t0
        self.stdout.write(
            self.style.SUCCESS(
                f"Done! {len(pages)} pages in {elapsed:.1f}s "
                f"(render {render_time:.1f}s, write {write_time:.1f}s) → {out}"
            )
        )

    def _write(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
