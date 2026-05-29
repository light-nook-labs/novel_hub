from django.contrib import admin
from .models import Author, Contest, Novel, Tag


# Base permission class: allow create only, forbid update and delete
class BaseReadOnlyAdmin(admin.ModelAdmin):
    list_editable = ()

    def has_add_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Author)
class AuthorAdmin(BaseReadOnlyAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    list_per_page = 50
    readonly_fields = ("name",)


@admin.register(Contest)
class ContestAdmin(BaseReadOnlyAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    list_per_page = 50
    readonly_fields = ("name",)


@admin.register(Tag)
class TagAdmin(BaseReadOnlyAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    list_per_page = 50
    readonly_fields = ("name",)


@admin.register(Novel)
class NovelAdmin(BaseReadOnlyAdmin):
    list_display = (
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
        # "last_update", "db_update", "author", "contest", "cover"
    )
    search_fields = ("title", "author__name")
    list_filter = ("ptype", "genre", "status", "has_banner")
    list_per_page = 50
    fieldsets = (
        ("Basic Info", {"fields": ("title", "cover", "has_banner")}),
        ("Category & Status", {"fields": ("ptype", "genre", "status")}),
        (
            "Statistics",
            {
                "fields": (
                    "click_num",
                    "word_num",
                    "praise_num",
                    "like_num",
                    "review_num",
                    "comment_num",
                )
            },
        ),
        ("Related Info", {"fields": ("author", "contest")}),
        (
            "Time Info",
            {"fields": ("last_update", "db_update"), "classes": ("collapse",)},
        ),
    )
    readonly_fields = ("db_update",)
