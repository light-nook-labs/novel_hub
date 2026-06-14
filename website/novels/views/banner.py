from django.views.generic import ListView

from ..models import Novel

_pagination = __import__("django.conf", fromlist=["settings"]).settings.TOML.get(
    "pagination", {}
)
_banner_paginate_by = _pagination.get("banner_per_page", 12)


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
