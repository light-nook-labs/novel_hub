from django.views.generic import ListView
from django.http import Http404

from ..models import Novel
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


class EnumListView(ListView):
    template_name = "novels/enum_list.html"
    context_object_name = "items"
    paginate_by = None  # few enum values, no pagination needed

    ENUM_MAP = {"genre": GENRE, "status": STATUS, "ptype": PTYPE}

    def dispatch(self, request, *args, **kwargs):
        self.enum_type = kwargs["enum_type"]
        self.mapping = self.ENUM_MAP.get(self.enum_type)
        if not self.mapping:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        from django.db.models import Count

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
            },
            3: {
                "bg": "#ffedd5",
                "text": "#9a3412",
                "bg_d": "#7c2d12",
                "text_d": "#fb923c",
            },
            4: {
                "bg": "#ffe4e6",
                "text": "#9f1239",
                "bg_d": "#881337",
                "text_d": "#fb7185",
            },
            5: {
                "bg": "#fef9c3",
                "text": "#854d0e",
                "bg_d": "#713f12",
                "text_d": "#facc15",
            },
            6: {
                "bg": "#ecfccb",
                "text": "#3f6212",
                "bg_d": "#365314",
                "text_d": "#a3e635",
            },
            7: {
                "bg": "#e5e7eb",
                "text": "#374151",
                "bg_d": "#1f2937",
                "text_d": "#d1d5db",
            },
            8: {
                "bg": "#fce7f3",
                "text": "#9d174d",
                "bg_d": "#831843",
                "text_d": "#f472b6",
            },
            9: {
                "bg": "#f5f5f4",
                "text": "#57534e",
                "bg_d": "#44403c",
                "text_d": "#a8a29e",
            },
            10: {
                "bg": "#ffedd5",
                "text": "#c2410c",
                "bg_d": "#9a3412",
                "text_d": "#fdba74",
            },
        },
        "status": {
            2: {
                "bg": "#fef3c7",
                "text": "#92400e",
                "bg_d": "#78350f",
                "text_d": "#fcd34d",
            },
            3: {
                "bg": "#ffe4e6",
                "text": "#9f1239",
                "bg_d": "#881337",
                "text_d": "#fb7185",
            },
            4: {
                "bg": "#e5e7eb",
                "text": "#374151",
                "bg_d": "#1f2937",
                "text_d": "#d1d5db",
            },
            5: {
                "bg": "#ffedd5",
                "text": "#9a3412",
                "bg_d": "#7c2d12",
                "text_d": "#fb923c",
            },
            6: {
                "bg": "#fef9c3",
                "text": "#854d0e",
                "bg_d": "#713f12",
                "text_d": "#facc15",
            },
        },
        "ptype": {
            2: {
                "bg": "#fef3c7",
                "text": "#92400e",
                "bg_d": "#78350f",
                "text_d": "#fcd34d",
            },
            3: {
                "bg": "#fce7f3",
                "text": "#9d174d",
                "bg_d": "#831843",
                "text_d": "#f472b6",
            },
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
            raise Http404
        self.enum_value = int(kwargs["value"])
        try:
            self.mapping.enum(self.enum_value)
        except ValueError:
            raise Http404
        self.enum_label = self.mapping.get_zh(self.enum_value)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = (
            Novel.objects.filter(**{self.enum_type: self.enum_value})
            .select_related("author", "contest")
            .prefetch_related("tags")
        )

        # Apply filters
        genre = self.request.GET.get("genre")
        status = self.request.GET.get("status")
        ptype = self.request.GET.get("ptype")

        if self.enum_type != "genre" and genre:
            qs = qs.filter(genre=int(genre))
        if self.enum_type != "status" and status:
            qs = qs.filter(status=int(status))
        if self.enum_type != "ptype" and ptype:
            qs = qs.filter(ptype=int(ptype))

        # Apply sorting
        sort = self.request.GET.get("sort", "click_num")
        if sort in SORT_OPTIONS and sort:
            qs = qs.order_by(f"-{sort}")
        else:
            qs = qs.order_by("-click_num")

        return qs

    LIST_URLS = {"genre": "genres", "status": "statuses", "ptype": "ptypes"}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["enum_type"] = self.enum_type
        ctx["enum_value"] = self.enum_value
        ctx["enum_label"] = self.enum_label
        ctx["list_url"] = self.LIST_URLS[self.enum_type]
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
