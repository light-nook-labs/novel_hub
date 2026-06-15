from django.views.generic import ListView
from django.http import Http404

from ..models import Novel, Contest

_pagination = __import__("django.conf", fromlist=["settings"]).settings.TOML.get(
    "pagination", {}
)
_paginate_by = _pagination.get("per_page", 24)


class ContestListView(ListView):
    model = Contest
    template_name = "novels/contests.html"
    context_object_name = "contests"

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(name__icontains=q)
        return qs.annotate_novel_count()


class ContestDetailView(ListView):
    model = Contest
    template_name = "novels/contest_detail.html"
    context_object_name = "novels"
    paginate_by = _paginate_by

    def dispatch(self, request, *args, **kwargs):
        try:
            self.contest = Contest.objects.get(pk=self.kwargs["pk"])
        except Contest.DoesNotExist:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            Novel.objects.filter(contest=self.contest)
            .select_related("author", "contest")
            .prefetch_related("tags")
            .order_by("-click_num")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["contest"] = self.contest
        ctx["novel_count"] = ctx["paginator"].count
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["querystring"] = params.urlencode()
        return ctx
