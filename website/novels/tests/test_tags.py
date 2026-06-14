from django.test import TestCase

from novels.models import Author, Tag


class TemplateTagTests(TestCase):
    def test_truncate_cjk_ascii(self):
        from novels.templatetags.novel_tags import truncate_cjk

        self.assertEqual(truncate_cjk("hello", 10), "hello")

    def test_truncate_cjk_cjk(self):
        from novels.templatetags.novel_tags import truncate_cjk

        result = truncate_cjk("你好世界test", 10)
        self.assertEqual(result, "你好世界t…")

    def test_truncate_cjk_none(self):
        from novels.templatetags.novel_tags import truncate_cjk

        self.assertEqual(truncate_cjk(None, 10), "")

    def test_truncate_cjk_exact_width(self):
        from novels.templatetags.novel_tags import truncate_cjk

        self.assertEqual(truncate_cjk("你好", 4), "你好")

    def test_cover_url_none(self):
        from novels.templatetags.novel_tags import cover_url

        result = cover_url(None)
        self.assertIn("defaultNew.jpg", result)

    def test_cover_url_suffix(self):
        from novels.templatetags.novel_tags import cover_url

        result = cover_url("test.jpg")
        self.assertTrue(result.endswith("test.jpg"))

    def test_cover_url_http_upgrade(self):
        from novels.templatetags.novel_tags import cover_url

        result = cover_url("http://example.com/img.jpg")
        self.assertTrue(result.startswith("https://"))

    def test_humanize_num_none(self):
        from novels.templatetags.novel_tags import humanize_num

        self.assertEqual(humanize_num(None), "-")

    def test_humanize_num_small(self):
        from novels.templatetags.novel_tags import humanize_num

        self.assertEqual(humanize_num(999), "999")

    def test_humanize_num_large(self):
        from novels.templatetags.novel_tags import humanize_num

        self.assertEqual(humanize_num(15000), "1.5w+")

    def test_pill_bg_none(self):
        from novels.templatetags.novel_tags import pill_bg

        self.assertEqual(pill_bg(None, "tag"), "")

    def test_pill_bg_valid(self):
        from novels.templatetags.novel_tags import pill_bg

        tag = Tag(id=1, name="test")
        result = pill_bg(tag, "tag")
        self.assertTrue(result.startswith("hsl("))

    def test_detail_url_none(self):
        from novels.templatetags.novel_tags import detail_url

        self.assertEqual(detail_url(None, "novels:tag_detail"), "")

    def test_detail_url_valid(self):
        from novels.templatetags.novel_tags import detail_url

        tag = Tag(id=1, name="test")
        result = detail_url(tag, "novels:tag_detail")
        self.assertIn("/tags/1/", result)

    def test_get_attr_valid(self):
        from novels.templatetags.novel_tags import get_attr

        author = Author(id=1, name="Test")
        self.assertEqual(get_attr(author, "name"), "Test")

    def test_get_attr_none(self):
        from novels.templatetags.novel_tags import get_attr

        self.assertEqual(get_attr(None, "name"), "")
