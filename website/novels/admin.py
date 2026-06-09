from django.contrib import admin

from .mappings import GENRE, PTYPE, STATUS
from .models import Author, Contest, Novel, Tag, Task

admin.site.site_header = "Novel Hub 管理"
admin.site.site_title = "Novel Hub"
admin.site.index_title = "数据管理"


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    list_display = ["name"]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    list_display = ["name"]


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    list_display = ["name"]


@admin.register(Novel)
class NovelAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "author",
        "genre_display",
        "status_display",
        "ptype_display",
        "last_update",
    ]
    list_filter = ["genre", "status", "ptype"]
    search_fields = ["title"]
    autocomplete_fields = ["author", "contest"]
    filter_horizontal = ["tags"]

    @admin.display(description="分类")
    def genre_display(self, obj):
        return GENRE.get_zh(obj.genre)

    @admin.display(description="状态")
    def status_display(self, obj):
        return STATUS.get_zh(obj.status)

    @admin.display(description="类型")
    def ptype_display(self, obj):
        return PTYPE.get_zh(obj.ptype)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["id", "novel"]
    search_fields = ["novel__title"]
    autocomplete_fields = ["novel"]
