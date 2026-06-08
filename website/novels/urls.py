from django.urls import path
from . import views

app_name = "novels"

urlpatterns = [
    path("", views.NovelListView.as_view(), name="index"),
    path("rank/", views.NovelRankView.as_view(), name="rank"),
    path("novel/<int:pk>/", views.NovelDetailView.as_view(), name="detail"),
    path("authors/", views.AuthorListView.as_view(), name="authors"),
    path("authors/<int:pk>/", views.AuthorDetailView.as_view(), name="author_detail"),
    path("tags/", views.TagListView.as_view(), name="tags"),
    path("tags/<int:pk>/", views.TagDetailView.as_view(), name="tag_detail"),
    path("contests/", views.ContestListView.as_view(), name="contests"),
    path("contests/<int:pk>/", views.ContestDetailView.as_view(), name="contest_detail"),
    path("<str:enum_type>/", views.EnumListView.as_view(), name="enum_list"),
    path("<str:enum_type>/<int:value>/", views.EnumDetailView.as_view(), name="enum_detail"),
]
