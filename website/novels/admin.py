from django.contrib import admin

from .models import Author, Contest, Tag

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
