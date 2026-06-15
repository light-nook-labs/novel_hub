# website — Detailed Documentation

Detailed documentation for the Django web application.

> **Quick overview**: See [website/README.md](../website/README.md)

## Configuration

### Environment Variables (.env)

```bash
SECRET_KEY=your-secret-key
DEBUG=true
DB_TYPE=sqlite          # or postgresql
DB_NAME=postgres        # PostgreSQL only
DB_USER=postgres
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=5432
```

### site_config.toml

```toml
[site]
name = "Novel Hub"
timezone = "Asia/Shanghai"

[pagination]
per_page = 24
rank_per_page = 100
banner_per_page = 12

[thresholds]
died_days = 90
active_click = 10000000
active_review = 60
active_like = 10000
active_praise = 10000
snapshot_days = 7
retention_days = 30
```

## Models

### Novel

| Field | Type | Description |
|-------|------|-------------|
| `id` | BigIntegerField | Primary key (sfacg nid) |
| `title` | CharField | Novel title |
| `author` | FK(Author) | Author |
| `contest` | FK(Contest) | Contest (nullable) |
| `tags` | M2M(Tag) | Tags |
| `genre` | SmallIntegerField | Genre enum |
| `status` | SmallIntegerField | Status enum |
| `ptype` | SmallIntegerField | Ptype enum |
| `has_banner` | BooleanField | Has banner |
| `word_num` | IntegerField | Word count |
| `click_num` | IntegerField | Click count |
| `praise_num` | IntegerField | Praise count |
| `like_num` | IntegerField | Like count |
| `review_num` | IntegerField | Review count |
| `comment_num` | IntegerField | Comment count |
| `cover` | CharField | Cover URL suffix |
| `last_update` | DateTimeField | Last update |
| `db_update` | DateTimeField | Auto-updated |

### Task

| Field | Type | Description |
|-------|------|-------------|
| `novel` | OneToOneField(Novel) | Linked novel |
| `status` | CharField | l=long_term, u=urgent, d=default, f=finished |

### NovelSnapshot

| Field | Type | Description |
|-------|------|-------------|
| `novel` | FK(Novel) | Linked novel |
| `snapshot_date` | DateField | Snapshot date |
| `click_num` | IntegerField | Click count |
| `like_num` | IntegerField | Like count |
| `praise_num` | IntegerField | Praise count |
| `word_num` | IntegerField | Word count |
| `review_num` | IntegerField | Review count |
| `comment_num` | IntegerField | Comment count |

## Views

### Novel Views

| View | URL | Description |
|------|-----|-------------|
| `NovelListView` | `/` | Homepage with search/filters |
| `NovelDetailView` | `/novel/<pk>/` | Novel detail with ranks |
| `NovelRankView` | `/rank/` | Sortable table view |
| `BannerListView` | `/banners/` | Banner novels |

### Entity Views

| View | URL | Description |
|------|-----|-------------|
| `AuthorListView` | `/authors/` | Author list with stats |
| `AuthorDetailView` | `/authors/<pk>/` | Author's novels |
| `TagListView` | `/tags/` | Tag list |
| `TagDetailView` | `/tags/<pk>/` | Tag's novels |
| `ContestListView` | `/contests/` | Contest list |
| `ContestDetailView` | `/contests/<pk>/` | Contest's novels |

### Enum Views

| View | URL | Description |
|------|-----|-------------|
| `EnumListView` | `/genres/` | Genre list with counts |
| `EnumDetailView` | `/genres/<value>/` | Novels by genre |
| `EnumListView` | `/statuses/` | Status list |
| `EnumDetailView` | `/statuses/<value>/` | Novels by status |
| `EnumListView` | `/ptypes/` | Ptype list |
| `EnumDetailView` | `/ptypes/<value>/` | Novels by ptype |

## Template Tags

| Tag/Filter | Usage | Description |
|------------|-------|-------------|
| `cover_url` | `{{ novel.cover\|cover_url }}` | Full cover URL |
| `humanize_num` | `{{ value\|humanize_num }}` | Format as X.Xw+ |
| `truncate_cjk` | `{{ text\|truncate_cjk:26 }}` | Truncate by width |
| `pill_bg` | `{{ obj\|pill_bg:"tag" }}` | HSL background |
| `pill_text` | `{{ obj\|pill_text:"tag" }}` | HSL text color |
| `get_attr` | `{{ obj\|get_attr:"author__name" }}` | Dynamic lookup |
| `detail_url` | `{{ obj\|detail_url:"novels:tag_detail" }}` | Detail URL |
| `banner_url` | `{% banner_url novel.id %}` | Banner image URL |
| `novel_url` | `{% novel_url novel.id %}` | Novel page URL |

## Management Commands

### init_db

Init DB from dataset. **Deletes ALL existing data first.**

```bash
uv run python manage.py init_db ../release/dataset/
uv run python manage.py init_db ../release/dataset/meta_01.jsonl
```

### upsert_dataset

Upsert — updates existing, inserts new.

```bash
uv run python manage.py upsert_dataset ../release/dataset/
```

### dump_dataset

Dump DB to JSONL/CSV.

```bash
uv run python manage.py dump_dataset release
uv run python manage.py dump_dataset release --format csv
```

### fill_tasks

Create tasks for duplicate covers.

```bash
uv run python manage.py fill_tasks
uv run python manage.py fill_tasks --dry-run
```

### run_tasks

Process tasks: crawl, update DB, mark finished.

```bash
uv run python manage.py run_tasks
uv run python manage.py run_tasks --limit 100
```

### smart_snapshot

Create daily snapshots.

```bash
uv run python manage.py smart_snapshot
```

### archive_snapshots

Archive to JSONL/CSV, delete from DB.

```bash
uv run python manage.py archive_snapshots
uv run python manage.py archive_snapshots --month 2026-01
```

### generate_static

Generate static site for GitHub Pages.

```bash
uv run python manage.py generate_static --output ../build --base-path novel_hub
```

## Data Rules

- **Died**: `连载中` + 3 months no update → `断更`
- **A-status**: `断更`/`已完结` + (banner OR click≥1000w OR review≥60 OR like≥1w OR praise≥1w) → `断更A`/`完结A`
- **Missing values**: `null`/`None` — never `0`
- **Ptype**: Only upgrade (免费→签约→VIP), never downgrade
