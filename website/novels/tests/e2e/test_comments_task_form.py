"""E2E tests for comments page task form using Playwright."""

import re
import urllib.parse
from django.test import LiveServerTestCase
from playwright.sync_api import sync_playwright, expect


class CommentsTaskFormE2ETest(LiveServerTestCase):
    """Test the task submission form on the comments page."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        super().tearDownClass()

    def setUp(self):
        self.page = self.browser.new_page()

    def tearDown(self):
        self.page.close()

    def test_comments_page_loads(self):
        """Test that the comments page loads correctly."""
        self.page.goto(f"{self.live_server_url}/comments/")
        expect(self.page.locator("h1")).to_contain_text("评论")
        expect(self.page.locator("h2").first).to_contain_text("提交任务")

    def test_task_form_elements_exist(self):
        """Test that all task form elements are present."""
        self.page.goto(f"{self.live_server_url}/comments/")

        form = self.page.locator("#task-form")
        expect(form).to_be_visible()

        input_field = self.page.locator("#task-nid")
        expect(input_field).to_be_visible()
        expect(input_field).to_have_attribute("type", "number")
        expect(input_field).to_have_attribute("min", "10000")
        expect(input_field).to_have_attribute("max", "9999999")

        submit_btn = self.page.locator("#task-form button[type='submit']")
        expect(submit_btn).to_be_visible()
        expect(submit_btn).to_contain_text("提交")

    def test_valid_id_opens_github_issue(self):
        """Test that submitting valid ID opens GitHub issue with correct template."""
        self.page.goto(f"{self.live_server_url}/comments/")

        input_field = self.page.locator("#task-nid")
        input_field.fill("730611")

        # Intercept window.open to capture the URL
        self.page.evaluate("""
            window._openedUrl = null;
            window.open = function(url) {
                window._openedUrl = url;
                return null;
            };
        """)

        self.page.locator("#task-form button[type='submit']").click()

        opened_url = self.page.evaluate("window._openedUrl")

        self.assertIn("template=task.yml", opened_url)
        self.assertIn("novel-id=730611", opened_url)
        self.assertIn("github.com/light-nook-labs/novel_hub/issues/new", opened_url)

        result = self.page.locator("#task-result")
        expect(result).to_be_visible()
        expect(result).to_contain_text("已跳转到 GitHub")
        expect(result).to_have_class(re.compile(r"text-green"))

        expect(input_field).to_have_value("")

    def test_valid_id_range_boundary_min(self):
        """Test that minimum valid ID (10000) is accepted."""
        self.page.goto(f"{self.live_server_url}/comments/")

        input_field = self.page.locator("#task-nid")
        input_field.fill("10000")

        self.page.evaluate("""
            window._openedUrl = null;
            window.open = function(url) {
                window._openedUrl = url;
                return null;
            };
        """)

        self.page.locator("#task-form button[type='submit']").click()
        opened_url = self.page.evaluate("window._openedUrl")
        self.assertIn("novel-id=10000", opened_url)

    def test_valid_id_range_boundary_max(self):
        """Test that maximum valid ID (9999999) is accepted."""
        self.page.goto(f"{self.live_server_url}/comments/")

        input_field = self.page.locator("#task-nid")
        input_field.fill("9999999")

        self.page.evaluate("""
            window._openedUrl = null;
            window.open = function(url) {
                window._openedUrl = url;
                return null;
            };
        """)

        self.page.locator("#task-form button[type='submit']").click()
        opened_url = self.page.evaluate("window._openedUrl")
        self.assertIn("novel-id=9999999", opened_url)

    def test_giscus_container_exists(self):
        """Test that GISCUS container is present."""
        self.page.goto(f"{self.live_server_url}/comments/")

        giscus_container = self.page.locator("#giscus-container")
        expect(giscus_container).to_be_visible()

    def test_github_issue_url_format(self):
        """Test that the generated GitHub issue URL has correct format."""
        self.page.goto(f"{self.live_server_url}/comments/")

        input_field = self.page.locator("#task-nid")
        input_field.fill("123456")

        self.page.evaluate("""
            window._openedUrl = null;
            window.open = function(url) {
                window._openedUrl = url;
                return null;
            };
        """)

        self.page.locator("#task-form button[type='submit']").click()
        opened_url = self.page.evaluate("window._openedUrl")

        # Verify URL structure
        self.assertTrue(opened_url.startswith("https://github.com/"))
        self.assertIn("/issues/new?", opened_url)
        self.assertIn("template=task.yml", opened_url)
        self.assertIn("title=", opened_url)
        self.assertIn("novel-id=", opened_url)

        # Verify title is URL encoded
        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(opened_url).query)
        self.assertIn("[Task] 小说 ID: 123456", parsed.get("title", [""])[0])
        self.assertEqual(parsed.get("novel-id", [""])[0], "123456")

    def test_multiple_submissions(self):
        """Test that form can be submitted multiple times."""
        self.page.goto(f"{self.live_server_url}/comments/")

        input_field = self.page.locator("#task-nid")

        # First submission
        input_field.fill("11111")
        self.page.evaluate("""
            window._openedUrl = null;
            window.open = function(url) {
                window._openedUrl = url;
                return null;
            };
        """)
        self.page.locator("#task-form button[type='submit']").click()
        first_url = self.page.evaluate("window._openedUrl")
        self.assertIn("novel-id=11111", first_url)

        # Second submission
        input_field.fill("22222")
        self.page.evaluate("""
            window._openedUrl = null;
            window.open = function(url) {
                window._openedUrl = url;
                return null;
            };
        """)
        self.page.locator("#task-form button[type='submit']").click()
        second_url = self.page.evaluate("window._openedUrl")
        self.assertIn("novel-id=22222", second_url)


class TaskFormIntegrationTest(LiveServerTestCase):
    """Integration tests for task form functionality without browser."""

    def test_comments_view_returns_200(self):
        """Test that comments view returns 200."""
        response = self.client.get("/comments/")
        self.assertEqual(response.status_code, 200)

    def test_comments_template_used(self):
        """Test that correct template is used."""
        response = self.client.get("/comments/")
        self.assertTemplateUsed(response, "novels/comments.html")

    def test_comments_contains_form(self):
        """Test that response contains the task form."""
        response = self.client.get("/comments/")
        self.assertContains(response, 'id="task-form"')
        self.assertContains(response, 'id="task-nid"')
        self.assertContains(response, 'type="submit"')

    def test_comments_contains_giscus(self):
        """Test that response contains GISCUS container."""
        response = self.client.get("/comments/")
        self.assertContains(response, 'id="giscus-container"')
        self.assertContains(response, "giscus.app")

    def test_comments_contains_validation(self):
        """Test that response contains validation attributes."""
        response = self.client.get("/comments/")
        self.assertContains(response, 'min="10000"')
        self.assertContains(response, 'max="9999999"')
        self.assertContains(response, 'pattern="\\d{5,7}"')

    def test_comments_contains_github_template_url(self):
        """Test that JavaScript contains correct GitHub template URL."""
        response = self.client.get("/comments/")
        self.assertContains(response, "template=task.yml")
        self.assertContains(response, "novel-id=")
