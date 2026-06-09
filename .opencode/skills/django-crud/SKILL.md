---
name: django-crud
description: Generate CRUD views, forms, templates, and tests for a Django model
---

## What I do
- Create ListView, DetailView, CreateView, UpdateView, DeleteView
- Generate ModelForm with appropriate widgets
- Create templates (list, detail, form, confirm_delete)
- Add URL patterns
- Write tests for all views
- Add pagination support

## Conventions
- Class-based views with Django generic views
- Forms use Tailwind CSS classes
- Use `CheckboxSelectMultiple` for M2M fields
- Templates extend app's `base.html`
- Tests cover: GET list, GET detail, GET create, POST create, GET update, POST update, POST delete
- Single admin user only — no authentication, no `LoginRequiredMixin`, no `UserPassesTestMixin`

## Layout rules
- **Grid-first**: ListView content uses CSS Grid (`grid-cols-4 md:grid-cols-6 lg:grid-cols-8`).
- Table views (rank, comparison) use `<table>`.
- Flexbox only for 1D alignment (nav, pills, badges).

## Pagination
- `per_page` must be a multiple of 6 (LCM of 4, 6, 8). Default: 24.
- Exceptions: banner (12), rank (100), detail sublists (50).
- No pagination for tag/contest list pages — render all as pills.
- Read `per_page` from `site_config.toml` via context processor.

## Test pattern
```python
class ModelViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create test data

    def test_list_view(self):
        response = self.client.get(reverse('app:list'))
        self.assertEqual(response.status_code, 200)

    def test_create_view(self):
        response = self.client.post(reverse('app:create'), data={...})
        self.assertEqual(response.status_code, 302)
```
