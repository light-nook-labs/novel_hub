from .novel import NovelListView, NovelDetailView, NovelRankView
from .author import AuthorListView, AuthorDetailView
from .tag import TagListView, TagDetailView
from .contest import ContestListView, ContestDetailView
from .enum import EnumListView, EnumDetailView
from .banner import BannerListView
from .other import AboutView, DashboardView, CommentsView

__all__ = [
    "NovelListView",
    "NovelDetailView",
    "NovelRankView",
    "AuthorListView",
    "AuthorDetailView",
    "TagListView",
    "TagDetailView",
    "ContestListView",
    "ContestDetailView",
    "EnumListView",
    "EnumDetailView",
    "BannerListView",
    "AboutView",
    "DashboardView",
    "CommentsView",
]
