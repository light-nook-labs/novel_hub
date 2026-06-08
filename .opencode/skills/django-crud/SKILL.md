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
- Add pagination support (use LoadMoreMixin for AJAX or traditional)

## Conventions
- Class-based views with Django generic views
- Forms use Tailwind CSS classes (see `templates/form_styles.txt`)
- Use `CheckboxSelectMultiple` for M2M fields
- Templates extend app's `base.html`
- Tests cover: GET list, GET detail, GET create, POST create, GET update, POST update, POST delete
- Staff-only views use `LoginRequiredMixin` and `UserPassesTestMixin`

## Pagination
- Check `site_config.toml` for pagination style
- `"traditional"` — use `paginate_by = 10` and pagination template
- `"load_more"` — use `LoadMoreMixin` from `config/mixins.py`

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
