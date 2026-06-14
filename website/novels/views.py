from django.views.generic import ListView, DetailView, TemplateView
from django.conf import settings
from django.core.cache import cache
from django.db import models

from .models import Novel, Author, Tag, Contest
from .mappings import GENRE, STATUS, PTYPE

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
_detail_novel_limit = _pagination.get("detail_novel_limit", 50)


# ── Novel views ──────────────────────────────────────────────────────


class NovelListView(ListView):
    model = Novel
    template_name = "novels/index.html"
    context_object_name = "novels"
    paginate_by = _paginate_by

    SORT_OPTIONS = {
        "": "综合排序",
        "click_num": "点击排序",
        "word_num": "字数排序",
        "like_num": "收藏排序",
        "praise_num": "点赞排序",
        "last_update": "最近更新",
        "db_update": "最近同步",
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


# ── Rank ─────────────────────────────────────────────────────────────


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
        ctx["querystring"] = params.urlencode()
        return ctx


# ── Author ───────────────────────────────────────────────────────────


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


# ── Tag ──────────────────────────────────────────────────────────────


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


# ── Contest ──────────────────────────────────────────────────────────


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


class ContestDetailView(DetailView):
    model = Contest
    template_name = "novels/contest_detail.html"
    context_object_name = "contest"

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


# ── Enum pages (genre / status / ptype) ──────────────────────────────


class EnumListView(ListView):
    template_name = "novels/enum_list.html"
    context_object_name = "items"
    paginate_by = None  # few enum values, no pagination needed

    ENUM_MAP = {"genre": GENRE, "status": STATUS, "ptype": PTYPE}

    def dispatch(self, request, *args, **kwargs):
        self.enum_type = kwargs["enum_type"]
        self.mapping = self.ENUM_MAP.get(self.enum_type)
        if not self.mapping:
            from django.http import Http404

            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        from django.db.models import Count
        from .models import Novel

        colors = self.BADGE_COLORS.get(self.enum_type, {})
        counts = dict(
            Novel.objects.values_list(self.enum_type)
            .annotate(c=Count("id"))
            .values_list(self.enum_type, "c")
        )
        return [
            {
                "value": m.value,
                "label": self.mapping.get_zh(m.value),
                "color": colors.get(m.value, {}),
                "novel_count": counts.get(m.value, 0),
            }
            for m in self.mapping.enum
            if m.name != "OTHER"
        ]

    BADGE_COLORS = {
        "genre": {
            2: {
                "bg": "#fef3c7",
                "text": "#92400e",
                "bg_d": "#78350f",
                "text_d": "#fcd34d",
            },  # amber
            3: {
                "bg": "#ffedd5",
                "text": "#9a3412",
                "bg_d": "#7c2d12",
                "text_d": "#fb923c",
            },  # orange
            4: {
                "bg": "#ffe4e6",
                "text": "#9f1239",
                "bg_d": "#881337",
                "text_d": "#fb7185",
            },  # rose
            5: {
                "bg": "#fef9c3",
                "text": "#854d0e",
                "bg_d": "#713f12",
                "text_d": "#facc15",
            },  # yellow
            6: {
                "bg": "#ecfccb",
                "text": "#3f6212",
                "bg_d": "#365314",
                "text_d": "#a3e635",
            },  # lime
            7: {
                "bg": "#e5e7eb",
                "text": "#374151",
                "bg_d": "#1f2937",
                "text_d": "#d1d5db",
            },  # gray
            8: {
                "bg": "#fce7f3",
                "text": "#9d174d",
                "bg_d": "#831843",
                "text_d": "#f472b6",
            },  # pink
            9: {
                "bg": "#f5f5f4",
                "text": "#57534e",
                "bg_d": "#44403c",
                "text_d": "#a8a29e",
            },  # stone
            10: {
                "bg": "#ffedd5",
                "text": "#c2410c",
                "bg_d": "#9a3412",
                "text_d": "#fdba74",
            },  # light orange
        },
        "status": {
            2: {
                "bg": "#fef3c7",
                "text": "#92400e",
                "bg_d": "#78350f",
                "text_d": "#fcd34d",
            },  # amber
            3: {
                "bg": "#ffe4e6",
                "text": "#9f1239",
                "bg_d": "#881337",
                "text_d": "#fb7185",
            },  # rose
            4: {
                "bg": "#e5e7eb",
                "text": "#374151",
                "bg_d": "#1f2937",
                "text_d": "#d1d5db",
            },  # gray
            5: {
                "bg": "#ffedd5",
                "text": "#9a3412",
                "bg_d": "#7c2d12",
                "text_d": "#fb923c",
            },  # orange
            6: {
                "bg": "#fef9c3",
                "text": "#854d0e",
                "bg_d": "#713f12",
                "text_d": "#facc15",
            },  # yellow
        },
        "ptype": {
            2: {
                "bg": "#fef3c7",
                "text": "#92400e",
                "bg_d": "#78350f",
                "text_d": "#fcd34d",
            },  # amber
            3: {
                "bg": "#fce7f3",
                "text": "#9d174d",
                "bg_d": "#831843",
                "text_d": "#f472b6",
            },  # pink
        },
    }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["enum_type"] = self.enum_type
        ctx["enum_label"] = {"genre": "分类", "status": "状态", "ptype": "类型"}.get(
            self.enum_type, ""
        )
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["querystring"] = params.urlencode()
        return ctx


class EnumDetailView(ListView):
    template_name = "novels/enum_detail.html"
    context_object_name = "novels"
    paginate_by = _paginate_by

    ENUM_MAP = {"genre": GENRE, "status": STATUS, "ptype": PTYPE}

    def dispatch(self, request, *args, **kwargs):
        self.enum_type = kwargs["enum_type"]
        self.mapping = self.ENUM_MAP.get(self.enum_type)
        if not self.mapping:
            from django.http import Http404

            raise Http404
        self.enum_value = int(kwargs["value"])
        try:
            self.mapping.enum(self.enum_value)
        except ValueError:
            from django.http import Http404

            raise Http404
        self.enum_label = self.mapping.get_zh(self.enum_value)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            Novel.objects.filter(**{self.enum_type: self.enum_value})
            .select_related("author", "contest")
            .prefetch_related("tags")
        )

    LIST_URLS = {"genre": "genres", "status": "statuses", "ptype": "ptypes"}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["enum_type"] = self.enum_type
        ctx["enum_value"] = self.enum_value
        ctx["enum_label"] = self.enum_label
        ctx["list_url"] = self.LIST_URLS[self.enum_type]
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["querystring"] = params.urlencode()
        return ctx


# ── Banner ───────────────────────────────────────────────────────────


class BannerListView(ListView):
    model = Novel
    template_name = "novels/banners.html"
    context_object_name = "novels"
    paginate_by = _banner_paginate_by

    def get_queryset(self):
        return (
            Novel.objects.filter(has_banner=True)
            .select_related("author", "contest")
            .prefetch_related("tags")
            .order_by("-last_update")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["querystring"] = params.urlencode()
        return ctx


# ── About ────────────────────────────────────────────────────────────


class AboutView(TemplateView):
    template_name = "novels/about.html"


# ── Stats / Dashboard ────────────────────────────────────────────────


class DashboardView(TemplateView):
    template_name = "novels/dashboard.html"

    def get_context_data(self, **kwargs):
        import plotly.graph_objects as go
        import plotly.express as px
        from django.db.models import (
            Count,
            Avg,
            Sum,
            Q,
            F,
            Case,
            When,
            Value,
            IntegerField,
        )

        ctx = super().get_context_data(**kwargs)

        # Summary
        ctx["novel_count"] = Novel.objects.count()
        ctx["author_count"] = Author.objects.count()
        ctx["tag_count"] = Tag.objects.count()
        ctx["contest_count"] = Contest.objects.count()

        # Colors
        amber = "#f59e0b"
        orange = "#f97316"
        rose = "#f43f5e"
        colors = [
            "#f59e0b",
            "#f97316",
            "#ef4444",
            "#ec4899",
            "#8b5cf6",
            "#6366f1",
            "#3b82f6",
            "#06b6d4",
            "#10b981",
            "#84cc16",
            "#fbbf24",
            "#fb923c",
            "#f87171",
            "#f472b6",
            "#a78bfa",
        ]

        def _layout(height=300, **kwargs):
            return dict(
                margin=dict(t=20, b=30, l=30, r=20),
                height=height,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(size=12),
                **kwargs,
            )

        def _to_html(fig, include_js=False):
            return fig.to_html(
                full_html=False,
                include_plotlyjs=include_js,
                config={"displayModeBar": False, "responsive": True},
            )

        def _to_json(fig):
            import json

            fig_dict = fig.to_dict()
            return json.dumps(
                {
                    "data": fig_dict["data"],
                    "layout": fig_dict["layout"],
                },
                ensure_ascii=False,
            )

        def _w(val):
            """Format number as X.Xw (1w = 10000)"""
            if val is None or val == 0:
                return "0"
            if val >= 10000:
                return f"{val/10000:.1f}w"
            return str(val)

        def _w_axis(val):
            """Format axis tick as Xw"""
            if val >= 10000:
                return f"{val/10000:.0f}w"
            return str(int(val))

        # 1. Genre distribution (donut)
        genre_stats = dict(
            Novel.objects.values_list("genre")
            .annotate(c=Count("id"))
            .values_list("genre", "c")
        )
        genre_labels = [GENRE.get_zh(i) for i in range(2, 11)]
        genre_data = [genre_stats.get(i, 0) for i in range(2, 11)]

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=genre_labels,
                    values=genre_data,
                    hole=0.5,
                    marker_colors=colors,
                    textinfo="label+percent",
                    textposition="outside",
                    textfont=dict(size=11),
                )
            ]
        )
        fig.update_layout(**_layout(240), showlegend=False)
        ctx["chart_genre_json"] = _to_json(fig)

        # 2. Status distribution - multiple pie charts
        status_stats = dict(
            Novel.objects.values_list("status")
            .annotate(c=Count("id"))
            .values_list("status", "c")
        )
        # FINISHED=2, ON_GOING=3, DIED=4, ACTIVE_D=5, ACTIVE_F=6, REMOVED=7

        # 2a. Real type: 已完结 (FINISHED+ACTIVE_F) vs 连载中 (ON_GOING+DIED+ACTIVE_D)
        real_finished = status_stats.get(2, 0) + status_stats.get(6, 0)
        real_ongoing = (
            status_stats.get(3, 0) + status_stats.get(4, 0) + status_stats.get(5, 0)
        )
        real_removed = status_stats.get(7, 0)
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=["已完结", "连载中", "下架"],
                    values=[real_finished, real_ongoing, real_removed],
                    hole=0.5,
                    marker_colors=[amber, orange, "#94a3b8"],
                    textinfo="label+percent",
                    textposition="outside",
                    textfont=dict(size=11),
                )
            ]
        )
        fig.update_layout(**_layout(240), showlegend=False)
        ctx["chart_real_type_json"] = _to_json(fig)

        # 2b. Status without A (no ACTIVE_D, ACTIVE_F)
        no_a_labels = ["连载中", "已完结", "断更", "下架"]
        no_a_data = [
            status_stats.get(3, 0),
            status_stats.get(2, 0),
            status_stats.get(4, 0),
            status_stats.get(7, 0),
        ]
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=no_a_labels,
                    values=no_a_data,
                    hole=0.5,
                    marker_colors=[orange, amber, rose, "#94a3b8"],
                    textinfo="label+percent",
                    textposition="outside",
                    textfont=dict(size=11),
                )
            ]
        )
        fig.update_layout(**_layout(240), showlegend=False)
        ctx["chart_status_no_a_json"] = _to_json(fig)

        # 2c. Status with A (all statuses)
        all_labels = ["连载中", "已完结", "断更", "断更A", "完结A", "下架"]
        all_data = [
            status_stats.get(3, 0),
            status_stats.get(2, 0),
            status_stats.get(4, 0),
            status_stats.get(5, 0),
            status_stats.get(6, 0),
            status_stats.get(7, 0),
        ]
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=all_labels,
                    values=all_data,
                    hole=0.5,
                    marker_colors=[
                        orange,
                        amber,
                        rose,
                        "#f472b6",
                        "#fbbf24",
                        "#94a3b8",
                    ],
                    textinfo="label+percent",
                    textposition="outside",
                    textfont=dict(size=11),
                )
            ]
        )
        fig.update_layout(**_layout(240), showlegend=False)
        ctx["chart_status_with_a_json"] = _to_json(fig)

        # 2d. 连载中 breakdown without A: 连载中 vs 断更
        ongoing_labels = ["连载中", "断更"]
        ongoing_data = [status_stats.get(3, 0), status_stats.get(4, 0)]
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=ongoing_labels,
                    values=ongoing_data,
                    hole=0.5,
                    marker_colors=[orange, rose],
                    textinfo="label+percent",
                    textposition="outside",
                    textfont=dict(size=11),
                )
            ]
        )
        fig.update_layout(**_layout(240), showlegend=False)
        ctx["chart_ongoing_breakdown_json"] = _to_json(fig)

        # 3. Top 15 tags (horizontal bar, log scale)
        top_tags = (
            Tag.objects.annotate(novel_count=Count("novels"))
            .filter(novel_count__gt=0)
            .order_by("-novel_count")[:15]
        )
        tag_labels = [t.name for t in top_tags]
        tag_data = [t.novel_count for t in top_tags]

        fig = go.Figure(
            data=[
                go.Bar(
                    y=tag_labels[::-1],
                    x=tag_data[::-1],
                    orientation="h",
                    marker_color=amber,
                    text=[_w(d) for d in tag_data[::-1]],
                    textposition="outside",
                )
            ]
        )
        fig.update_layout(
            **_layout(380),
            yaxis=dict(autorange="reversed"),
            xaxis=dict(
                type="log",
                gridcolor="rgba(128,128,128,0.2)",
                ticktext=[_w_axis(v) for v in [10, 100, 1000, 10000, 100000]],
                tickvals=[10, 100, 1000, 10000, 100000],
            ),
        )
        ctx["chart_tags_json"] = _to_json(fig)

        # 4. Top 10 authors by total clicks (horizontal bar, log scale)
        top_authors = (
            Author.objects.annotate(
                novel_count=Count("novels"),
                total_click=Sum("novels__click_num"),
            )
            .filter(novel_count__gt=0)
            .order_by("-total_click")[:10]
        )
        author_labels = [a.name[:8] for a in top_authors]
        author_clicks = [a.total_click or 0 for a in top_authors]

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                y=author_labels[::-1],
                x=author_clicks[::-1],
                orientation="h",
                marker_color=orange,
                text=[_w(c) for c in author_clicks[::-1]],
                textposition="outside",
            )
        )
        fig.update_layout(
            **_layout(380),
            yaxis=dict(autorange="reversed"),
            xaxis=dict(
                type="log",
                gridcolor="rgba(128,128,128,0.2)",
                ticktext=[_w_axis(v) for v in [100000, 1000000, 10000000, 100000000]],
                tickvals=[100000, 1000000, 10000000, 100000000],
            ),
        )
        ctx["chart_authors_json"] = _to_json(fig)

        # 5. Click vs Like scatter (log scale, color by genre)
        sample_novels = Novel.objects.filter(click_num__gt=0, like_num__gt=0).values(
            "click_num", "like_num", "title", "genre"
        )[:3000]
        scatter_x = [n["click_num"] for n in sample_novels]
        scatter_y = [n["like_num"] for n in sample_novels]
        scatter_text = [n["title"][:20] for n in sample_novels]
        scatter_color = [GENRE.get_zh(n["genre"]) for n in sample_novels]

        fig = go.Figure(
            data=[
                go.Scatter(
                    x=scatter_x,
                    y=scatter_y,
                    mode="markers",
                    marker=dict(size=4, opacity=0.5, line=dict(width=0)),
                    text=scatter_text,
                    customdata=scatter_color,
                    hovertemplate="%{text}<br>分类: %{customdata}<br>点击: %{x}<br>收藏: %{y}",
                )
            ]
        )
        fig.update_layout(
            **_layout(350),
            xaxis=dict(title="点击", type="log", gridcolor="rgba(128,128,128,0.2)"),
            yaxis=dict(title="收藏", type="log", gridcolor="rgba(128,128,128,0.2)"),
        )
        ctx["chart_scatter_json"] = _to_json(fig)

        # 6. Ptype distribution (donut)
        ptype_stats = dict(
            Novel.objects.values_list("ptype")
            .annotate(c=Count("id"))
            .values_list("ptype", "c")
        )
        ptype_labels = [PTYPE.get_zh(i) for i in range(2, 5)]
        ptype_data = [ptype_stats.get(i, 0) for i in range(2, 5)]

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=ptype_labels,
                    values=ptype_data,
                    hole=0.5,
                    marker_colors=[amber, rose, "#6366f1"],
                    textinfo="label+percent",
                    textposition="outside",
                )
            ]
        )
        fig.update_layout(**_layout(240), showlegend=False)
        ctx["chart_ptype_json"] = _to_json(fig)

        # 7. Word count distribution (histogram, log x-axis)
        word_data = list(
            Novel.objects.filter(word_num__gt=0).values_list("word_num", flat=True)[
                :50000
            ]
        )

        fig = go.Figure(
            data=[
                go.Histogram(
                    x=word_data,
                    nbinsx=40,
                    marker_color=amber,
                    opacity=0.8,
                )
            ]
        )
        fig.update_layout(
            **_layout(280),
            xaxis=dict(title="字数", type="log", gridcolor="rgba(128,128,128,0.2)"),
            yaxis=dict(title="小说数", gridcolor="rgba(128,128,128,0.2)"),
        )
        ctx["chart_word_dist_json"] = _to_json(fig)

        # 8. Top contests (horizontal bar, log scale)
        top_contests = (
            Contest.objects.annotate(novel_count=Count("novels"))
            .filter(novel_count__gt=0)
            .order_by("-novel_count")[:10]
        )
        contest_labels = [c.name[:12] for c in top_contests]
        contest_data = [c.novel_count for c in top_contests]

        fig = go.Figure(
            data=[
                go.Bar(
                    y=contest_labels[::-1],
                    x=contest_data[::-1],
                    orientation="h",
                    marker_color=colors[: len(contest_labels)],
                    text=[_w(d) for d in contest_data[::-1]],
                    textposition="outside",
                )
            ]
        )
        fig.update_layout(
            **_layout(320),
            yaxis=dict(autorange="reversed"),
            xaxis=dict(type="log", gridcolor="rgba(128,128,128,0.2)"),
        )
        ctx["chart_contests_json"] = _to_json(fig)

        # 9. Genre x Status heatmap
        heatmap_data = Novel.objects.values("genre", "status").annotate(c=Count("id"))
        genre_range = list(range(2, 11))
        status_range = list(range(2, 8))
        heat_matrix = []
        for g in genre_range:
            row = []
            for s in status_range:
                val = next(
                    (
                        h["c"]
                        for h in heatmap_data
                        if h["genre"] == g and h["status"] == s
                    ),
                    0,
                )
                row.append(val)
            heat_matrix.append(row)

        fig = go.Figure(
            data=[
                go.Heatmap(
                    z=heat_matrix,
                    x=[STATUS.get_zh(s) for s in status_range],
                    y=[GENRE.get_zh(g) for g in genre_range],
                    colorscale="YlOrRd",
                    text=heat_matrix,
                    texttemplate="%{text}",
                    textfont=dict(size=10),
                )
            ]
        )
        fig.update_layout(**_layout(350))
        ctx["chart_heatmap_json"] = _to_json(fig)

        # 10. Top 10 novels by click (horizontal bar)
        top_click = Novel.objects.order_by("-click_num")[:10]
        fig = go.Figure(
            data=[
                go.Bar(
                    y=[n.title[:12] for n in top_click][::-1],
                    x=[n.click_num or 0 for n in top_click][::-1],
                    orientation="h",
                    marker_color=amber,
                    text=[_w(n.click_num) for n in top_click][::-1],
                    textposition="outside",
                )
            ]
        )
        fig.update_layout(
            **_layout(320),
            yaxis=dict(autorange="reversed"),
            xaxis=dict(
                type="log",
                gridcolor="rgba(128,128,128,0.2)",
                ticktext=[_w_axis(v) for v in [1000000, 10000000, 100000000]],
                tickvals=[1000000, 10000000, 100000000],
            ),
        )
        ctx["chart_top_click_json"] = _to_json(fig)

        # 11. Top 10 novels by like (horizontal bar)
        top_like = Novel.objects.order_by("-like_num")[:10]
        fig = go.Figure(
            data=[
                go.Bar(
                    y=[n.title[:12] for n in top_like][::-1],
                    x=[n.like_num or 0 for n in top_like][::-1],
                    orientation="h",
                    marker_color=orange,
                    text=[_w(n.like_num) for n in top_like][::-1],
                    textposition="outside",
                )
            ]
        )
        fig.update_layout(
            **_layout(320),
            yaxis=dict(autorange="reversed"),
            xaxis=dict(
                type="log",
                gridcolor="rgba(128,128,128,0.2)",
                ticktext=[_w_axis(v) for v in [10000, 100000, 1000000]],
                tickvals=[10000, 100000, 1000000],
            ),
        )
        ctx["chart_top_like_json"] = _to_json(fig)

        # 12. Banner vs Non-Banner comparison (grouped bar)
        banner_stats = Novel.objects.aggregate(
            banner_click=Sum("click_num", filter=Q(has_banner=True)),
            nonbanner_click=Sum("click_num", filter=Q(has_banner=False)),
            banner_like=Sum("like_num", filter=Q(has_banner=True)),
            nonbanner_like=Sum("like_num", filter=Q(has_banner=False)),
            banner_praise=Sum("praise_num", filter=Q(has_banner=True)),
            nonbanner_praise=Sum("praise_num", filter=Q(has_banner=False)),
            banner_count=Count("id", filter=Q(has_banner=True)),
            nonbanner_count=Count("id", filter=Q(has_banner=False)),
        )
        metrics = ["点击", "收藏", "点赞"]
        banner_vals = [
            banner_stats["banner_click"] or 0,
            banner_stats["banner_like"] or 0,
            banner_stats["banner_praise"] or 0,
        ]
        nonbanner_vals = [
            banner_stats["nonbanner_click"] or 0,
            banner_stats["nonbanner_like"] or 0,
            banner_stats["nonbanner_praise"] or 0,
        ]
        # Normalize per novel
        bc = banner_stats["banner_count"] or 1
        nc = banner_stats["nonbanner_count"] or 1
        banner_per = [v / bc for v in banner_vals]
        nonbanner_per = [v / nc for v in nonbanner_vals]

        fig = go.Figure()
        fig.add_trace(
            go.Bar(x=metrics, y=banner_per, name=f"Banner ({bc}部)", marker_color=amber)
        )
        fig.add_trace(
            go.Bar(
                x=metrics,
                y=nonbanner_per,
                name=f"非Banner ({nc}部)",
                marker_color="#94a3b8",
            )
        )
        fig.update_layout(
            **_layout(300),
            barmode="group",
            yaxis=dict(type="log", gridcolor="rgba(128,128,128,0.2)"),
        )
        ctx["chart_banner_json"] = _to_json(fig)

        # 13. A-status candidates (novels close to A-status)
        a_criteria = (
            Q(has_banner=True)
            | Q(click_num__gte=10000000)
            | Q(review_num__gte=60)
            | Q(like_num__gte=10000)
            | Q(praise_num__gte=10000)
        )
        a_count = Novel.objects.filter(
            a_criteria, status__in=[3, 2]
        ).count()  # died or finished
        not_a_count = Novel.objects.filter(~a_criteria, status__in=[3, 2]).count()
        already_a = Novel.objects.filter(
            status__in=[4, 5]
        ).count()  # active_d or active_f

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=["已是A状态", "符合A条件(待升级)", "不符合A条件"],
                    values=[already_a, a_count, not_a_count],
                    hole=0.5,
                    marker_colors=[amber, orange, "#94a3b8"],
                    textinfo="label+value",
                    textposition="outside",
                )
            ]
        )
        fig.update_layout(**_layout(240), showlegend=False)
        ctx["chart_a_status_json"] = _to_json(fig)

        return ctx


# ── Comments view ────────────────────────────────────────────────────


class CommentsView(TemplateView):
    template_name = "novels/comments.html"
