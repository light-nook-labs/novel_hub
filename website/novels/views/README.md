# views

## Routes

| URL | Name | Description |
|-----|------|-------------|
| `/` | `index` | Homepage — novel grid with search, filters, sorting |
| `/rank/` | `rank` | Full ranking table with sortable columns |
| `/banners/` | `banners` | Banner novels showcase |
| `/novel/<pk>/` | `detail` | Novel detail with metrics and rank stats |
| `/authors/` | `authors` | Author ranking by aggregated stats |
| `/authors/<pk>/` | `author_detail` | Single author's novels |
| `/tags/` | `tags` | Tag list with novel counts |
| `/tags/<pk>/` | `tag_detail` | Single tag's novels |
| `/contests/` | `contests` | Contest list with novel counts |
| `/contests/<pk>/` | `contest_detail` | Single contest's novels |
| `/genres/` | `genres` | Genre distribution with counts |
| `/genres/<value>/` | `genre_detail` | Novels in specific genre |
| `/statuses/` | `statuses` | Status distribution with counts |
| `/statuses/<value>/` | `status_detail` | Novels with specific status |
| `/ptypes/` | `ptypes` | Ptype distribution with counts |
| `/ptypes/<value>/` | `ptype_detail` | Novels with specific ptype |
| `/about/` | `about` | About page |
| `/dashboard/` | `dashboard` | Data dashboard with Plotly charts |
| `/comments/` | `comments` | Comments page |

## Parameters

### `/` (Homepage)

| Param | Description |
|-------|-------------|
| `q` | Search (title or author) |
| `genre` | Filter by genre |
| `status` | Filter by status |
| `ptype` | Filter by ptype |
| `sort` | Sort: click_num, word_num, like_num, praise_num, last_update, db_update |
| `page` | Page number |

### `/rank/` (Ranking)

| Param | Description |
|-------|-------------|
| `sort` | Sort column |
| `dir` | asc / desc |
| `page` | Page number |

### `/authors/` (Author Ranking)

| Param | Description |
|-------|-------------|
| `q` | Search by name |
| `sort` | Sort: total_click, novel_count, total_word, total_like, total_praise, total_review, total_comment, latest_update |
| `dir` | asc / desc |
| `page` | Page number |

### `/authors/<pk>/`, `/tags/<pk>/`, `/contests/<pk>/` (Detail Pages)

| Param | Description |
|-------|-------------|
| `genre` | Filter by genre |
| `status` | Filter by status |
| `ptype` | Filter by ptype |
| `sort` | Sort: click_num, word_num, like_num, praise_num, last_update |
| `page` | Page number |

### `/genres/<value>/`, `/statuses/<value>/`, `/ptypes/<value>/` (Enum Detail)

| Param | Description |
|-------|-------------|
| `genre` | Filter by genre |
| `status` | Filter by status |
| `ptype` | Filter by ptype |
| `sort` | Sort: click_num, word_num, like_num, praise_num, last_update |
| `page` | Page number |
