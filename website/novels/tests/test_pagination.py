from django.test import TestCase
from django.urls import reverse

from novels.models import Novel, Author
from novels.mappings import GENRE, STATUS, PTYPE


class PaginationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(name="Pagination Author")
        for i in range(50):
            Novel.objects.create(
                id=8000 + i,
                title=f"Pagination Novel {i}",
                author=cls.author,
                genre=GENRE.enum.MAGIC.value,
                status=STATUS.enum.FINISHED.value,
                ptype=PTYPE.enum.FREE.value,
                click_num=100 * i,
            )

    def test_first_page(self):
        response = self.client.get(reverse("novels:index"))
        self.assertEqual(response.status_code, 200)

    def test_second_page(self):
        response = self.client.get(reverse("novels:index"), {"page": "2"})
        self.assertEqual(response.status_code, 200)

    def test_last_page(self):
        response = self.client.get(reverse("novels:index"), {"page": "3"})
        self.assertEqual(response.status_code, 200)

    def test_page_beyond_last(self):
        response = self.client.get(reverse("novels:index"), {"page": "999"})
        self.assertEqual(response.status_code, 404)

    def test_page_zero(self):
        response = self.client.get(reverse("novels:index"), {"page": "0"})
        self.assertEqual(response.status_code, 404)

    def test_page_negative(self):
        response = self.client.get(reverse("novels:index"), {"page": "-1"})
        self.assertEqual(response.status_code, 404)

    def test_page_not_a_number(self):
        response = self.client.get(reverse("novels:index"), {"page": "abc"})
        self.assertEqual(response.status_code, 404)

    def test_rank_pagination(self):
        response = self.client.get(reverse("novels:rank"), {"page": "1"})
        self.assertEqual(response.status_code, 200)
