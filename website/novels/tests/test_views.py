from django.test import TestCase
from django.urls import reverse

from novels.models import Novel, Author, Tag, Contest
from novels.mappings import GENRE, STATUS, PTYPE


# ── Novel views ──────────────────────────────────────────────────────


class NovelListViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(name="Test Author")
        cls.novel = Novel.objects.create(
            id=1001,
            title="Test Novel",
            author=cls.author,
            genre=GENRE.enum.MAGIC.value,
            status=STATUS.enum.FINISHED.value,
            ptype=PTYPE.enum.FREE.value,
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
        response = self.client.get(
            reverse("novels:index"), {"genre": str(GENRE.enum.MAGIC.value)}
        )
        self.assertEqual(response.status_code, 200)

    def test_index_filter_status(self):
        response = self.client.get(
            reverse("novels:index"), {"status": str(STATUS.enum.FINISHED.value)}
        )
        self.assertEqual(response.status_code, 200)

    def test_index_sort_click_num(self):
        response = self.client.get(
            reverse("novels:index"), {"sort": "click_num"}
        )
        self.assertEqual(response.status_code, 200)

    def test_index_sort_word_num(self):
        response = self.client.get(
            reverse("novels:index"), {"sort": "word_num"}
        )
        self.assertEqual(response.status_code, 200)

    def test_index_invalid_sort(self):
        response = self.client.get(reverse("novels:index"), {"sort": "invalid"})
        self.assertEqual(response.status_code, 200)

    def test_index_queries(self):
        with self.assertNumQueries(4):
            self.client.get(reverse("novels:index"))


class NovelDetailViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(name="Test Author")
        cls.novel = Novel.objects.create(
            id=1001,
            title="Test Novel",
            author=cls.author,
            genre=GENRE.enum.MAGIC.value,
            status=STATUS.enum.FINISHED.value,
            ptype=PTYPE.enum.FREE.value,
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

    def test_detail_contains_title(self):
        response = self.client.get(reverse("novels:detail", args=[1001]))
        self.assertContains(response, "Test Novel")

    def test_detail_queries(self):
        with self.assertNumQueries(2):
            self.client.get(reverse("novels:detail", args=[1001]))


class NovelRankViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(name="Test Author")
        for i in range(3):
            Novel.objects.create(
                id=2000 + i,
                title=f"Rank Novel {i}",
                author=cls.author,
                genre=GENRE.enum.MAGIC.value,
                status=STATUS.enum.FINISHED.value,
                ptype=PTYPE.enum.FREE.value,
                click_num=100 * i,
            )

    def test_rank_status_code(self):
        response = self.client.get(reverse("novels:rank"))
        self.assertEqual(response.status_code, 200)

    def test_rank_sort_asc(self):
        response = self.client.get(
            reverse("novels:rank"), {"sort": "click_num", "dir": "asc"}
        )
        self.assertEqual(response.status_code, 200)

    def test_rank_sort_desc(self):
        response = self.client.get(
            reverse("novels:rank"), {"sort": "click_num", "dir": "desc"}
        )
        self.assertEqual(response.status_code, 200)

    def test_rank_invalid_sort(self):
        response = self.client.get(
            reverse("novels:rank"), {"sort": "invalid"}
        )
        self.assertEqual(response.status_code, 200)

    def test_rank_queries(self):
        with self.assertNumQueries(3):
            self.client.get(reverse("novels:rank"))


# ── Author views ─────────────────────────────────────────────────────


class AuthorViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(name="Test Author")
        Novel.objects.create(
            id=3001,
            title="Author Novel",
            author=cls.author,
            genre=GENRE.enum.MAGIC.value,
            status=STATUS.enum.FINISHED.value,
            ptype=PTYPE.enum.FREE.value,
        )

    def test_author_list(self):
        response = self.client.get(reverse("novels:authors"))
        self.assertEqual(response.status_code, 200)

    def test_author_list_queries(self):
        with self.assertNumQueries(3):
            self.client.get(reverse("novels:authors"))

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

    def test_author_detail_404(self):
        response = self.client.get(reverse("novels:author_detail", args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_author_detail_queries(self):
        with self.assertNumQueries(4):
            self.client.get(reverse("novels:author_detail", args=[self.author.id]))


# ── Tag views ────────────────────────────────────────────────────────


class TagViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tag = Tag.objects.create(name="Test Tag")
        cls.author = Author.objects.create(name="Author")
        cls.novel = Novel.objects.create(
            id=4001,
            title="Tag Novel",
            author=cls.author,
            genre=GENRE.enum.MAGIC.value,
            status=STATUS.enum.FINISHED.value,
            ptype=PTYPE.enum.FREE.value,
        )
        cls.novel.tags.add(cls.tag)

    def test_tag_list(self):
        response = self.client.get(reverse("novels:tags"))
        self.assertEqual(response.status_code, 200)

    def test_tag_detail(self):
        response = self.client.get(reverse("novels:tag_detail", args=[self.tag.id]))
        self.assertEqual(response.status_code, 200)

    def test_tag_detail_404(self):
        response = self.client.get(reverse("novels:tag_detail", args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_tag_detail_queries(self):
        with self.assertNumQueries(4):
            self.client.get(reverse("novels:tag_detail", args=[self.tag.id]))


# ── Contest views ────────────────────────────────────────────────────


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
            genre=GENRE.enum.MAGIC.value,
            status=STATUS.enum.FINISHED.value,
            ptype=PTYPE.enum.FREE.value,
        )

    def test_contest_list(self):
        response = self.client.get(reverse("novels:contests"))
        self.assertEqual(response.status_code, 200)

    def test_contest_detail(self):
        response = self.client.get(
            reverse("novels:contest_detail", args=[self.contest.id])
        )
        self.assertEqual(response.status_code, 200)

    def test_contest_detail_404(self):
        response = self.client.get(reverse("novels:contest_detail", args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_contest_detail_queries(self):
        with self.assertNumQueries(4):
            self.client.get(reverse("novels:contest_detail", args=[self.contest.id]))


# ── Banner view ──────────────────────────────────────────────────────


class BannerViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(name="Author")
        Novel.objects.create(
            id=6001,
            title="Banner Novel",
            author=cls.author,
            genre=GENRE.enum.MAGIC.value,
            status=STATUS.enum.FINISHED.value,
            ptype=PTYPE.enum.FREE.value,
            has_banner=True,
        )

    def test_banner_list(self):
        response = self.client.get(reverse("novels:banners"))
        self.assertEqual(response.status_code, 200)

    def test_banner_queries(self):
        with self.assertNumQueries(3):
            self.client.get(reverse("novels:banners"))


# ── Enum views ───────────────────────────────────────────────────────


class EnumViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(name="Author")
        Novel.objects.create(
            id=7001,
            title="Enum Novel",
            author=cls.author,
            genre=GENRE.enum.MAGIC.value,
            status=STATUS.enum.FINISHED.value,
            ptype=PTYPE.enum.FREE.value,
        )

    def test_genres_list(self):
        response = self.client.get(reverse("novels:genres"))
        self.assertEqual(response.status_code, 200)

    def test_genre_detail(self):
        response = self.client.get(
            reverse("novels:genre_detail", args=[GENRE.enum.MAGIC.value])
        )
        self.assertEqual(response.status_code, 200)

    def test_statuses_list(self):
        response = self.client.get(reverse("novels:statuses"))
        self.assertEqual(response.status_code, 200)

    def test_ptypes_list(self):
        response = self.client.get(reverse("novels:ptypes"))
        self.assertEqual(response.status_code, 200)

    def test_enum_404(self):
        response = self.client.get("/invalid/")
        self.assertEqual(response.status_code, 404)


# ── About view ───────────────────────────────────────────────────────


class AboutViewTest(TestCase):
    def test_about_status_code(self):
        response = self.client.get(reverse("novels:about"))
        self.assertEqual(response.status_code, 200)

    def test_about_template(self):
        response = self.client.get(reverse("novels:about"))
        self.assertTemplateUsed(response, "novels/about.html")
