---
name: django-testing
description: Write Django tests and optimize performance
---

## What I do
- Write unit tests for views, models, forms, commands
- Detect and fix N+1 query problems
- Optimize database queries
- Implement caching strategies

## Test file location
Place in `app/tests.py` or `app/tests/` directory.

## View test pattern
```python
from django.test import TestCase
from django.urls import reverse

class MyViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.obj = MyModel.objects.create(name="Test")

    def test_list_view_status(self):
        response = self.client.get(reverse("app:list"))
        self.assertEqual(response.status_code, 200)

    def test_detail_view_404(self):
        response = self.client.get(reverse("app:detail", args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_search_filter(self):
        response = self.client.get(reverse("app:list"), {"q": "test"})
        self.assertContains(response, "Test")
```

## Model test pattern
```python
class MyModelTests(TestCase):
    def test_str_representation(self):
        obj = MyModel(name="Test")
        self.assertEqual(str(obj), "Test")

    def test_unique_constraint(self):
        MyModel.objects.create(name="Test")
        with self.assertRaises(Exception):
            MyModel.objects.create(name="Test")
```

## Command test pattern
```python
from django.core.management import call_command
from io import StringIO

class MyCommandTests(TestCase):
    def test_command_output(self):
        out = StringIO()
        call_command("my_command", stdout=out)
        self.assertIn("Done", out.getvalue())
```

## Running tests
```bash
uv run python manage.py test <app_name>        # Always specify app
uv run python manage.py test <app_name> -v 2   # With verbosity
uv run python manage.py test app.MyTests       # Specific class
uv run python manage.py test app.MyTests.test  # Specific method
```

## N+1 problem detection
```python
# BAD: N+1 queries
novels = Novel.objects.all()
for novel in novels:
    print(novel.author.name)  # Each triggers a query

# GOOD: select_related for FK/O2O
novels = Novel.objects.select_related("author", "contest").all()

# GOOD: prefetch_related for M2M/reverse FK
novels = Novel.objects.prefetch_related("tags").all()

# Combine both
novels = Novel.objects.select_related("author").prefetch_related("tags")
```

## Query optimization
```python
# Use values() when you only need specific fields
names = Novel.objects.values_list("title", flat=True)

# Use exists() instead of count() for boolean checks
if Novel.objects.filter(status=2).exists():
    ...

# Use only()/defer() for large fields
novels = Novel.objects.only("id", "title")
novels = Novel.objects.defer("cover", "description")

# Use annotate() for computed values
from django.db.models import Count
authors = Author.objects.annotate(novel_count=Count("novels"))
```

## Bulk operations
```python
# Bulk create
Novel.objects.bulk_create([Novel(...) for _ in range(1000)], batch_size=500)

# Bulk update
Novel.objects.filter(status=1).update(status=4)

# Bulk delete
Novel.objects.filter(last_update__year=2020).delete()
```

## Database indexes
```python
class Novel(models.Model):
    genre = models.SmallIntegerField(db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=["genre", "status"]),
            models.Index(fields=["-last_update"]),
        ]
```

## Caching
```python
from django.core.cache import cache

# Cache with timeout
result = cache.get("my_key")
if result is None:
    result = expensive_query()
    cache.set("my_key", result, timeout=300)

# Cache decorator
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)
def my_view(request):
    ...
```

## Best practices
- Use `setUpTestData` for data shared across tests (runs once)
- Use `setUp` for data that needs resetting per test
- Test both success and failure cases
- Always use `select_related` for FK you'll access
- Always use `prefetch_related` for M2M you'll access
- Add indexes for frequently filtered/sorted fields
- Use bulk operations for multiple creates/updates
