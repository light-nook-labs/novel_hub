import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from novels.models import Novel, Author, Tag, Contest
from novels.mappings import GENRE, STATUS, PTYPE

fake = Faker("zh_CN")

GENRES = GENRE.en_keys()
STATUSES = STATUS.en_keys()
PTYPES = PTYPE.en_keys()
TAGS_POOL = [
    "冒险",
    "热血",
    "搞笑",
    "恋爱",
    "校园",
    "都市",
    "穿越",
    "重生",
    "系统",
    "升级",
    "女频",
    "男频",
    "悬疑",
    "科幻",
    "奇幻",
    "古风",
    "仙侠",
    "末日",
    "治愈",
    "致郁",
    "日常",
    "职场",
    "推理",
    "战斗",
]


class Command(BaseCommand):
    help = "Generate fake novel data for development"

    def add_arguments(self, parser):
        parser.add_argument(
            "-n", "--num", type=int, default=500, help="Number of novels (default: 500)"
        )

    def handle(self, *args, **options):
        num = options["num"]
        now = timezone.now()

        self.stdout.write(f"Generating {num} fake novels ...")

        authors = [Author(name=fake.name()) for _ in range(num // 2)]
        Author.objects.bulk_create(authors, ignore_conflicts=True)
        author_ids = list(Author.objects.values_list("id", flat=True))

        contests = [Contest(name=fake.sentence(nb_words=4)) for _ in range(20)]
        Contest.objects.bulk_create(contests, ignore_conflicts=True)
        contest_ids = list(Contest.objects.values_list("id", flat=True))

        tags = [Tag(name=t) for t in TAGS_POOL]
        Tag.objects.bulk_create(tags, ignore_conflicts=True)
        tag_ids = list(Tag.objects.values_list("id", flat=True))

        novels = []
        for i in range(num):
            genre_val = GENRE.get_value(fake.random_element(GENRES))
            status_val = STATUS.get_value(fake.random_element(STATUSES))
            ptype_val = PTYPE.get_value(fake.random_element(PTYPES))

            last_update = now - timedelta(days=random.randint(0, 2000))
            is_on_going = status_val == STATUS.enum.ON_GOING.value
            if is_on_going and (now - last_update).days > 90:
                status_val = STATUS.enum.DIED.value

            novels.append(
                Novel(
                    id=100000 + i,
                    title=fake.sentence(nb_words=6).rstrip("。"),
                    genre=genre_val,
                    status=status_val,
                    ptype=ptype_val,
                    click_num=random.randint(0, 10_000_000),
                    word_num=random.randint(1000, 5_000_000),
                    praise_num=random.randint(0, 100_000),
                    like_num=random.randint(0, 500_000),
                    review_num=random.randint(0, 10_000),
                    comment_num=random.randint(0, 50_000),
                    has_banner=fake.boolean(chance_of_getting_true=20),
                    last_update=last_update,
                    author_id=random.choice(author_ids) if author_ids else None,
                    contest_id=random.choice(contest_ids + [None] * 3),
                )
            )

        Novel.objects.bulk_create(novels, batch_size=5000)
        novel_ids = list(Novel.objects.values_list("id", flat=True))

        self.stdout.write("Setting M2M tags ...")
        tag_rows = []
        for nid in novel_ids:
            chosen = random.sample(tag_ids, k=random.randint(1, 5))
            for tid in chosen:
                tag_rows.append((nid, tid))

        from django.db import connection

        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT OR IGNORE INTO novels_novel_tags (novel_id, tag_id) VALUES (?, ?)",
                tag_rows,
            )

        self.stdout.write(self.style.SUCCESS(f"Done. {num} novels created."))
