from django.views.generic import TemplateView

from ..models import Novel, Author, Tag, Contest
from ..mappings import GENRE, STATUS, PTYPE


class AboutView(TemplateView):
    template_name = "novels/about.html"


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

        # 3. Ptype distribution (donut)
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

        # 7. Word count distribution (frequency histogram, exclude <10w)
        word_data = list(
            Novel.objects.filter(word_num__gte=100000).values_list(
                "word_num", flat=True
            )[:100000]
        )
        # Bins: 10-15w, 15-20w, 20-30w, 30-50w, 50-100w, 100-200w, 200-500w, 500-1000w, 1000w+
        bins = [
            100000,
            150000,
            200000,
            300000,
            500000,
            1000000,
            2000000,
            5000000,
            10000000,
            float("inf"),
        ]
        bin_labels = [
            "10-15w",
            "15-20w",
            "20-30w",
            "30-50w",
            "50-100w",
            "100-200w",
            "200-500w",
            "500-1000w",
            "1000w+",
        ]
        bin_counts = [0] * len(bin_labels)
        for w in word_data:
            for i in range(len(bins) - 1):
                if bins[i] <= w < bins[i + 1]:
                    bin_counts[i] += 1
                    break

        fig = go.Figure(
            data=[
                go.Bar(
                    x=bin_labels,
                    y=bin_counts,
                    marker_color=amber,
                    text=bin_counts,
                    textposition="outside",
                )
            ]
        )
        fig.update_layout(
            **_layout(350),
            xaxis=dict(title="字数区间", gridcolor="rgba(128,128,128,0.2)"),
            yaxis=dict(
                title="小说数",
                gridcolor="rgba(128,128,128,0.2)",
                tickformat=",d",
            ),
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

        # 9. Genre x Status stacked bar
        genre_status_data = Novel.objects.values("genre", "status").annotate(
            c=Count("id")
        )
        genre_range = list(range(2, 11))
        status_range = list(range(2, 8))
        status_colors = [amber, orange, rose, "#f472b6", "#fbbf24", "#94a3b8"]

        fig = go.Figure()
        for i, s in enumerate(status_range):
            vals = []
            for g in genre_range:
                val = next(
                    (
                        d["c"]
                        for d in genre_status_data
                        if d["genre"] == g and d["status"] == s
                    ),
                    0,
                )
                vals.append(val)
            fig.add_trace(
                go.Bar(
                    x=[GENRE.get_zh(g) for g in genre_range],
                    y=vals,
                    name=STATUS.get_zh(s),
                    marker_color=status_colors[i % len(status_colors)],
                )
            )
        fig.update_layout(
            **_layout(300),
            barmode="stack",
            xaxis=dict(gridcolor="rgba(128,128,128,0.2)"),
            yaxis=dict(title="小说数", gridcolor="rgba(128,128,128,0.2)"),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
        )
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

        # 12. Banner vs Non-Banner comparison (2 charts)
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
        bc = banner_stats["banner_count"] or 1
        nc = banner_stats["nonbanner_count"] or 1

        # Chart 1: Click comparison
        banner_click_per = (banner_stats["banner_click"] or 0) / bc
        nonbanner_click_per = (banner_stats["nonbanner_click"] or 0) / nc
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=["Banner", "非Banner"],
                y=[banner_click_per, nonbanner_click_per],
                marker_color=[amber, "#94a3b8"],
                text=[_w(int(v)) for v in [banner_click_per, nonbanner_click_per]],
                textposition="outside",
            )
        )
        fig.update_layout(
            **_layout(280),
            yaxis=dict(title="人均点击", gridcolor="rgba(128,128,128,0.2)"),
            showlegend=False,
        )
        ctx["chart_banner_click_json"] = _to_json(fig)

        # Chart 2: Engagement comparison (like + praise)
        banner_like_per = (banner_stats["banner_like"] or 0) / bc
        nonbanner_like_per = (banner_stats["nonbanner_like"] or 0) / nc
        banner_praise_per = (banner_stats["banner_praise"] or 0) / bc
        nonbanner_praise_per = (banner_stats["nonbanner_praise"] or 0) / nc
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=["收藏", "点赞"],
                y=[banner_like_per, banner_praise_per],
                name=f"Banner ({bc}部)",
                marker_color=amber,
            )
        )
        fig.add_trace(
            go.Bar(
                x=["收藏", "点赞"],
                y=[nonbanner_like_per, nonbanner_praise_per],
                name=f"非Banner ({nc}部)",
                marker_color="#94a3b8",
            )
        )
        fig.update_layout(
            **_layout(280),
            barmode="group",
            yaxis=dict(title="人均", gridcolor="rgba(128,128,128,0.2)"),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
        )
        ctx["chart_banner_engagement_json"] = _to_json(fig)

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


class CommentsView(TemplateView):
    template_name = "novels/comments.html"
