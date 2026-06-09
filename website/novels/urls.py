from django.urls import path
from . import views

app_name = "novels"

urlpatterns = [
    path("", views.NovelListView.as_view(), name="index"),
    path("rank/", views.NovelRankView.as_view(), name="rank"),
    path("banners/", views.BannerListView.as_view(), name="banners"),
    path("novel/<int:pk>/", views.NovelDetailView.as_view(), name="detail"),
    path("authors/", views.AuthorListView.as_view(), name="authors"),
    path("authors/<int:pk>/", views.AuthorDetailView.as_view(), name="author_detail"),
    path("tags/", views.TagListView.as_view(), name="tags"),
    path("tags/<int:pk>/", views.TagDetailView.as_view(), name="tag_detail"),
    path("contests/", views.ContestListView.as_view(), name="contests"),
    path(
        "contests/<int:pk>/", views.ContestDetailView.as_view(), name="contest_detail"
    ),
    path(
        "genres/", views.EnumListView.as_view(), {"enum_type": "genre"}, name="genres"
    ),
    path(
        "genres/<int:value>/",
        views.EnumDetailView.as_view(),
        {"enum_type": "genre"},
        name="genre_detail",
    ),
    path(
        "statuses/",
        views.EnumListView.as_view(),
        {"enum_type": "status"},
        name="statuses",
    ),
    path(
        "statuses/<int:value>/",
        views.EnumDetailView.as_view(),
        {"enum_type": "status"},
        name="status_detail",
    ),
    path(
        "ptypes/", views.EnumListView.as_view(), {"enum_type": "ptype"}, name="ptypes"
    ),
    path(
        "ptypes/<int:value>/",
        views.EnumDetailView.as_view(),
        {"enum_type": "ptype"},
        name="ptype_detail",
    ),
    path("about/", views.AboutView.as_view(), name="about"),
]
