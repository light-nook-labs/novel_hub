"""Management command to generate static site for GitHub Pages.

Generates:
- index.html (1 page)
- about.html (1 page)
- authors/ (10 pages)
- rank/ (100 pages)
- banners/ (all pages)
- 404.html (1 page)
- static/ (CSS, JS, images)

Usage:
    uv run python manage.py generate_static --output ../build --base-path novel_hub
"""

import os
import shutil
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import models
from django.db.models import Subquery, OuterRef, Count, Sum, Max
from django.template.loader import render_to_string

from novels.models import Author, Novel, Tag, Contest
from novels.views import AuthorListView
from novels.views.novel import COLUMNS
from novels.mappings import GENRE, STATUS, PTYPE

from utils.logger import get_logger, progress

logger = get_logger(__name__)

# SSG configuration
AUTHORS_PAGES = 10
RANK_PAGES = 100


class SimplePage:
    """Simple page object for pagination in SSG."""

    def __init__(self, number, paginator):
        self.number = number
        self.paginator = paginator

    def has_previous(self):
        return self.number > 1

    def has_next(self):
        return self.number < self.paginator.num_pages

    def previous_page_number(self):
        return self.number - 1

    def next_page_number(self):
        return self.number + 1


class SimplePaginator:
    """Simple paginator for SSG."""

    def __init__(self, count, per_page):
        self.count = count
        self.per_page = per_page
        self.num_pages = (count + per_page - 1) // per_page

    @property
    def page_range(self):
        return range(1, self.num_pages + 1)


def _generate_page(args):
    """Generate a single HTML page (for multiprocessing)."""
    template, context, output_path, base_path = args

    # Add common context
    context["static_mode"] = True
    context["base_path"] = base_path
    context["TOML"] = settings.TOML

    html = render_to_string(template, context)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


class Command(BaseCommand):
    help = "Generate static site for GitHub Pages"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default="../build",
            help="Output directory (default: ../build)",
        )
        parser.add_argument(
            "--base-path",
            type=str,
            default="",
            help="Base path for URLs (e.g., 'novel_hub' for GitHub Pages)",
        )
        parser.add_argument(
            "--workers",
            type=int,
            default=4,
            help="Number of worker processes (default: 4)",
        )

    def handle(self, *args, **options):
        output_dir = Path(options["output"])
        base_path = options["base_path"]
        workers = options["workers"]

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Copy static files
        self._copy_static_files(output_dir, base_path)

        # Pre-fetch all data
        logger.info("Pre-fetching data...")
        data = self._prefetch_data()
        logger.info(
            "Data fetched: %d novels, %d authors",
            data["novel_count"],
            data["author_count"],
        )

        # Collect all pages to generate
        pages = []

        # 1. Index page (1 page)
        pages.extend(self._collect_index_pages(output_dir, base_path, data))

        # 2. About page (1 page)
        pages.extend(self._collect_about_pages(output_dir, base_path, data))

        # 3. Authors pages (10 pages)
        pages.extend(self._collect_author_pages(output_dir, base_path, data))

        # 4. Rank pages (100 pages)
        pages.extend(self._collect_rank_pages(output_dir, base_path, data))

        # 5. Banner pages (all pages)
        pages.extend(self._collect_banner_pages(output_dir, base_path, data))

        # 6. Comments page (1 page)
        pages.extend(self._collect_comments_pages(output_dir, base_path, data))

        # 7. Dashboard page (1 page)
        pages.extend(self._collect_dashboard_pages(output_dir, base_path, data))

        # 8. 404 page (1 page)
        pages.extend(self._collect_404_pages(output_dir, base_path))

        logger.info(
            "Generating %d static pages with %d workers...", len(pages), workers
        )

        # Generate pages using multiprocessing
        generated = 0
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_generate_page, page): page for page in pages}

            for future in progress(
                as_completed(futures), desc="Generating", total=len(pages)
            ):
                try:
                    future.result()
                    generated += 1
                except Exception as e:
                    logger.error("Error generating page: %s", e)

        logger.info("Generated %d/%d pages", generated, len(pages))

    def _prefetch_data(self):
        """Pre-fetch all data for SSG generation."""
        # Common context for all pages
        novel_count = Novel.objects.count()
        author_count = Author.objects.count()

        # Get all novels with related data (only fetch needed fields)
        logger.info("Fetching novels...")
        all_novels = list(
            Novel.objects.select_related("author", "contest")
            .prefetch_related("tags")
            .order_by("-click_num")
            .only(
                "id",
                "title",
                "has_banner",
                "word_num",
                "click_num",
                "like_num",
                "praise_num",
                "review_num",
                "comment_num",
                "last_update",
                "genre",
                "status",
                "ptype",
                "cover",
                "author__name",
                "contest__name",
            )
        )

        # Get banner novels
        logger.info("Filtering banner novels...")
        banner_novels = [n for n in all_novels if n.has_banner]
        from datetime import datetime

        banner_novels.sort(key=lambda n: n.last_update or datetime.min, reverse=True)

        # Get latest banner
        latest_banner = banner_novels[0] if banner_novels else None

        # Get all authors with annotations (simplified for performance)
        logger.info("Fetching authors...")
        all_authors = list(
            Author.objects.annotate(
                novel_count=Count("novels"),
                total_click=Sum("novels__click_num"),
                total_word=Sum("novels__word_num"),
                total_like=Sum("novels__like_num"),
                total_praise=Sum("novels__praise_num"),
                total_review=Sum("novels__review_num"),
                total_comment=Sum("novels__comment_num"),
                banner_count=Count("novels", filter=models.Q(novels__has_banner=True)),
                latest_update=Max("novels__last_update"),
            ).order_by("-total_click", "-novel_count")
        )

        # Fetch top novel for each author using ORM Window function
        logger.info("Fetching top novels for authors...")
        from django.db.models import Window, F
        from django.db.models.functions import RowNumber

        author_ids = [a.id for a in all_authors]
        ranked = (
            Novel.objects.filter(author_id__in=author_ids)
            .annotate(
                rn=Window(
                    expression=RowNumber(),
                    partition_by=[F("author_id")],
                    order_by=F("click_num").desc(nulls_last=True),
                )
            )
            .filter(rn=1)
            .values("id", "title", "click_num", "author_id")
        )
        top_novels_map = {row["author_id"]: row for row in ranked}

        for author in all_authors:
            top = top_novels_map.get(author.id, {})
            author.top_novel_id = top.get("id")
            author.top_novel_title = top.get("title")
            author.top_novel_click = top.get("click_num")

        # Get enum choices
        def _choices(mapping):
            return [
                {"value": m.value, "label": mapping.get_zh(m.value)}
                for m in mapping.enum
                if m.name != "OTHER"
            ]

        return {
            "novel_count": novel_count,
            "author_count": author_count,
            "all_novels": all_novels,
            "banner_novels": banner_novels,
            "latest_banner": latest_banner,
            "all_authors": all_authors,
            "genres": _choices(GENRE),
            "statuses": _choices(STATUS),
            "ptypes": _choices(PTYPE),
            "sort_options": AuthorListView.SORT_OPTIONS,
        }

    def _copy_static_files(self, output_dir, base_path):
        """Copy static files to output directory."""
        static_root = Path(settings.STATIC_ROOT) if settings.STATIC_ROOT else None
        staticfiles_dirs = settings.STATICFILES_DIRS

        source_dirs = []
        if static_root and static_root.exists():
            source_dirs.append(static_root)
        for dir_path in staticfiles_dirs:
            p = Path(dir_path)
            if p.exists():
                source_dirs.append(p)

        if not source_dirs:
            logger.warning("No static files directory found")
            return

        static_output = output_dir / "static"
        static_output.mkdir(parents=True, exist_ok=True)

        # Copy static files (exclude node_modules to avoid copying entire tree)
        for source_dir in source_dirs:
            if source_dir.exists():
                logger.info("Copying static files from %s", source_dir)
                for item in source_dir.iterdir():
                    if item.name == "node_modules":
                        continue  # Skip node_modules, will copy htmx separately
                    dest = static_output / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest, dirs_exist_ok=True, symlinks=False)
                    else:
                        shutil.copy2(item, dest)

        # Copy only htmx.org from node_modules
        project_root = Path(settings.BASE_DIR).parent
        node_modules_src = project_root / "node_modules"
        htmx_src = node_modules_src / "htmx.org"
        htmx_dst = static_output / "node_modules" / "htmx.org"
        if htmx_src.exists() and not htmx_dst.exists():
            logger.info("Copying htmx.org from %s", htmx_src)
            shutil.copytree(htmx_src, htmx_dst, symlinks=False)

        logger.info("Static files copied to %s", static_output)

    def _collect_index_pages(self, output_dir, base_path, data):
        """Collect index page generation tasks."""
        pages = []

        # Get first 24 novels for index
        index_novels = data["all_novels"][:24]

        context = {
            "novels": index_novels,
            "latest_banner": data["latest_banner"],
            "page_obj": None,
            "is_paginated": False,
            "query": "",
            "genres": data["genres"],
            "statuses": data["statuses"],
            "ptypes": data["ptypes"],
            "current_genre": "",
            "current_status": "",
            "current_ptype": "",
            "current_sort": "",
            "sort_options": {
                "": "综合排序",
                "click_num": "点击排序",
                "word_num": "字数排序",
                "like_num": "收藏排序",
                "praise_num": "点赞排序",
                "last_update": "最近更新",
                "db_update": "最近同步",
            },
            "querystring": "",
        }

        pages.append(
            (
                "novels/index.html",
                context,
                str(output_dir / "index.html"),
                base_path,
            )
        )

        return pages

    def _collect_about_pages(self, output_dir, base_path, data):
        """Collect about page generation tasks."""
        pages = []

        context = {
            "novel_count": data["novel_count"],
            "author_count": data["author_count"],
        }

        pages.append(
            (
                "novels/about.html",
                context,
                str(output_dir / "about" / "index.html"),
                base_path,
            )
        )

        return pages

    def _collect_author_pages(self, output_dir, base_path, data):
        """Collect author pages generation tasks."""
        pages = []
        per_page = 100

        total_authors = data["author_count"]
        total_pages = min(AUTHORS_PAGES, (total_authors + per_page - 1) // per_page)

        for page_num in range(1, total_pages + 1):
            start = (page_num - 1) * per_page
            end = start + per_page

            paginator = SimplePaginator(total_authors, per_page)
            page_obj = SimplePage(page_num, paginator)

            page_authors = data["all_authors"][start:end]

            context = {
                "authors": page_authors,
                "page_obj": page_obj,
                "paginator": paginator,
                "is_paginated": total_pages > 1,
                "sort_options": data["sort_options"],
                "current_sort": "total_click",
                "current_dir": "desc",
                "page_start": start + 1,
                "querystring": "",
            }

            if page_num == 1:
                output_path = str(output_dir / "authors" / "index.html")
            else:
                output_path = str(output_dir / "authors" / f"page{page_num}.html")

            pages.append(
                (
                    "novels/authors.html",
                    context,
                    output_path,
                    base_path,
                )
            )

        return pages

    def _collect_rank_pages(self, output_dir, base_path, data):
        """Collect rank pages generation tasks."""
        pages = []
        per_page = 100

        total_novels = data["novel_count"]
        total_pages = min(RANK_PAGES, (total_novels + per_page - 1) // per_page)

        for page_num in range(1, total_pages + 1):
            start = (page_num - 1) * per_page
            end = start + per_page

            paginator = SimplePaginator(total_novels, per_page)
            page_obj = SimplePage(page_num, paginator)

            page_novels = data["all_novels"][start:end]

            context = {
                "novels": page_novels,
                "page_obj": page_obj,
                "paginator": paginator,
                "is_paginated": total_pages > 1,
                "columns": COLUMNS,
                "current_sort": "click_num",
                "current_dir": "desc",
                "page_start": start + 1,
                "querystring": "",
            }

            if page_num == 1:
                output_path = str(output_dir / "rank" / "index.html")
            else:
                output_path = str(output_dir / "rank" / f"page{page_num}.html")

            pages.append(
                (
                    "novels/rank.html",
                    context,
                    output_path,
                    base_path,
                )
            )

        return pages

    def _collect_banner_pages(self, output_dir, base_path, data):
        """Collect banner pages generation tasks (all pages)."""
        pages = []
        per_page = 12

        banner_novels = data["banner_novels"]
        total_banners = len(banner_novels)
        total_pages = (total_banners + per_page - 1) // per_page

        for page_num in range(1, total_pages + 1):
            start = (page_num - 1) * per_page
            end = start + per_page

            paginator = SimplePaginator(total_banners, per_page)
            page_obj = SimplePage(page_num, paginator)

            page_novels = banner_novels[start:end]

            context = {
                "novels": page_novels,
                "page_obj": page_obj,
                "paginator": paginator,
                "is_paginated": total_pages > 1,
                "querystring": "",
            }

            if page_num == 1:
                output_path = str(output_dir / "banners" / "index.html")
            else:
                output_path = str(output_dir / "banners" / f"page{page_num}.html")

            pages.append(
                (
                    "novels/banners.html",
                    context,
                    output_path,
                    base_path,
                )
            )

        return pages

    def _collect_comments_pages(self, output_dir, base_path, data):
        """Collect comments page generation task."""
        pages = []

        context = {}

        pages.append(
            (
                "novels/comments.html",
                context,
                str(output_dir / "comments" / "index.html"),
                base_path,
            )
        )

        return pages

    def _collect_dashboard_pages(self, output_dir, base_path, data):
        """Collect dashboard page generation task."""
        pages = []

        # Import plotly for chart generation
        import plotly.graph_objects as go
        from novels.mappings import GENRE, STATUS, PTYPE

        def _layout(height=300):
            return dict(
                height=height,
                margin=dict(l=40, r=20, t=30, b=30),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(size=11),
            )

        def _to_html(fig):
            return fig.to_html(full_html=False, include_plotlyjs=False)

        def _to_json(fig):
            import json

            fig_dict = fig.to_dict()
            return json.dumps(
                {
                    "data": fig_dict["data"],
                    "layout": fig_dict["layout"],
                },
                ensure_ascii=False,
            )

        def _w(val):
            """Format number as X.Xw"""
            if val >= 10000:
                return f"{val/10000:.1f}w"
            return str(val)

        def _w_axis(val):
            """Format axis tick as Xw"""
            if val >= 10000:
                return f"{val//10000}w"
            return str(val)

        amber = "#f59e0b"
        orange = "#f97316"
        rose = "#f43f5e"
        colors = [
            amber,
            orange,
            rose,
            "#8b5cf6",
            "#06b6d4",
            "#10b981",
            "#3b82f6",
            "#ec4899",
            "#14b8a6",
        ]

        ctx = {
            "novel_count": data["novel_count"],
            "author_count": data["author_count"],
            "tag_count": Tag.objects.count(),
            "contest_count": Contest.objects.count(),
        }

        # 1. Genre distribution (donut)
        genre_stats = dict(
            Novel.objects.values_list("genre")
            .annotate(c=Count("id"))
            .values_list("genre", "c")
        )
        genre_labels = [GENRE.get_zh(i) for i in range(2, 11)]
        genre_data = [genre_stats.get(i, 0) for i in range(2, 11)]

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=genre_labels,
                    values=genre_data,
                    hole=0.5,
                    marker_colors=colors,
                    textinfo="label+percent",
                    textposition="outside",
                    textfont=dict(size=11),
                )
            ]
        )
        fig.update_layout(**_layout(240), showlegend=False)
        ctx["chart_genre_json"] = _to_json(fig)

        # 2. Status distribution - multiple pie charts
        status_stats = dict(
            Novel.objects.values_list("status")
            .annotate(c=Count("id"))
            .values_list("status", "c")
        )
        # FINISHED=2, ON_GOING=3, DIED=4, ACTIVE_D=5, ACTIVE_F=6, REMOVED=7

        # 2a. Real type: 已完结 (FINISHED+ACTIVE_F) vs 连载中 (ON_GOING+DIED+ACTIVE_D)
        real_finished = status_stats.get(2, 0) + status_stats.get(6, 0)
        real_ongoing = (
            status_stats.get(3, 0) + status_stats.get(4, 0) + status_stats.get(5, 0)
        )
        real_removed = status_stats.get(7, 0)
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=["已完结", "连载中", "下架"],
                    values=[real_finished, real_ongoing, real_removed],
                    hole=0.5,
                    marker_colors=[amber, orange, "#94a3b8"],
                    textinfo="label+percent",
                    textposition="outside",
                    textfont=dict(size=11),
                )
            ]
        )
        fig.update_layout(**_layout(240), showlegend=False)
        ctx["chart_real_type_json"] = _to_json(fig)

        # 2b. Status without A (no ACTIVE_D, ACTIVE_F)
        no_a_labels = ["连载中", "已完结", "断更", "下架"]
        no_a_data = [
            status_stats.get(3, 0),
            status_stats.get(2, 0),
            status_stats.get(4, 0),
            status_stats.get(7, 0),
        ]
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=no_a_labels,
                    values=no_a_data,
                    hole=0.5,
                    marker_colors=[orange, amber, rose, "#94a3b8"],
                    textinfo="label+percent",
                    textposition="outside",
                    textfont=dict(size=11),
                )
            ]
        )
        fig.update_layout(**_layout(280), showlegend=False)
        ctx["chart_status_no_a_json"] = _to_json(fig)

        # 2c. Status with A (all statuses)
        all_labels = ["连载中", "已完结", "断更", "断更A", "完结A", "下架"]
        all_data = [
            status_stats.get(3, 0),
            status_stats.get(2, 0),
            status_stats.get(4, 0),
            status_stats.get(5, 0),
            status_stats.get(6, 0),
            status_stats.get(7, 0),
        ]
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=all_labels,
                    values=all_data,
                    hole=0.5,
                    marker_colors=[
                        orange,
                        amber,
                        rose,
                        "#f472b6",
                        "#fbbf24",
                        "#94a3b8",
                    ],
                    textinfo="label+percent",
                    textposition="outside",
                    textfont=dict(size=11),
                )
            ]
        )
        fig.update_layout(**_layout(280), showlegend=False)
        ctx["chart_status_with_a_json"] = _to_json(fig)

        # 2d. 连载中 breakdown without A: 连载中 vs 断更
        ongoing_labels = ["连载中", "断更"]
        ongoing_data = [status_stats.get(3, 0), status_stats.get(4, 0)]
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=ongoing_labels,
                    values=ongoing_data,
                    hole=0.5,
                    marker_colors=[orange, rose],
                    textinfo="label+percent",
                    textposition="outside",
                    textfont=dict(size=11),
                )
            ]
        )
        fig.update_layout(**_layout(240), showlegend=False)
        ctx["chart_ongoing_breakdown_json"] = _to_json(fig)

        # 3. Ptype distribution (donut)
        ptype_stats = dict(
            Novel.objects.values_list("ptype")
            .annotate(c=Count("id"))
            .values_list("ptype", "c")
        )
        ptype_labels = [PTYPE.get_zh(i) for i in range(2, 5)]
        ptype_data = [ptype_stats.get(i, 0) for i in range(2, 5)]

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=ptype_labels,
                    values=ptype_data,
                    hole=0.5,
                    marker_colors=[amber, rose, "#6366f1"],
                    textinfo="label+percent",
                    textposition="outside",
                )
            ]
        )
        fig.update_layout(**_layout(240), showlegend=False)
        ctx["chart_ptype_json"] = _to_json(fig)

        # 6. Word count distribution (frequency histogram, exclude <10w)
        word_data = list(
            Novel.objects.filter(word_num__gte=100000).values_list(
                "word_num", flat=True
            )[:100000]
        )
        # Bins: 10-15w, 15-20w, 20-30w, 30-50w, 50-100w, 100-200w, 200-500w, 500-1000w, 1000w+
        bins = [
            100000,
            150000,
            200000,
            300000,
            500000,
            1000000,
            2000000,
            5000000,
            10000000,
            float("inf"),
        ]
        bin_labels = [
            "10-15w",
            "15-20w",
            "20-30w",
            "30-50w",
            "50-100w",
            "100-200w",
            "200-500w",
            "500-1000w",
            "1000w+",
        ]
        bin_counts = [0] * len(bin_labels)
        for w in word_data:
            for i in range(len(bins) - 1):
                if bins[i] <= w < bins[i + 1]:
                    bin_counts[i] += 1
                    break

        fig = go.Figure(
            data=[
                go.Bar(
                    x=bin_labels,
                    y=bin_counts,
                    marker_color=amber,
                    text=bin_counts,
                    textposition="outside",
                )
            ]
        )
        fig.update_layout(
            **_layout(350),
            xaxis=dict(title="字数区间", gridcolor="rgba(128,128,128,0.2)"),
            yaxis=dict(
                title="小说数",
                gridcolor="rgba(128,128,128,0.2)",
                tickformat=",d",
            ),
        )
        ctx["chart_word_dist_json"] = _to_json(fig)

        # 7. Top contests (horizontal bar, log scale)
        top_contests = (
            Contest.objects.annotate(novel_count=Count("novels"))
            .filter(novel_count__gt=0)
            .order_by("-novel_count")[:10]
        )
        contest_labels = [c.name[:12] for c in top_contests]
        contest_data = [c.novel_count for c in top_contests]

        fig = go.Figure(
            data=[
                go.Bar(
                    y=contest_labels[::-1],
                    x=contest_data[::-1],
                    orientation="h",
                    marker_color=colors[: len(contest_labels)],
                    text=[_w(d) for d in contest_data[::-1]],
                    textposition="outside",
                )
            ]
        )
        fig.update_layout(
            **_layout(320),
            yaxis=dict(autorange="reversed"),
            xaxis=dict(type="log", gridcolor="rgba(128,128,128,0.2)"),
        )
        ctx["chart_contests_json"] = _to_json(fig)

        # 8. Genre x Status stacked bar
        genre_status_data = Novel.objects.values("genre", "status").annotate(
            c=Count("id")
        )
        genre_range = list(range(2, 11))
        status_range = list(range(2, 8))
        status_colors = [amber, orange, rose, "#f472b6", "#fbbf24", "#94a3b8"]

        fig = go.Figure()
        for i, s in enumerate(status_range):
            vals = []
            for g in genre_range:
                val = next(
                    (
                        d["c"]
                        for d in genre_status_data
                        if d["genre"] == g and d["status"] == s
                    ),
                    0,
                )
                vals.append(val)
            fig.add_trace(
                go.Bar(
                    x=[GENRE.get_zh(g) for g in genre_range],
                    y=vals,
                    name=STATUS.get_zh(s),
                    marker_color=status_colors[i % len(status_colors)],
                )
            )
        fig.update_layout(
            **_layout(300),
            barmode="stack",
            xaxis=dict(gridcolor="rgba(128,128,128,0.2)"),
            yaxis=dict(title="小说数", gridcolor="rgba(128,128,128,0.2)"),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
        )
        ctx["chart_heatmap_json"] = _to_json(fig)

        # 9. Top 10 novels by click
        top_click = data["all_novels"][:10]
        fig = go.Figure(
            data=[
                go.Bar(
                    y=[n.title[:12] for n in top_click[::-1]],
                    x=[n.click_num or 0 for n in top_click[::-1]],
                    orientation="h",
                    marker_color=amber,
                    text=[_w(n.click_num or 0) for n in top_click[::-1]],
                    textposition="outside",
                )
            ]
        )
        fig.update_layout(
            **_layout(380),
            yaxis=dict(autorange="reversed"),
            xaxis=dict(type="log", gridcolor="rgba(128,128,128,0.2)"),
        )
        ctx["chart_top_click_json"] = _to_json(fig)

        # 10. Top 10 novels by like
        top_like_novels = sorted(
            data["all_novels"], key=lambda n: n.like_num or 0, reverse=True
        )[:10]
        fig = go.Figure(
            data=[
                go.Bar(
                    y=[n.title[:12] for n in top_like_novels[::-1]],
                    x=[n.like_num or 0 for n in top_like_novels[::-1]],
                    orientation="h",
                    marker_color=orange,
                    text=[_w(n.like_num or 0) for n in top_like_novels[::-1]],
                    textposition="outside",
                )
            ]
        )
        fig.update_layout(
            **_layout(380),
            yaxis=dict(autorange="reversed"),
            xaxis=dict(type="log", gridcolor="rgba(128,128,128,0.2)"),
        )
        ctx["chart_top_like_json"] = _to_json(fig)

        # 11. Scatter: click vs like
        sample_novels = Novel.objects.filter(click_num__gt=0, like_num__gt=0).values(
            "click_num", "like_num", "title", "genre"
        )[:3000]
        scatter_x = [n["click_num"] for n in sample_novels]
        scatter_y = [n["like_num"] for n in sample_novels]
        scatter_text = [n["title"][:20] for n in sample_novels]
        scatter_color = [GENRE.get_zh(n["genre"]) for n in sample_novels]

        fig = go.Figure(
            data=[
                go.Scatter(
                    x=scatter_x,
                    y=scatter_y,
                    mode="markers",
                    marker=dict(size=4, opacity=0.5, line=dict(width=0)),
                    text=scatter_text,
                    customdata=scatter_color,
                    hovertemplate="%{text}<br>分类: %{customdata}<br>点击: %{x}<br>收藏: %{y}",
                )
            ]
        )
        fig.update_layout(
            **_layout(350),
            xaxis=dict(title="点击", type="log", gridcolor="rgba(128,128,128,0.2)"),
            yaxis=dict(title="收藏", type="log", gridcolor="rgba(128,128,128,0.2)"),
        )
        ctx["chart_scatter_json"] = _to_json(fig)

        # 12. Banner comparison (2 charts)
        from django.db.models import Q

        banner_stats = Novel.objects.aggregate(
            banner_count=Count("id", filter=Q(has_banner=True)),
            nonbanner_count=Count("id", filter=Q(has_banner=False)),
            banner_click=Sum("click_num", filter=Q(has_banner=True)),
            nonbanner_click=Sum("click_num", filter=Q(has_banner=False)),
            banner_like=Sum("like_num", filter=Q(has_banner=True)),
            nonbanner_like=Sum("like_num", filter=Q(has_banner=False)),
            banner_praise=Sum("praise_num", filter=Q(has_banner=True)),
            nonbanner_praise=Sum("praise_num", filter=Q(has_banner=False)),
        )

        bc = banner_stats["banner_count"] or 1
        nc = banner_stats["nonbanner_count"] or 1

        # Chart 1: Click comparison
        banner_click_per = (banner_stats["banner_click"] or 0) / bc
        nonbanner_click_per = (banner_stats["nonbanner_click"] or 0) / nc
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=["Banner", "非Banner"],
                y=[banner_click_per, nonbanner_click_per],
                marker_color=[amber, "#94a3b8"],
                text=[_w(int(v)) for v in [banner_click_per, nonbanner_click_per]],
                textposition="outside",
            )
        )
        fig.update_layout(
            **_layout(280),
            yaxis=dict(title="人均点击", gridcolor="rgba(128,128,128,0.2)"),
            showlegend=False,
        )
        ctx["chart_banner_click_json"] = _to_json(fig)

        # Chart 2: Engagement comparison (like + praise)
        banner_like_per = (banner_stats["banner_like"] or 0) / bc
        nonbanner_like_per = (banner_stats["nonbanner_like"] or 0) / nc
        banner_praise_per = (banner_stats["banner_praise"] or 0) / bc
        nonbanner_praise_per = (banner_stats["nonbanner_praise"] or 0) / nc
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=["收藏", "点赞"],
                y=[banner_like_per, banner_praise_per],
                name=f"Banner ({bc}部)",
                marker_color=amber,
            )
        )
        fig.add_trace(
            go.Bar(
                x=["收藏", "点赞"],
                y=[nonbanner_like_per, nonbanner_praise_per],
                name=f"非Banner ({nc}部)",
                marker_color="#94a3b8",
            )
        )
        fig.update_layout(
            **_layout(280),
            barmode="group",
            yaxis=dict(title="人均", gridcolor="rgba(128,128,128,0.2)"),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
        )
        ctx["chart_banner_engagement_json"] = _to_json(fig)

        # 13. A-status candidates
        a_criteria = (
            Q(has_banner=True)
            | Q(click_num__gte=10000000)
            | Q(review_num__gte=60)
            | Q(like_num__gte=10000)
            | Q(praise_num__gte=10000)
        )
        a_count = Novel.objects.filter(a_criteria, status__in=[3, 2]).count()
        not_a_count = Novel.objects.filter(~a_criteria, status__in=[3, 2]).count()
        already_a = Novel.objects.filter(status__in=[4, 5]).count()

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=["已是A状态", "符合A条件(待升级)", "不符合A条件"],
                    values=[already_a, a_count, not_a_count],
                    hole=0.5,
                    marker_colors=[amber, orange, "#94a3b8"],
                    textinfo="label+value",
                    textposition="outside",
                )
            ]
        )
        fig.update_layout(**_layout(240), showlegend=False)
        ctx["chart_a_status_json"] = _to_json(fig)

        pages.append(
            (
                "novels/dashboard.html",
                ctx,
                str(output_dir / "dashboard" / "index.html"),
                base_path,
            )
        )

        return pages

    def _collect_404_pages(self, output_dir, base_path):
        """Collect 404 page generation task."""
        pages = []

        context = {}

        pages.append(
            (
                "novels/404.html",
                context,
                str(output_dir / "404.html"),
                base_path,
            )
        )

        return pages
