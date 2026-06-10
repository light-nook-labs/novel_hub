from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core.management import call_command
from django.db import connection
from io import StringIO

from .models import Novel, Author, Tag, Contest
from .mappings import GENRE, STATUS, PTYPE


class ModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(name="Test Author")
        cls.tag = Tag.objects.create(name="Test Tag")
        cls.contest = Contest.objects.create(name="Test Contest")
        cls.novel = Novel.objects.create(
            id=1001,
            title="Test Novel",
            author=cls.author,
            contest=cls.contest,
            genre=GENRE.enum.MAGIC.value,
            status=STATUS.enum.FINISHED.value,
            ptype=PTYPE.enum.FREE.value,
            click_num=1000,
            word_num=50000,
            has_banner=False,
        )
        cls.novel.tags.add(cls.tag)

    def test_novel_str(self):
        self.assertEqual(str(self.novel), "Test Novel")

    def test_author_str(self):
        self.assertEqual(str(self.author), "Test Author")

    def test_tag_str(self):
        self.assertEqual(str(self.tag), "Test Tag")

    def test_contest_str(self):
        self.assertEqual(str(self.contest), "Test Contest")

    def test_novel_get_genre_display(self):
        self.assertEqual(self.novel.get_genre_display(), "魔幻")

    def test_novel_get_status_display(self):
        self.assertEqual(self.novel.get_status_display(), "已完结")

    def test_novel_get_ptype_display(self):
        self.assertEqual(self.novel.get_ptype_display(), "免费")

    def test_novel_tags(self):
        self.assertIn(self.tag, self.novel.tags.all())

    def test_novel_author(self):
        self.assertEqual(self.novel.author, self.author)

    def test_novel_contest(self):
        self.assertEqual(self.novel.contest, self.contest)

    def test_author_novel_count(self):
        count = Author.objects.filter(id=self.author.id).annotate_novel_count()
        self.assertEqual(count[0].novel_count, 1)

    def test_tag_novel_count(self):
        count = Tag.objects.filter(id=self.tag.id).annotate_novel_count()
        self.assertEqual(count[0].novel_count, 1)


class MappingTests(TestCase):
    def test_genre_get_zh(self):
        self.assertEqual(GENRE.get_zh(GENRE.enum.MAGIC.value), "魔幻")
        self.assertEqual(GENRE.get_zh(999), "其他")

    def test_genre_get_value(self):
        self.assertEqual(GENRE.get_value("魔幻"), GENRE.enum.MAGIC.value)

    def test_status_get_zh(self):
        self.assertEqual(STATUS.get_zh(STATUS.enum.FINISHED.value), "已完结")

    def test_ptype_get_zh(self):
        self.assertEqual(PTYPE.get_zh(PTYPE.enum.VIP.value), "VIP")

    def test_genre_choices(self):
        choices = GENRE.choices
        self.assertTrue(len(choices) > 0)
        self.assertEqual(choices[0], (1, "其他"))


class QueryPerformanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(name="Author")
        cls.tag1 = Tag.objects.create(name="Tag1")
        cls.tag2 = Tag.objects.create(name="Tag2")
        cls.contest = Contest.objects.create(name="Contest")

        for i in range(10):
            novel = Novel.objects.create(
                id=10000 + i,
                title=f"Novel {i}",
                author=cls.author,
                contest=cls.contest,
                genre=GENRE.enum.MAGIC.value,
                status=STATUS.enum.FINISHED.value,
                ptype=PTYPE.enum.FREE.value,
                click_num=100 * i,
            )
            novel.tags.add(cls.tag1, cls.tag2)

    def test_index_query_count(self):
        with self.assertNumQueries(4):
            response = self.client.get(reverse("novels:index"))

    def test_detail_query_count(self):
        with self.assertNumQueries(3):
            response = self.client.get(reverse("novels:detail", args=[10000]))

    def test_rank_query_count(self):
        with self.assertNumQueries(3):
            response = self.client.get(reverse("novels:rank"))

    def test_author_list_query_count(self):
        with self.assertNumQueries(2):
            response = self.client.get(reverse("novels:authors"))

    def test_tag_list_query_count(self):
        with self.assertNumQueries(1):
            response = self.client.get(reverse("novels:tags"))

    def test_n1_select_related(self):
        novels = list(
            Novel.objects.select_related("author", "contest").all()[:5]
        )
        with self.assertNumQueries(0):
            for novel in novels:
                _ = novel.author.name
                _ = novel.contest.name if novel.contest else None

    def test_n1_prefetch_related(self):
        novels = list(Novel.objects.prefetch_related("tags").all()[:5])
        with self.assertNumQueries(0):
            for novel in novels:
                list(novel.tags.all())


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


class AboutViewTest(TestCase):
    def test_about_status_code(self):
        response = self.client.get(reverse("novels:about"))
        self.assertEqual(response.status_code, 200)

    def test_about_template(self):
        response = self.client.get(reverse("novels:about"))
        self.assertTemplateUsed(response, "novels/about.html")
