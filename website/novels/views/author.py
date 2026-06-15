from django.views.generic import ListView
from django.db import models
from django.http import Http404

from ..models import Novel, Author
from ..mappings import GENRE, STATUS, PTYPE

_pagination = __import__("django.conf", fromlist=["settings"]).settings.TOML.get(
    "pagination", {}
)
_paginate_by = _pagination.get("per_page", 24)

SORT_OPTIONS = {
    "click_num": "点击",
    "word_num": "字数",
    "like_num": "收藏",
    "praise_num": "点赞",
    "last_update": "最近",
}


def _choices(mapping):
    return [
        {"value": m.value, "label": mapping.get_zh(m.value)}
        for m in mapping.enum
        if m.name != "OTHER"
    ]


class AuthorListView(ListView):
    model = Author
    template_name = "novels/authors.html"
    context_object_name = "authors"
    paginate_by = 100

    SORT_OPTIONS = {
        "total_click": "总点击",
        "novel_count": "作品数",
        "total_word": "总字数",
        "total_like": "总收藏",
        "total_praise": "总点赞",
        "total_review": "总长评",
        "total_comment": "总短评",
        "latest_update": "最近",
    }

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(name__icontains=q)

        from django.db.models import Value, IntegerField
        from django.db.models.functions import Coalesce

        qs = qs.annotate(
            novel_count=models.Count("novels"),
            total_click=Coalesce(
                models.Sum("novels__click_num"), Value(0), output_field=IntegerField()
            ),
            total_word=Coalesce(
                models.Sum("novels__word_num"), Value(0), output_field=IntegerField()
            ),
            total_like=Coalesce(
                models.Sum("novels__like_num"), Value(0), output_field=IntegerField()
            ),
            total_praise=Coalesce(
                models.Sum("novels__praise_num"), Value(0), output_field=IntegerField()
            ),
            total_review=Coalesce(
                models.Sum("novels__review_num"), Value(0), output_field=IntegerField()
            ),
            total_comment=Coalesce(
                models.Sum("novels__comment_num"), Value(0), output_field=IntegerField()
            ),
            banner_count=models.Count(
                "novels", filter=models.Q(novels__has_banner=True)
            ),
            latest_update=models.Max("novels__last_update"),
        )

        sort = self.request.GET.get("sort", "total_click")
        if sort in self.SORT_OPTIONS:
            direction = self.request.GET.get("dir", "desc")
            prefix = "" if direction == "asc" else "-"
            qs = qs.order_by(f"{prefix}{sort}", "-novel_count")
        else:
            qs = qs.order_by("-total_click")

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["sort_options"] = self.SORT_OPTIONS
        ctx["current_sort"] = self.request.GET.get("sort", "total_click")
        ctx["current_dir"] = self.request.GET.get("dir", "desc")
        page_obj = ctx.get("page_obj")
        ctx["page_start"] = (
            (page_obj.number - 1) * self.paginate_by + 1 if page_obj else 1
        )
        params = self.request.GET.copy()
        params.pop("page", None)
        params.pop("sort", None)
        params.pop("dir", None)
        ctx["querystring"] = params.urlencode()

        # Fetch top novel for each author on current page
        authors = ctx.get("authors", [])
        if authors:
            author_ids = [a.id for a in authors]
            from django.db.models import Window, F
            from django.db.models.functions import RowNumber

            ranked = (
                Novel.objects.filter(author_id__in=author_ids)
                .annotate(
                    rn=Window(
                        expression=RowNumber(),
                        partition_by=[F("author_id")],
                        order_by=F("click_num").desc(nulls_last=True),
                    )
                )
                .filter(rn=1)
                .values("id", "title", "click_num", "author_id")
            )
            top_novels = {row["author_id"]: row for row in ranked}

            for author in authors:
                top = top_novels.get(author.id, {})
                author.top_novel_id = top.get("id")
                author.top_novel_title = top.get("title")
                author.top_novel_click = top.get("click_num")

        return ctx


class AuthorDetailView(ListView):
    model = Author
    template_name = "novels/author_detail.html"
    context_object_name = "novels"
    paginate_by = _paginate_by

    def dispatch(self, request, *args, **kwargs):
        try:
            self.author = Author.objects.get(pk=self.kwargs["pk"])
        except Author.DoesNotExist:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = (
            Novel.objects.filter(author=self.author)
            .select_related("author", "contest")
            .prefetch_related("tags")
        )

        # Apply filters
        genre = self.request.GET.get("genre")
        status = self.request.GET.get("status")
        ptype = self.request.GET.get("ptype")

        if genre:
            qs = qs.filter(genre=int(genre))
        if status:
            qs = qs.filter(status=int(status))
        if ptype:
            qs = qs.filter(ptype=int(ptype))

        # Apply sorting
        sort = self.request.GET.get("sort", "click_num")
        if sort in SORT_OPTIONS and sort:
            qs = qs.order_by(f"-{sort}")
        else:
            qs = qs.order_by("-click_num")

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["author"] = self.author
        ctx["novel_count"] = ctx["paginator"].count
        ctx["genres"] = _choices(GENRE)
        ctx["statuses"] = _choices(STATUS)
        ctx["ptypes"] = _choices(PTYPE)
        ctx["sort_options"] = SORT_OPTIONS
        ctx["current_genre"] = self.request.GET.get("genre", "")
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["current_ptype"] = self.request.GET.get("ptype", "")
        ctx["current_sort"] = self.request.GET.get("sort", "click_num")
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["querystring"] = params.urlencode()
        return ctx
