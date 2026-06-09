---
name: django-app
description: Create and develop Django apps with models, views, forms, templates, admin, and template tags
---

## What I do
- Create Django app structure
- Define models with relationships
- Create views (ListView, DetailView, CreateView, UpdateView, DeleteView)
- Build forms with validation
- Register models in Django admin
- Create custom template tags and filters
- Write management commands

## App structure
```
app/
├── templates/app/
│   ├── base.html
│   ├── list.html
│   ├── detail.html
│   └── components/
├── static/app/
├── templatetags/
│   ├── __init__.py
│   └── app_tags.py
├── management/commands/
├── models.py
├── views.py
├── urls.py
├── forms.py
├── admin.py
└── tests.py
```

## Models
```python
from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=200, unique=True)
    
    class Meta:
        ordering = ["name"]
    
    def __str__(self):
        return self.name

class Novel(models.Model):
    id = models.BigIntegerField(primary_key=True)
    title = models.CharField(max_length=500)
    author = models.ForeignKey(Author, on_delete=models.SET_NULL, null=True, related_name="novels")
    tags = models.ManyToManyField(Tag, blank=True, related_name="novels")
    
    class Meta:
        ordering = ["-last_update"]
        indexes = [
            models.Index(fields=["genre", "status"]),
        ]
```

## Views
```python
from django.views.generic import ListView, DetailView
from django.db.models import Q

class NovelListView(ListView):
    model = Novel
    template_name = "novels/list.html"
    context_object_name = "novels"
    paginate_by = 24

    def get_queryset(self):
        qs = super().get_queryset().select_related("author").prefetch_related("tags")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(author__name__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["querystring"] = params.urlencode()
        return ctx
```

## Forms
```python
from django import forms

class NovelForm(forms.ModelForm):
    class Meta:
        model = Novel
        fields = ["title", "author", "genre", "status", "tags"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "input-field"}),
            "tags": forms.CheckboxSelectMultiple,
        }
```

## Admin
```python
from django.contrib import admin

@admin.register(Novel)
class NovelAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "genre", "status", "last_update"]
    list_filter = ["genre", "status", "ptype"]
    search_fields = ["title", "author__name"]
    autocomplete_fields = ["author", "contest"]
    filter_horizontal = ["tags"]
    readonly_fields = ["id", "db_update"]

class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    inlines = [ChapterInline]
```

## Template tags
```python
from django import template
register = template.Library()

@register.filter
def get_attr(obj, attr):
    """{{ obj|get_attr:"field_name" }}"""
    try:
        for part in attr.split("__"):
            obj = getattr(obj, part)
        return obj() if callable(obj) else obj
    except (AttributeError, TypeError):
        return ""

@register.filter
def humanize_num(value):
    """{{ value|humanize_num }} — 10000 -> 1w+"""
    try:
        if value is None: return "-"
        n = int(value)
        return f"{int(n/10000)}w+" if n >= 10000 else str(n)
    except (ValueError, TypeError):
        return "-"

@register.simple_tag
def get_color(obj, model_name):
    """{% get_color obj "tag" as color %}"""
    h = hash(f"{model_name}_{obj.id}") % 360
    return f"hsl({h}, 70%, 92%)"
```

## Management commands
```python
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Description"

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", default="data/")

    def handle(self, *args, **options):
        self.stdout.write("Processing...")
        # ... logic ...
        self.stdout.write(self.style.SUCCESS("Done."))
```

## URL patterns
```python
from django.urls import path
from . import views

app_name = "novels"

urlpatterns = [
    path("", views.NovelListView.as_view(), name="list"),
    path("<int:pk>/", views.NovelDetailView.as_view(), name="detail"),
]
```

## Layout rules
- **Grid-first**: ListView uses `grid-cols-4 md:grid-cols-6 lg:grid-cols-8`
- **Pagination**: `per_page` must be multiple of 6. Default: 24
- **No pagination** for tag/contest list pages (render all as pills)
- **Single admin user**: No authentication, no `LoginRequiredMixin`

## After creation
- Run `uv run python manage.py makemigrations`
- Run `uv run python manage.py migrate`
- Run `uv run python manage.py test <app_name>`
