# tests

Unit and E2E tests for the novels app.

## Test Files

| File | Tests | What it tests |
|------|-------|---------------|
| `test_models.py` | Model and mapping tests | Model __str__, get_*_display(), FK/M2M relationships, novel_count annotation, Mapping get_zh/get_value/choices |
| `test_views.py` | View tests | All views return 200, correct templates, 404 for invalid IDs, query count optimization |
| `test_tags.py` | Template tag tests | truncate_cjk (CJK width), cover_url (suffix/None/HTTP upgrade), humanize_num, pill_bg, detail_url, get_attr |
| `test_search.py` | Search boundary tests | Empty query, whitespace, special chars, SQL injection, found/not found, invalid filter values |
| `test_pagination.py` | Pagination tests | First/second/last page, beyond last (404), zero/negative/non-number (404) |
| `test_commands.py` | Management command tests | --help flag for init_db, upsert_dataset, dump_dataset, generate_static, serve_static |
| `e2e/test_comments_task_form.py` | E2E task form tests | Page loads, form elements, valid ID opens GitHub issue, boundary IDs, GISCUS container, URL format, multiple submissions |
| `e2e/test_process_task_issues.py` | Process task issues tests | No issues, valid issue, non-existent novel, duplicate task, NID extraction, invalid title, missing env vars, multiple issues |

## Run Tests

```bash
uv run python manage.py test novels -v 2
```
