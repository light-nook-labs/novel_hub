"""Management command to generate static site for GitHub Pages.

Generates:
- index.html (1 page)
- about.html (1 page)
- authors/ (10 pages)
- rank/ (100 pages)
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
from django.template.loader import render_to_string
from django.test import RequestFactory

from novels.models import Author, Novel
from novels.views import AuthorListView, NovelRankView, NovelListView, COLUMNS

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

        # Collect all pages to generate
        pages = []

        # 1. Index page (1 page)
        pages.extend(self._collect_index_pages(output_dir, base_path))

        # 2. About page (1 page)
        pages.extend(self._collect_about_pages(output_dir, base_path))

        # 3. Authors pages (10 pages)
        pages.extend(self._collect_author_pages(output_dir, base_path))

        # 4. Rank pages (100 pages)
        pages.extend(self._collect_rank_pages(output_dir, base_path))

        # 5. Banner pages (all pages)
        pages.extend(self._collect_banner_pages(output_dir, base_path))

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

    def _copy_static_files(self, output_dir, base_path):
        """Copy static files to output directory."""
        # Find static root
        static_root = Path(settings.STATIC_ROOT) if settings.STATIC_ROOT else None
        staticfiles_dirs = settings.STATICFILES_DIRS

        # Try STATIC_ROOT first, then STATICFILES_DIRS
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

        # Copy static files
        static_output = output_dir / "static"
        static_output.mkdir(parents=True, exist_ok=True)

        for source_dir in source_dirs:
            if source_dir.exists():
                logger.info("Copying static files from %s", source_dir)
                shutil.copytree(source_dir, static_output, dirs_exist_ok=True)

        logger.info("Static files copied to %s", static_output)

    def _collect_index_pages(self, output_dir, base_path):
        """Collect index page generation tasks."""
        pages = []

        # Get novels for index (default sort: -click_num)
        novels = (
            Novel.objects.select_related("author", "contest")
            .prefetch_related("tags")
            .order_by("-click_num")[:24]
        )

        # Get latest banner
        latest_banner = Novel.objects.filter(has_banner=True).order_by("-last_update").first()

        context = {
            "novels": novels,
            "latest_banner": latest_banner,
            "page_obj": None,
            "is_paginated": False,
        }

        pages.append((
            "novels/index.html",
            context,
            str(output_dir / "index.html"),
            base_path,
        ))

        return pages

    def _collect_about_pages(self, output_dir, base_path):
        """Collect about page generation tasks."""
        pages = []

        context = {
            "novel_count": Novel.objects.count(),
            "author_count": Author.objects.count(),
        }

        pages.append((
            "novels/about.html",
            context,
            str(output_dir / "about" / "index.html"),
            base_path,
        ))

        return pages

    def _collect_author_pages(self, output_dir, base_path):
        """Collect author pages generation tasks."""
        pages = []
        per_page = 100

        # Get total author count
        total_authors = Author.objects.count()
        total_pages = min(AUTHORS_PAGES, (total_authors + per_page - 1) // per_page)

        for page_num in range(1, total_pages + 1):
            # Get authors for this page (default sort: -total_click)
            start = (page_num - 1) * per_page
            end = start + per_page

            from django.db.models import Subquery, OuterRef, Count, Sum, Max

            top_novel = (
                Novel.objects.filter(author=OuterRef("pk"))
                .order_by("-click_num")
                .values("id", "title", "click_num")[:1]
            )

            authors = (
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
                    top_novel_id=Subquery(top_novel.values("id")),
                    top_novel_title=Subquery(top_novel.values("title")),
                    top_novel_click=Subquery(top_novel.values("click_num")),
                )
                .order_by("-total_click", "-novel_count")
            )

            paginator = SimplePaginator(total_authors, per_page)
            page_obj = SimplePage(page_num, paginator)

            # Get authors for this page
            page_authors = list(authors[start:end])

            context = {
                "authors": page_authors,
                "page_obj": page_obj,
                "is_paginated": total_pages > 1,
                "sort_options": AuthorListView.SORT_OPTIONS,
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

    def _collect_rank_pages(self, output_dir, base_path):
        """Collect rank pages generation tasks."""
        pages = []
        per_page = 100

        # Get total novel count
        total_novels = Novel.objects.count()
        total_pages = min(RANK_PAGES, (total_novels + per_page - 1) // per_page)

        for page_num in range(1, total_pages + 1):
            # Get novels for this page (default sort: -click_num)
            start = (page_num - 1) * per_page
            end = start + per_page

            novels = (
                Novel.objects.select_related("author", "contest")
                .prefetch_related("tags")
                .order_by("-click_num")
            )

            paginator = SimplePaginator(total_novels, per_page)
            page_obj = SimplePage(page_num, paginator)

            # Get novels for this page
            page_novels = list(novels[start:end])

            context = {
                "novels": page_novels,
                "page_obj": page_obj,
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

    def _collect_banner_pages(self, output_dir, base_path):
        """Collect banner pages generation tasks (all pages)."""
        pages = []
        per_page = 12

        # Get total banner count
        total_banners = Novel.objects.filter(has_banner=True).count()
        total_pages = (total_banners + per_page - 1) // per_page

        for page_num in range(1, total_pages + 1):
            start = (page_num - 1) * per_page
            end = start + per_page

            novels = (
                Novel.objects.filter(has_banner=True)
                .select_related("author", "contest")
                .prefetch_related("tags")
                .order_by("-last_update")
            )

            paginator = SimplePaginator(total_banners, per_page)
            page_obj = SimplePage(page_num, paginator)

            page_novels = list(novels[start:end])

            context = {
                "novels": page_novels,
                "page_obj": page_obj,
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
