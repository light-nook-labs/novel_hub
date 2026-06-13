from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core.management import call_command
from django.db import connection
from io import StringIO

from novels.models import Novel, Author, Tag, Contest
from novels.mappings import GENRE, STATUS, PTYPE


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


class ManagementCommandTests(TestCase):
    def test_init_db_help(self):
        out = StringIO()
        with self.assertRaises(SystemExit) as cm:
            call_command("init_db", "--help", stdout=out)
        self.assertEqual(cm.exception.code, 0)

    def test_upsert_dataset_help(self):
        out = StringIO()
        with self.assertRaises(SystemExit) as cm:
            call_command("upsert_dataset", "--help", stdout=out)
        self.assertEqual(cm.exception.code, 0)

    def test_dump_dataset_help(self):
        out = StringIO()
        with self.assertRaises(SystemExit) as cm:
            call_command("dump_dataset", "--help", stdout=out)
        self.assertEqual(cm.exception.code, 0)

    def test_generate_static_help(self):
        out = StringIO()
        with self.assertRaises(SystemExit) as cm:
            call_command("generate_static", "--help", stdout=out)
        self.assertEqual(cm.exception.code, 0)

    def test_serve_static_help(self):
        out = StringIO()
        with self.assertRaises(SystemExit) as cm:
            call_command("serve_static", "--help", stdout=out)
        self.assertEqual(cm.exception.code, 0)


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
        from novels.models import Tag
        tag = Tag(id=1, name="test")
        result = pill_bg(tag, "tag")
        self.assertTrue(result.startswith("hsl("))

    def test_detail_url_none(self):
        from novels.templatetags.novel_tags import detail_url
        self.assertEqual(detail_url(None, "novels:tag_detail"), "")

    def test_detail_url_valid(self):
        from novels.templatetags.novel_tags import detail_url
        from novels.models import Tag
        tag = Tag(id=1, name="test")
        result = detail_url(tag, "novels:tag_detail")
        self.assertIn("/tags/1/", result)

    def test_get_attr_valid(self):
        from novels.templatetags.novel_tags import get_attr
        from novels.models import Author
        author = Author(id=1, name="Test")
        self.assertEqual(get_attr(author, "name"), "Test")

    def test_get_attr_none(self):
        from novels.templatetags.novel_tags import get_attr
        self.assertEqual(get_attr(None, "name"), "")


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
        response = self.client.get(reverse("novels:index"), {"q": "<script>alert(1)</script>"})
        self.assertEqual(response.status_code, 200)
        # Django auto-escapes HTML, so check for escaped version
        self.assertContains(response, "&lt;script&gt;")

    def test_search_sql_injection(self):
        response = self.client.get(reverse("novels:index"), {"q": "'; DROP TABLE novels;--"})
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
