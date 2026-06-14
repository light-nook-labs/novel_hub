from django.test import TestCase
from django.urls import reverse

from novels.models import Novel, Author
from novels.mappings import GENRE, STATUS, PTYPE


class SearchBoundaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(name="Test Author")
        cls.novel = Novel.objects.create(
            id=9001,
            title="Search Test Novel",
            author=cls.author,
            genre=GENRE.enum.MAGIC.value,
            status=STATUS.enum.FINISHED.value,
            ptype=PTYPE.enum.FREE.value,
        )

    def test_search_empty_query(self):
        response = self.client.get(reverse("novels:index"), {"q": ""})
        self.assertEqual(response.status_code, 200)

    def test_search_whitespace_only(self):
        response = self.client.get(reverse("novels:index"), {"q": "   "})
        self.assertEqual(response.status_code, 200)

    def test_search_special_chars(self):
        response = self.client.get(
            reverse("novels:index"), {"q": "<script>alert(1)</script>"}
        )
        self.assertEqual(response.status_code, 200)
        # Django auto-escapes HTML, so check for escaped version
        self.assertContains(response, "&lt;script&gt;")

    def test_search_sql_injection(self):
        response = self.client.get(
            reverse("novels:index"), {"q": "'; DROP TABLE novels;--"}
        )
        self.assertEqual(response.status_code, 200)

    def test_search_found(self):
        response = self.client.get(reverse("novels:index"), {"q": "Search Test"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Search Test Novel")

    def test_search_not_found(self):
        response = self.client.get(reverse("novels:index"), {"q": "nonexistent_xyz"})
        self.assertEqual(response.status_code, 200)

    def test_author_search_empty(self):
        response = self.client.get(reverse("novels:authors"), {"q": ""})
        self.assertEqual(response.status_code, 200)

    def test_filter_invalid_value(self):
        response = self.client.get(reverse("novels:index"), {"genre": "abc"})
        self.assertEqual(response.status_code, 200)

    def test_filter_negative_value(self):
        response = self.client.get(reverse("novels:index"), {"genre": "-1"})
        self.assertEqual(response.status_code, 200)
