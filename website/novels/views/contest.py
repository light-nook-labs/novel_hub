from django.views.generic import ListView
from django.http import Http404

from ..models import Novel, Contest
from ..mappings import GENRE, STATUS, PTYPE

_pagination = __import__("django.conf", fromlist=["settings"]).settings.TOML.get(
    "pagination", {}
)
_paginate_by = _pagination.get("per_page", 24)

SORT_OPTIONS = {
    "": "综合排序",
    "click_num": "点击排序",
    "word_num": "字数排序",
    "like_num": "收藏排序",
    "praise_num": "点赞排序",
    "last_update": "最近更新",
}


def _choices(mapping):
    return [
        {"value": m.value, "label": mapping.get_zh(m.value)}
        for m in mapping.enum
        if m.name != "OTHER"
    ]


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
        qs = (
            Novel.objects.filter(contest=self.contest)
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
        ctx["contest"] = self.contest
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
