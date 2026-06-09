from django.views.generic import ListView, DetailView

from .models import Novel, Author, Tag, Contest
from .mappings import GENRE, STATUS, PTYPE
from config.toml import _load_config

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
_paginate_by = _load_config().get("pagination", {}).get("per_page", 20)


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
        "id": "最近收录",
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


# ── Rank ─────────────────────────────────────────────────────────────


class NovelRankView(ListView):
    model = Novel
    template_name = "novels/rank.html"
    context_object_name = "novels"
    paginate_by = 100

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
    paginate_by = _paginate_by

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(name__icontains=q)
        return qs.annotate_novel_count()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
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
        ctx["novels"] = novels_qs[:50]
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
        ctx["novels"] = novels_qs[:50]
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
        ctx["novels"] = novels_qs[:50]
        ctx["novel_count"] = self.object.novels.count()
        return ctx


# ── Enum pages (genre / status / ptype) ──────────────────────────────


class EnumListView(ListView):
    template_name = "novels/enum_list.html"
    context_object_name = "items"
    paginate_by = _paginate_by

    ENUM_MAP = {"genre": GENRE, "status": STATUS, "ptype": PTYPE}

    def dispatch(self, request, *args, **kwargs):
        self.enum_type = kwargs["enum_type"]
        self.mapping = self.ENUM_MAP.get(self.enum_type)
        if not self.mapping:
            from django.http import Http404

            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return [
            {"value": m.value, "label": self.mapping.get_zh(m.value)}
            for m in self.mapping.enum
            if m.name != "OTHER"
        ]

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
        self.enum_label = self.mapping.get_zh(self.enum_value)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            Novel.objects.filter(**{self.enum_type: self.enum_value})
            .select_related("author", "contest")
            .prefetch_related("tags")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["enum_type"] = self.enum_type
        ctx["enum_value"] = self.enum_value
        ctx["enum_label"] = self.enum_label
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["querystring"] = params.urlencode()
        return ctx


# ── Banner ───────────────────────────────────────────────────────────


class BannerListView(ListView):
    model = Novel
    template_name = "novels/banners.html"
    context_object_name = "novels"
    paginate_by = 12

    def get_queryset(self):
        return (
            Novel.objects.filter(has_banner=True)
            .select_related("author", "contest")
            .prefetch_related("tags")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["querystring"] = params.urlencode()
        return ctx
