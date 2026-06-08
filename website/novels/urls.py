from django.urls import path
from . import views

app_name = "novels"

urlpatterns = [
    path("", views.NovelListView.as_view(), name="index"),
    path("rank/", views.NovelRankView.as_view(), name="rank"),
    path("novel/<int:pk>/", views.NovelDetailView.as_view(), name="detail"),
]
