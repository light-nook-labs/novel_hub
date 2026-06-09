from django.contrib import admin

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
    list_display = ["title", "author", "genre", "status", "ptype", "last_update"]
    list_filter = ["genre", "status", "ptype"]
    search_fields = ["title"]
    readonly_fields = [
        "id",
        "title",
        "ptype",
        "genre",
        "status",
        "click_num",
        "word_num",
        "praise_num",
        "like_num",
        "has_banner",
        "review_num",
        "comment_num",
        "cover",
        "last_update",
        "db_update",
        "author",
        "contest",
        "tags",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["id", "novel"]
    search_fields = ["novel__title"]
    autocomplete_fields = ["novel"]
