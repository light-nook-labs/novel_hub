from django.views.generic import ListView, DetailView
from django.conf import settings
from django.core.cache import cache

from ..models import Novel, Author, Tag, Contest
from ..mappings import GENRE, STATUS, PTYPE

COLUMNS = [
    {"key": "info", "label": "小说", "sortable": True, "sort_key": "id"},
    {"key": "has_banner", "label": "Banner", "sortable": True},
    {"key": "word_num", "label": "字数", "sortable": True},
    {"key": "click_num", "label": "点击", "sortable": True},
    {"key": "like_num", "label": "收藏", "sortable": True},
    {"key": "praise_num", "label": "点赞", "sortable": True},
    {"key": "review_num", "label": "长评", "sortable": True},
    {"key": "comment_num", "label": "短评", "sortable": True},
    {"key": "last_update", "label": "更新时间", "sortable": True},
]

NOVEL_LIST_SELECT = ("author", "contest")
NOVEL_LIST_PREFETCH = ("tags",)
_pagination = settings.TOML.get("pagination", {})
_paginate_by = _pagination.get("per_page", 24)
_rank_paginate_by = _pagination.get("rank_per_page", 100)
_banner_paginate_by = _pagination.get("banner_per_page", 12)


class NovelListView(ListView):
    model = Novel
    template_name = "novels/index.html"
    context_object_name = "novels"
    paginate_by = _paginate_by

    SORT_OPTIONS = {
        "click_num": "点击",
        "word_num": "字数",
        "like_num": "收藏",
        "praise_num": "点赞",
        "last_update": "最近",
        "db_update": "同步",
    }

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related(*NOVEL_LIST_SELECT)
            .prefetch_related(*NOVEL_LIST_PREFETCH)
        )
        query = self.request.GET.get("q", "").strip()
        if query:
            from django.db.models import Q

            qs = qs.filter(Q(title__icontains=query) | Q(author__name__icontains=query))
        for field in ("genre", "status", "ptype"):
            val = self.request.GET.get(field)
            if val:
                try:
                    qs = qs.filter(**{field: int(val)})
                except (ValueError, TypeError):
                    pass

        sort = self.request.GET.get("sort", "")
        if sort in self.SORT_OPTIONS and sort:
            qs = qs.order_by(f"-{sort}")
        else:
            qs = qs.order_by("-click_num")

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["query"] = self.request.GET.get("q", "").strip()

        def _choices(mapping):
            return [
                {"value": m.value, "label": mapping.get_zh(m.value)}
                for m in mapping.enum
                if m.name != "OTHER"
            ]

        ctx["genres"] = _choices(GENRE)
        ctx["statuses"] = _choices(STATUS)
        ctx["ptypes"] = _choices(PTYPE)
        ctx["current_genre"] = self.request.GET.get("genre", "")
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["current_ptype"] = self.request.GET.get("ptype", "")
        ctx["current_sort"] = self.request.GET.get("sort", "")
        ctx["sort_options"] = self.SORT_OPTIONS

        latest_banner = cache.get("latest_banner")
        if latest_banner is None:
            latest_banner = (
                Novel.objects.filter(has_banner=True).order_by("-last_update").first()
            )
            cache.set("latest_banner", latest_banner, timeout=300)
        ctx["latest_banner"] = latest_banner

        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["querystring"] = params.urlencode()
        return ctx


class NovelDetailView(DetailView):
    model = Novel
    template_name = "novels/detail.html"
    context_object_name = "novel"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(*NOVEL_LIST_SELECT)
            .prefetch_related(*NOVEL_LIST_PREFETCH)
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        novel = self.object

        # Cache rank calculation for 5 minutes
        cache_key = f"novel_ranks_{novel.id}"
        ranks = cache.get(cache_key)
        if ranks is None:
            from django.db.models import Q, Sum, Case, When, Value, IntegerField

            stats = [
                "word_num",
                "click_num",
                "like_num",
                "praise_num",
                "review_num",
                "comment_num",
            ]
            q = Q()
            for field in stats:
                val = getattr(novel, field)
                if val is not None:
                    q |= Q(**{f"{field}__gt": val})

            if q:
                counts = Novel.objects.filter(q).aggregate(
                    **{
                        f"{field}_gt": Sum(
                            Case(
                                When(
                                    **{f"{field}__gt": getattr(novel, field)},
                                    then=Value(1),
                                ),
                                default=Value(0),
                                output_field=IntegerField(),
                            )
                        )
                        for field in stats
                        if getattr(novel, field) is not None
                    }
                )
                ranks = {
                    k.replace("_gt", ""): v + 1
                    for k, v in counts.items()
                    if v is not None
                }
            else:
                ranks = {field: 1 for field in stats}

            cache.set(cache_key, ranks, timeout=300)

        ctx["ranks"] = ranks
        return ctx


class NovelRankView(ListView):
    model = Novel
    template_name = "novels/rank.html"
    context_object_name = "novels"
    paginate_by = _rank_paginate_by

    SORTABLE = {c.get("sort_key", c["key"]) for c in COLUMNS if c["sortable"]}

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related(*NOVEL_LIST_SELECT)
            .prefetch_related(*NOVEL_LIST_PREFETCH)
        )
        sort = self.request.GET.get("sort", "click_num")
        if sort not in self.SORTABLE:
            sort = "click_num"
        direction = self.request.GET.get("dir", "desc")
        if direction not in ("asc", "desc"):
            direction = "desc"
        return qs.order_by(f"{'-' if direction == 'desc' else ''}{sort}")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        sort = self.request.GET.get("sort", "click_num")
        direction = self.request.GET.get("dir", "desc")
        ctx["current_sort"] = sort if sort in self.SORTABLE else "click_num"
        ctx["current_dir"] = direction
        page_obj = ctx.get("page_obj")
        ctx["page_start"] = (
            (page_obj.number - 1) * self.paginate_by + 1 if page_obj else 1
        )
        ctx["columns"] = COLUMNS
        params = self.request.GET.copy()
        params.pop("page", None)
        params.pop("sort", None)
        params.pop("dir", None)
        ctx["querystring"] = params.urlencode()
        return ctx
