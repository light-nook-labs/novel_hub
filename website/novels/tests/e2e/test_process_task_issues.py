"""Tests for process_task_issues management command."""

import os
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.core.management import call_command

from novels.models import Novel, Author, Task


class ProcessTaskIssuesTest(TestCase):
    """Test the process_task_issues management command."""

    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(name="Test Author")
        cls.novel = Novel.objects.create(
            id=730611,
            title="Test Novel",
            author=cls.author,
        )

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token", "GITHUB_REPO": "test/repo"})
    @patch("novels.management.commands.process_task_issues.requests.get")
    def test_no_issues(self, mock_get):
        """Test when there are no task issues."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        call_command("process_task_issues")
        mock_get.assert_called_once()

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token", "GITHUB_REPO": "test/repo"})
    @patch("novels.management.commands.process_task_issues.requests.get")
    @patch("novels.management.commands.process_task_issues.requests.post")
    @patch("novels.management.commands.process_task_issues.requests.patch")
    def test_process_valid_issue(self, mock_patch, mock_post, mock_get):
        """Test processing a valid task issue."""
        # Mock API responses
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = [
            {
                "number": 1,
                "title": "[Task] 小说 ID: 730611",
                "body": "**小说 ID**: 730611",
            }
        ]
        mock_get_response.raise_for_status.return_value = None
        mock_get.return_value = mock_get_response

        mock_post_response = MagicMock()
        mock_post_response.raise_for_status.return_value = None
        mock_post.return_value = mock_post_response

        mock_patch_response = MagicMock()
        mock_patch_response.raise_for_status.return_value = None
        mock_patch.return_value = mock_patch_response

        # Run command
        call_command("process_task_issues")

        # Verify task was created
        self.assertTrue(Task.objects.filter(novel_id=730611).exists())

        # Verify issue was closed
        mock_patch.assert_called_once()
        patch_call_args = mock_patch.call_args
        self.assertIn("state", patch_call_args[1]["json"])
        self.assertEqual(patch_call_args[1]["json"]["state"], "closed")

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token", "GITHUB_REPO": "test/repo"})
    @patch("novels.management.commands.process_task_issues.requests.get")
    @patch("novels.management.commands.process_task_issues.requests.post")
    @patch("novels.management.commands.process_task_issues.requests.patch")
    def test_process_nonexistent_novel(self, mock_patch, mock_post, mock_get):
        """Test processing issue with non-existent novel ID."""
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = [
            {
                "number": 2,
                "title": "[Task] 小说 ID: 99999",
                "body": "",
            }
        ]
        mock_get_response.raise_for_status.return_value = None
        mock_get.return_value = mock_get_response

        mock_post_response = MagicMock()
        mock_post_response.raise_for_status.return_value = None
        mock_post.return_value = mock_post_response

        mock_patch_response = MagicMock()
        mock_patch_response.raise_for_status.return_value = None
        mock_patch.return_value = mock_patch_response

        call_command("process_task_issues")

        # Task should not be created for non-existent novel
        self.assertFalse(Task.objects.filter(novel_id=99999).exists())

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token", "GITHUB_REPO": "test/repo"})
    @patch("novels.management.commands.process_task_issues.requests.get")
    @patch("novels.management.commands.process_task_issues.requests.post")
    @patch("novels.management.commands.process_task_issues.requests.patch")
    def test_process_duplicate_task(self, mock_patch, mock_post, mock_get):
        """Test processing issue when task already exists."""
        # Create existing task
        Task.objects.create(novel_id=730611, status=Task.Status.URGENT)

        mock_get_response = MagicMock()
        mock_get_response.json.return_value = [
            {
                "number": 3,
                "title": "[Task] 小说 ID: 730611",
                "body": "",
            }
        ]
        mock_get_response.raise_for_status.return_value = None
        mock_get.return_value = mock_get_response

        mock_post_response = MagicMock()
        mock_post_response.raise_for_status.return_value = None
        mock_post.return_value = mock_post_response

        mock_patch_response = MagicMock()
        mock_patch_response.raise_for_status.return_value = None
        mock_patch.return_value = mock_patch_response

        # Should not raise
        call_command("process_task_issues")

        # Still only one task
        self.assertEqual(Task.objects.filter(novel_id=730611).count(), 1)

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token", "GITHUB_REPO": "test/repo"})
    @patch("novels.management.commands.process_task_issues.requests.get")
    @patch("novels.management.commands.process_task_issues.requests.post")
    @patch("novels.management.commands.process_task_issues.requests.patch")
    def test_extract_nid_from_title(self, mock_patch, mock_post, mock_get):
        """Test extracting novel ID from various title formats."""
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = [
            {
                "number": 4,
                "title": "[Task] 小说 ID: 12345",
                "body": "",
            }
        ]
        mock_get_response.raise_for_status.return_value = None
        mock_get.return_value = mock_get_response

        mock_post_response = MagicMock()
        mock_post_response.raise_for_status.return_value = None
        mock_post.return_value = mock_post_response

        mock_patch_response = MagicMock()
        mock_patch_response.raise_for_status.return_value = None
        mock_patch.return_value = mock_patch_response

        # Create novel with ID 12345
        Novel.objects.create(id=12345, title="Another Novel", author=self.author)

        call_command("process_task_issues")

        self.assertTrue(Task.objects.filter(novel_id=12345).exists())

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token", "GITHUB_REPO": "test/repo"})
    @patch("novels.management.commands.process_task_issues.requests.get")
    @patch("novels.management.commands.process_task_issues.requests.post")
    @patch("novels.management.commands.process_task_issues.requests.patch")
    def test_invalid_title_closed_with_error(self, mock_patch, mock_post, mock_get):
        """Test that issues with invalid titles are closed with error message."""
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = [
            {
                "number": 5,
                "title": "Invalid Title",
                "body": "",
            }
        ]
        mock_get_response.raise_for_status.return_value = None
        mock_get.return_value = mock_get_response

        mock_post_response = MagicMock()
        mock_post_response.raise_for_status.return_value = None
        mock_post.return_value = mock_post_response

        mock_patch_response = MagicMock()
        mock_patch_response.raise_for_status.return_value = None
        mock_patch.return_value = mock_patch_response

        call_command("process_task_issues")

        # Verify issue was closed
        mock_patch.assert_called_once()

        # Verify comment contains error message
        comment_call = mock_post.call_args
        comment_body = comment_call[1]["json"]["body"]
        self.assertIn("未找到有效的小说 ID", comment_body)

    @patch.dict(os.environ, {"GITHUB_TOKEN": "", "GITHUB_REPO": ""})
    def test_missing_env_vars(self):
        """Test that command fails gracefully without env vars."""
        # Should not raise, just print error
        call_command("process_task_issues")

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token", "GITHUB_REPO": "test/repo"})
    @patch("novels.management.commands.process_task_issues.requests.get")
    @patch("novels.management.commands.process_task_issues.requests.post")
    @patch("novels.management.commands.process_task_issues.requests.patch")
    def test_multiple_issues(self, mock_patch, mock_post, mock_get):
        """Test processing multiple issues in one run."""
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = [
            {
                "number": 10,
                "title": "[Task] 小说 ID: 730611",
                "body": "",
            },
            {
                "number": 11,
                "title": "[Task] 小说 ID: 12345",
                "body": "",
            },
        ]
        mock_get_response.raise_for_status.return_value = None
        mock_get.return_value = mock_get_response

        mock_post_response = MagicMock()
        mock_post_response.raise_for_status.return_value = None
        mock_post.return_value = mock_post_response

        mock_patch_response = MagicMock()
        mock_patch_response.raise_for_status.return_value = None
        mock_patch.return_value = mock_patch_response

        # Create second novel
        Novel.objects.create(id=12345, title="Another Novel", author=self.author)

        call_command("process_task_issues")

        # Both tasks should be created
        self.assertTrue(Task.objects.filter(novel_id=730611).exists())
        self.assertTrue(Task.objects.filter(novel_id=12345).exists())

        # Both issues should be closed
        self.assertEqual(mock_patch.call_count, 2)
