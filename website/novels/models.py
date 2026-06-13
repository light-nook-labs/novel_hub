from django.db import models

from .mappings import GENRE, STATUS, PTYPE


class NovelCountQuerySet(models.QuerySet):
    def annotate_novel_count(self):
        return self.annotate(novel_count=models.Count("novels")).order_by(
            "-novel_count"
        )


class Author(models.Model):
    name = models.CharField(max_length=200, unique=True)
    objects = NovelCountQuerySet.as_manager()

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    objects = NovelCountQuerySet.as_manager()

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class Contest(models.Model):
    name = models.CharField(max_length=300, unique=True)
    objects = NovelCountQuerySet.as_manager()

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class Novel(models.Model):
    id = models.BigIntegerField(primary_key=True)
    title = models.CharField(max_length=500)
    ptype = models.SmallIntegerField(default=1, db_index=True)
    genre = models.SmallIntegerField(default=1, db_index=True)
    status = models.SmallIntegerField(default=1, db_index=True)
    click_num = models.IntegerField(null=True, blank=True)
    word_num = models.IntegerField(null=True, blank=True)
    praise_num = models.IntegerField(null=True, blank=True)
    like_num = models.IntegerField(null=True, blank=True)
    has_banner = models.BooleanField(default=False, db_index=True)
    review_num = models.IntegerField(null=True, blank=True)
    comment_num = models.IntegerField(null=True, blank=True)
    cover = models.CharField(max_length=500, blank=True, null=True)
    last_update = models.DateTimeField(null=True, blank=True)
    db_update = models.DateTimeField(auto_now=True)

    author = models.ForeignKey(
        Author,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="novels",
    )
    contest = models.ForeignKey(
        Contest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="novels",
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="novels")

    class Meta:
        ordering = ["-last_update"]
        indexes = [
            models.Index(fields=["genre", "status"]),
            models.Index(fields=["has_banner", "-last_update"]),
            models.Index(fields=["-click_num"]),
            models.Index(fields=["author"]),
        ]

    def __str__(self):
        return self.title

    def get_genre_display(self):
        return GENRE.get_zh(self.genre)

    def get_status_display(self):
        return STATUS.get_zh(self.status)

    def get_ptype_display(self):
        return PTYPE.get_zh(self.ptype)


class Task(models.Model):
    class Status(models.TextChoices):
        URGENT = "u", "urgent"
        DEFAULT = "d", "default"
        FINISHED = "f", "finished"

    novel = models.OneToOneField(
        Novel,
        on_delete=models.CASCADE,
        related_name="task",
    )
    status = models.CharField(
        max_length=1,
        choices=Status,
        default=Status.DEFAULT,
    )

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"Task #{self.id} → Novel {self.novel_id}"
