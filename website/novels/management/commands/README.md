# Management Commands

Django management commands for data processing, task management, snapshots, and static site generation.

## Tech Stack

- **utils/** — loader, Meta model, fetch_html, fetch_api, logger

## Quick Start

```bash
# Init DB (deletes all data)
uv run python manage.py init_db ../release/dataset/

# Upsert (updates existing)
uv run python manage.py upsert_dataset ../release/dataset/

# Process tasks
uv run python manage.py run_tasks
```

## Commands

### Data

| Command | Description |
|---------|-------------|
| `init_db <path>` | Init DB from JSONL/CSV (deletes all data first) |
| `init_from_release <archive>` | Init DB from release tar archive |
| `upsert_dataset <path>` | Upsert dataset (updates existing records) |
| `dump_dataset <path>` | Dump DB to JSONL/CSV |
| `create_release` | Create release tar archive |
| `fix_m2m <path>` | Fix missing M2M tag relationships |
| `fix_ptype <path>` | Fix ptype (upgrade only) |

### Tasks

| Command | Description |
|---------|-------------|
| `fill_tasks` | Create tasks for duplicate covers |
| `run_tasks` | Process tasks (crawl + update) |
| `add_long_term <nid>` | Add novel as long-term task |
| `remove_long_term <nid>` | Remove long-term task |
| `process_task_issues` | Process task issues from GitHub |

### Snapshots

| Command | Description |
|---------|-------------|
| `smart_snapshot` | Create daily snapshots |
| `archive_snapshots` | Archive snapshots to JSONL/CSV |

### Static Site

| Command | Description |
|---------|-------------|
| `generate_static` | Generate static site for GitHub Pages |
| `serve_static` | Serve static site for local preview |

## Docs

See [docs/commands.md](../../../docs/commands.md) for detailed usage and options.
