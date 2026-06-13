from django.test import TestCase

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
