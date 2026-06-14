"""Management command to process task issues from GitHub.

Reads open issues with 'task' label, extracts novel IDs, adds to Task table.
Closes issues after processing.

Usage:
    uv run python manage.py process_task_issues

Requires GITHUB_TOKEN and GITHUB_REPO environment variables.
"""

import os
import re

import requests
from django.core.management.base import BaseCommand
from django.db import transaction

from novels.models import Author, Novel, Task
from utils import fetch_html
from utils.logger import get_logger

logger = get_logger(__name__)

GITHUB_API = "https://api.github.com"


class Command(BaseCommand):
    help = "Process task issues from GitHub"

    def handle(self, *args, **options):
        token = os.environ.get("GITHUB_TOKEN")
        repo = os.environ.get("GITHUB_REPO")

        if not token or not repo:
            self.stdout.write(
                self.style.ERROR(
                    "GITHUB_TOKEN and GITHUB_REPO environment variables required"
                )
            )
            return

        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

        # Get open issues with 'task' label
        url = f"{GITHUB_API}/repos/{repo}/issues"
        params = {"labels": "task", "state": "open", "per_page": 100}

        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        issues = resp.json()

        if not issues:
            self.stdout.write(self.style.SUCCESS("No task issues found."))
            return

        logger.info("Found %d task issues", len(issues))

        processed = 0
        failed = 0
        created_tasks = 0

        for issue in issues:
            issue_number = issue["number"]
            title = issue["title"]
            body = issue.get("body", "")

            try:
                nid = self._extract_nid(title, body)
                if not nid:
                    logger.warning("No novel ID found in issue #%d", issue_number)
                    self._close_issue(
                        headers,
                        repo,
                        issue_number,
                        "❌ 未找到有效的小说 ID（需要5-7位纯数字）",
                    )
                    failed += 1
                    continue

                # Add task
                result = self._add_task(nid)
                processed += 1

                if result == "created":
                    created_tasks += 1
                    comment = (
                        f"✅ 已收到任务提交\n\n"
                        f"**小说 ID**: {nid}\n\n"
                        f"任务已加入队列，将在下次 Run Tasks 时处理。"
                    )
                elif result == "created_pending":
                    created_tasks += 1
                    comment = (
                        f"✅ 已收到任务提交\n\n"
                        f"**小说 ID**: {nid}\n\n"
                        f"小说不在数据库中，已创建待处理条目并加入爬取队列。"
                    )
                elif result == "exists":
                    comment = (
                        f"⚠️ 任务已存在\n\n"
                        f"**小说 ID**: {nid}\n\n"
                        f"该任务已在队列中，无需重复提交。"
                    )
                else:  # not_found
                    comment = (
                        f"❌ 小说不存在\n\n"
                        f"**小说 ID**: {nid}\n\n"
                        f"sfacg.com 上未找到该小说，请检查 ID 是否正确。"
                    )

                self._close_issue(headers, repo, issue_number, comment)

                logger.info("Processed issue #%d: %s", issue_number, nid)

            except Exception as e:
                logger.error("Failed to process issue #%d: %s", issue_number, e)
                failed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Processed: {processed}, Failed: {failed}, "
                f"Tasks created: {created_tasks}"
            )
        )

    def _extract_nid(self, title, body):
        """Extract single novel ID from issue title or body."""
        # Title format: [Task] 小说 ID: 123456
        match = re.search(r"\[Task\]\s*小说\s*ID:\s*(\d{5,7})", title)
        if match:
            return match.group(1)

        # Body format: **小说 ID**: 123456
        match = re.search(r"\*\*小说\s*ID\*\*:\s*(\d{5,7})", body)
        if match:
            return match.group(1)

        # Fallback: any 5-7 digit number in title
        match = re.search(r"\b(\d{5,7})\b", title)
        if match:
            return match.group(1)

        return None

    def _add_task(self, nid):
        """Add task for novel ID.

        Returns:
            'created': task created for existing novel
            'created_pending': novel not in DB, created minimal entry + task
            'exists': task already exists
            'not_found': novel doesn't exist anywhere
        """
        nid = int(nid)

        # Check if novel exists in DB
        if Novel.objects.filter(id=nid).exists():
            # Check if task already exists
            if Task.objects.filter(novel_id=nid).exists():
                logger.info("Task for novel %d already exists, skipping", nid)
                return "exists"

            with transaction.atomic():
                Task.objects.create(novel_id=nid, status=Task.Status.URGENT)
            return "created"

        # Novel not in DB, try to fetch from sfacg.com
        logger.info("Novel %d not in DB, checking sfacg.com...", nid)
        try:
            session = requests.Session()
            html_data = fetch_html(session, nid)
            title = html_data.get("title", "")
            author_name = html_data.get("author", "")

            if not title:
                logger.warning("Novel %d: no title found, skipping", nid)
                return "not_found"

            # Create minimal novel entry
            with transaction.atomic():
                author = None
                if author_name:
                    author, _ = Author.objects.get_or_create(name=author_name)

                Novel.objects.create(
                    id=nid,
                    title=title,
                    author=author,
                    status=1,  # Default status
                )
                Task.objects.create(novel_id=nid, status=Task.Status.DEFAULT)

            logger.info("Created pending novel %d: %s", nid, title)
            return "created_pending"

        except Exception as e:
            logger.warning("Novel %d not found on sfacg.com: %s", nid, e)
            return "not_found"

    def _close_issue(self, headers, repo, issue_number, comment):
        """Add comment and close issue."""
        # Add comment
        url = f"{GITHUB_API}/repos/{repo}/issues/{issue_number}/comments"
        requests.post(
            url, headers=headers, json={"body": comment}, timeout=30
        ).raise_for_status()

        # Close issue
        url = f"{GITHUB_API}/repos/{repo}/issues/{issue_number}"
        requests.patch(
            url, headers=headers, json={"state": "closed"}, timeout=30
        ).raise_for_status()
