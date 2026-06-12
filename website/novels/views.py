from django.views.generic import ListView, DetailView, TemplateView
from django.conf import settings
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
        genre = self.request.GET.get("genre")
        status = self.request.GET.get("status")
        ptype = self.request.GET.get("ptype")
        if genre:
            qs = qs.filter(genre=int(genre))
        if status:
            qs = qs.filter(status=int(status))
        if ptype:
            qs = qs.filter(ptype=int(ptype))

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

        latest_banner = (
            Novel.objects.filter(has_banner=True).order_by("-last_update").first()
        )
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

        from django.db.models import Q, Sum, Case, When, Value, IntegerField

        stats = ["word_num", "click_num", "like_num", "praise_num", "review_num", "comment_num"]
        q = Q()
        for field in stats:
            val = getattr(novel, field)
            if val is not None:
                q |= Q(**{f"{field}__gt": val})

        if q:
            counts = Novel.objects.filter(q).aggregate(
                **{f"{field}_gt": Sum(
                    Case(
                        When(**{f"{field}__gt": getattr(novel, field)}, then=Value(1)),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                ) for field in stats if getattr(novel, field) is not None}
            )
            ranks = {k.replace("_gt", ""): v + 1 for k, v in counts.items() if v is not None}
        else:
            ranks = {field: 1 for field in stats}

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
        from django.db.models import Subquery, OuterRef

        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(name__icontains=q)

        top_novel = (
            Novel.objects.filter(author=OuterRef("pk"))
            .order_by("-click_num")
            .values("id", "title", "click_num")[:1]
        )

        qs = qs.annotate(
            novel_count=models.Count("novels"),
            total_click=models.Sum("novels__click_num"),
            total_word=models.Sum("novels__word_num"),
            total_like=models.Sum("novels__like_num"),
            total_praise=models.Sum("novels__praise_num"),
            total_review=models.Sum("novels__review_num"),
            total_comment=models.Sum("novels__comment_num"),
            banner_count=models.Count("novels", filter=models.Q(novels__has_banner=True)),
            latest_update=models.Max("novels__last_update"),
            top_novel_id=Subquery(top_novel.values("id")),
            top_novel_title=Subquery(top_novel.values("title")),
            top_novel_click=Subquery(top_novel.values("click_num")),
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
        return ctx


class AuthorDetailView(DetailView):
    model = Author
    template_name = "novels/author_detail.html"
    context_object_name = "author"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        novels_qs = (
            self.object.novels.select_related("contest")
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
            self.object.novels.select_related("author")
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
