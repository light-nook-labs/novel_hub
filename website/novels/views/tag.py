from django.views.generic import ListView, DetailView

from ..models import Tag

_pagination = __import__("django.conf", fromlist=["settings"]).settings.TOML.get(
    "pagination", {}
)
_detail_novel_limit = _pagination.get("detail_novel_limit", 50)


class TagListView(ListView):
    model = Tag
    template_name = "novels/tags.html"
    context_object_name = "tags"

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(name__icontains=q)
        return qs.annotate_novel_count()


class TagDetailView(DetailView):
    model = Tag
    template_name = "novels/tag_detail.html"
    context_object_name = "tag"

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
