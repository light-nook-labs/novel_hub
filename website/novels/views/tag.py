from django.views.generic import ListView
from django.http import Http404

from ..models import Tag

_pagination = __import__("django.conf", fromlist=["settings"]).settings.TOML.get(
    "pagination", {}
)
_paginate_by = _pagination.get("per_page", 24)


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


class TagDetailView(ListView):
    model = Tag
    template_name = "novels/tag_detail.html"
    context_object_name = "novels"
    paginate_by = _paginate_by

    def dispatch(self, request, *args, **kwargs):
        try:
            self.tag = Tag.objects.get(pk=self.kwargs["pk"])
        except Tag.DoesNotExist:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        from ..models import Novel

        return (
            Novel.objects.filter(tags=self.tag)
            .select_related("author", "contest")
            .prefetch_related("tags")
            .order_by("-click_num")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tag"] = self.tag
        ctx["novel_count"] = ctx["paginator"].count
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["querystring"] = params.urlencode()
        return ctx
