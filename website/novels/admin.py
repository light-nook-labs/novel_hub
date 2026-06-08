from django.contrib import admin
from .models import Author, Tag, Contest, Novel


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Novel)
class NovelAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "genre", "status", "ptype", "last_update"]
    list_filter = ["genre", "status", "ptype"]
    search_fields = ["title"]
    autocomplete_fields = ["author", "contest"]
    filter_horizontal = ["tags"]
