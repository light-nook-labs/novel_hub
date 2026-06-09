from django.test import TestCase, Client
from django.urls import reverse

from .models import Novel, Author, Tag, Contest


class NovelListViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(name="Test Author")
        cls.novel = Novel.objects.create(
            id=1001,
            title="Test Novel",
            author=cls.author,
            genre=1,
            status=2,
            ptype=1,
            click_num=1000,
            word_num=50000,
        )

    def test_index_status_code(self):
        response = self.client.get(reverse("novels:index"))
        self.assertEqual(response.status_code, 200)

    def test_index_template(self):
        response = self.client.get(reverse("novels:index"))
        self.assertTemplateUsed(response, "novels/index.html")

    def test_index_search(self):
        response = self.client.get(reverse("novels:index"), {"q": "Test"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Novel")

    def test_index_filter_genre(self):
        response = self.client.get(reverse("novels:index"), {"genre": "1"})
        self.assertEqual(response.status_code, 200)

    def test_index_filter_status(self):
        response = self.client.get(reverse("novels:index"), {"status": "2"})
        self.assertEqual(response.status_code, 200)

    def test_index_sort(self):
        response = self.client.get(reverse("novels:index"), {"sort": "click_num"})
        self.assertEqual(response.status_code, 200)


class NovelDetailViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(name="Test Author")
        cls.novel = Novel.objects.create(
            id=1001,
            title="Test Novel",
            author=cls.author,
            genre=1,
            status=2,
            ptype=1,
        )

    def test_detail_status_code(self):
        response = self.client.get(reverse("novels:detail", args=[1001]))
        self.assertEqual(response.status_code, 200)

    def test_detail_template(self):
        response = self.client.get(reverse("novels:detail", args=[1001]))
        self.assertTemplateUsed(response, "novels/detail.html")

    def test_detail_404(self):
        response = self.client.get(reverse("novels:detail", args=[9999]))
        self.assertEqual(response.status_code, 404)


class NovelRankViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(name="Test Author")
        for i in range(3):
            Novel.objects.create(
                id=2000 + i,
                title=f"Rank Novel {i}",
                author=cls.author,
                genre=1,
                status=2,
                ptype=1,
                click_num=100 * i,
            )

    def test_rank_status_code(self):
        response = self.client.get(reverse("novels:rank"))
        self.assertEqual(response.status_code, 200)

    def test_rank_sort(self):
        response = self.client.get(
            reverse("novels:rank"), {"sort": "click_num", "dir": "asc"}
        )
        self.assertEqual(response.status_code, 200)


class AuthorViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(name="Test Author")
        Novel.objects.create(
            id=3001,
            title="Author Novel",
            author=cls.author,
            genre=1,
            status=2,
            ptype=1,
        )

    def test_author_list(self):
        response = self.client.get(reverse("novels:authors"))
        self.assertEqual(response.status_code, 200)

    def test_author_search(self):
        response = self.client.get(reverse("novels:authors"), {"q": "Test"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Author")

    def test_author_detail(self):
        response = self.client.get(
            reverse("novels:author_detail", args=[self.author.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Author")


class TagViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tag = Tag.objects.create(name="Test Tag")
        cls.author = Author.objects.create(name="Author")
        cls.novel = Novel.objects.create(
            id=4001,
            title="Tag Novel",
            author=cls.author,
            genre=1,
            status=2,
            ptype=1,
        )
        cls.novel.tags.add(cls.tag)

    def test_tag_list(self):
        response = self.client.get(reverse("novels:tags"))
        self.assertEqual(response.status_code, 200)

    def test_tag_detail(self):
        response = self.client.get(reverse("novels:tag_detail", args=[self.tag.id]))
        self.assertEqual(response.status_code, 200)


class ContestViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.contest = Contest.objects.create(name="Test Contest")
        cls.author = Author.objects.create(name="Author")
        Novel.objects.create(
            id=5001,
            title="Contest Novel",
            author=cls.author,
            contest=cls.contest,
            genre=1,
            status=2,
            ptype=1,
        )

    def test_contest_list(self):
        response = self.client.get(reverse("novels:contests"))
        self.assertEqual(response.status_code, 200)

    def test_contest_detail(self):
        response = self.client.get(
            reverse("novels:contest_detail", args=[self.contest.id])
        )
        self.assertEqual(response.status_code, 200)


class BannerViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(name="Author")
        Novel.objects.create(
            id=6001,
            title="Banner Novel",
            author=cls.author,
            genre=1,
            status=2,
            ptype=1,
            has_banner=True,
        )

    def test_banner_list(self):
        response = self.client.get(reverse("novels:banners"))
        self.assertEqual(response.status_code, 200)


class EnumViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(name="Author")
        Novel.objects.create(
            id=7001,
            title="Enum Novel",
            author=cls.author,
            genre=2,
            status=2,
            ptype=1,
        )

    def test_enum_list(self):
        response = self.client.get(reverse("novels:enum_list", args=["genre"]))
        self.assertEqual(response.status_code, 200)

    def test_enum_detail(self):
        response = self.client.get(reverse("novels:enum_detail", args=["genre", 2]))
        self.assertEqual(response.status_code, 200)

    def test_enum_404(self):
        response = self.client.get(reverse("novels:enum_list", args=["invalid"]))
        self.assertEqual(response.status_code, 404)
