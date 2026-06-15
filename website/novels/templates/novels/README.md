# templates

Django templates for the novels app.

## Template Inheritance

```
website/templates/base.html              ← Project-level base
  └── novels/templates/novels/base.html  ← App-level base
        ├── index.html
        ├── rank.html
        ├── detail.html
        ├── banners.html
        ├── authors.html
        ├── author_detail.html
        ├── tags.html
        ├── tag_detail.html
        ├── contests.html
        ├── contest_detail.html
        ├── enum_list.html
        ├── enum_detail.html
        ├── about.html
        ├── dashboard.html
        ├── comments.html
        └── 404.html
```

### `website/templates/base.html` (Project Base)

Defines the HTML skeleton and loads global assets:

- `<head>` — charset, viewport, favicon, Tailwind CSS, htmx, dark mode script
- Blocks: `title`, `css`, `head_js`, `header`, `content`, `pagination`, `footer`, `body_js`

### `novels/templates/novels/base.html` (App Base)

Extends project base, fills blocks with app-specific components:

- `header` → `header_solid.html` (gradient header)
- `pagination` → `components/pagination.html`
- `footer` → `footer.html`
- `body_js` → `main.js` (theme toggle, search, menu)

All page templates extend this app base.

## Pages

| Template | View | Description |
|----------|------|-------------|
| `index.html` | NovelListView | Homepage — hero banner, filters, novel grid |
| `rank.html` | NovelRankView | Ranking table with sortable columns |
| `detail.html` | NovelDetailView | Novel detail with cover, stats, ranks |
| `banners.html` | BannerListView | Banner novels grid |
| `authors.html` | AuthorListView | Author ranking |
| `author_detail.html` | AuthorDetailView | Single author's novels |
| `tags.html` | TagListView | Tag list |
| `tag_detail.html` | TagDetailView | Single tag's novels |
| `contests.html` | ContestListView | Contest list |
| `contest_detail.html` | ContestDetailView | Single contest's novels |
| `enum_list.html` | EnumListView | Enum distribution (genre/status/ptype) |
| `enum_detail.html` | EnumDetailView | Novels in specific enum value |
| `about.html` | AboutView | About page |
| `dashboard.html` | DashboardView | Data dashboard with Plotly charts |
| `comments.html` | CommentsView | Comments page with task form |
| `404.html` | — | 404 error page |

## Components

| Component | Description |
|-----------|-------------|
| `header_solid.html` | Gradient header for non-index pages |
| `header_transparent.html` | Transparent header for index page (no dark mode) |
| `header_solid_static.html` | Solid header for static mode |
| `header_transparent_static.html` | Transparent header for static mode |
| `nav.html` | Navigation links |
| `nav_static.html` | Navigation for static mode |
| `header_actions.html` | Search, theme toggle, menu, GitHub |
| `header_actions_static.html` | Header actions for static mode |
| `footer.html` | Footer |
| `footer_static.html` | Footer for static mode |
| `novel_card.html` | Novel card for grid layout |
| `novel_row.html` | Novel row for table layout |
| `filters.html` | Genre/status/ptype filters |
| `badge.html` | Status badge component |
