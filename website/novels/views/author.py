from django.views.generic import ListView, DetailView
from django.db import models

from ..models import Novel, Author

_pagination = __import__("django.conf", fromlist=["settings"]).settings.TOML.get(
    "pagination", {}
)
_detail_novel_limit = _pagination.get("detail_novel_limit", 50)


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
        "latest_update": "最近更新",
    }

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(name__icontains=q)

        qs = qs.annotate(
            novel_count=models.Count("novels"),
            total_click=models.Sum("novels__click_num"),
            total_word=models.Sum("novels__word_num"),
            total_like=models.Sum("novels__like_num"),
            total_praise=models.Sum("novels__praise_num"),
            total_review=models.Sum("novels__review_num"),
            total_comment=models.Sum("novels__comment_num"),
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


class AuthorDetailView(DetailView):
    model = Author
    template_name = "novels/author_detail.html"
    context_object_name = "author"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        novels_qs = (
            self.object.novels.select_related("author", "contest")
            .prefetch_related("tags")
            .order_by("-click_num")
        )
        ctx["novels"] = novels_qs[:_detail_novel_limit]
        ctx["novel_count"] = self.object.novels.count()
        return ctx
