# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=30)

    class Meta:
        managed = False
        db_table = "author"
        ordering = ["-id"]


class Contest(models.Model):
    name = models.CharField(max_length=30)

    class Meta:
        managed = False
        db_table = "contest"
        ordering = ["-id"]


class Novel(models.Model):
    title = models.CharField(max_length=30)
    ptype = models.IntegerField(blank=True, null=True, db_index=True)
    genre = models.IntegerField(blank=True, null=True, db_index=True)
    status = models.IntegerField(blank=True, null=True, db_index=True)
    click_num = models.IntegerField(blank=True, null=True)
    word_num = models.IntegerField(blank=True, null=True)
    praise_num = models.IntegerField(blank=True, null=True)
    like_num = models.IntegerField(blank=True, null=True)
    has_banner = models.BooleanField(db_index=True)
    review_num = models.IntegerField(blank=True, null=True)
    comment_num = models.IntegerField(blank=True, null=True)
    last_update = models.DateTimeField(blank=True, null=True)
    db_update = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(Author, models.DO_NOTHING, blank=True, null=True)
    contest = models.ForeignKey(Contest, models.DO_NOTHING, blank=True, null=True)
    cover = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "novel"
        ordering = [
            "-id",
            "-last_update",
            "-click_num",
            "-praise_num",
            "-like_num",
            "-word_num",
            "has_banner",
            "-review_num",
            "-comment_num",
            "title",
            "ptype",
            "genre",
            "status",
            "author",
            "contest",
            "db_update",
            "cover",
        ]


class Noveltaglink(models.Model):
    pk = models.CompositePrimaryKey("tag_id", "novel_id")
    tag = models.ForeignKey("Tag", models.DO_NOTHING)
    novel = models.ForeignKey(Novel, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "noveltaglink"
        ordering = ["-novel_id", "-tag_id"]


class Tag(models.Model):
    name = models.CharField(max_length=30)

    class Meta:
        managed = False
        db_table = "tag"
        ordering = ["-id"]
