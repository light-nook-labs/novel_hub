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
from novels.views import AuthorListView, COLUMNS
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
        logger.info("Data fetched: %d novels, %d authors", data["novel_count"], data["author_count"])

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

        # 6. 404 page (1 page)
        pages.extend(self._collect_404_pages(output_dir, base_path))

        logger.info("Generating %d static pages with %d workers...", len(pages), workers)

        # Generate pages using multiprocessing
        generated = 0
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_generate_page, page): page for page in pages}

            for future in progress(as_completed(futures), desc="Generating", total=len(pages)):
                try:
                    result = future.result()
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
                "id", "title", "has_banner", "word_num", "click_num",
                "like_num", "praise_num", "review_num", "comment_num",
                "last_update", "genre", "status", "ptype", "cover",
                "author__name", "contest__name",
            )
        )

        # Get banner novels
        logger.info("Filtering banner novels...")
        banner_novels = [n for n in all_novels if n.has_banner]
        banner_novels.sort(key=lambda n: n.last_update or "", reverse=True)

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
                latest_update=Max("novels__last_update"),
            )
            .order_by("-total_click", "-novel_count")
        )

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

        pages.append((
            "novels/index.html",
            context,
            str(output_dir / "index.html"),
            base_path,
        ))

        return pages

    def _collect_about_pages(self, output_dir, base_path, data):
        """Collect about page generation tasks."""
        pages = []

        context = {
            "novel_count": data["novel_count"],
            "author_count": data["author_count"],
        }

        pages.append((
            "novels/about.html",
            context,
            str(output_dir / "about" / "index.html"),
            base_path,
        ))

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

            pages.append((
                "novels/authors.html",
                context,
                output_path,
                base_path,
            ))

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

            pages.append((
                "novels/rank.html",
                context,
                output_path,
                base_path,
            ))

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

            pages.append((
                "novels/banners.html",
                context,
                output_path,
                base_path,
            ))

        return pages

    def _collect_404_pages(self, output_dir, base_path):
        """Collect 404 page generation task."""
        pages = []

        context = {}

        pages.append((
            "novels/404.html",
            context,
            str(output_dir / "404.html"),
            base_path,
        ))

        return pages
