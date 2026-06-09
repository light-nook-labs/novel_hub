---
name: htmx-django
description: Integrate HTMX with Django for dynamic interactions without full page reloads
---

## What I do
- Add HTMX attributes to Django templates
- Create partial template responses
- Implement dynamic filtering, sorting, pagination
- Form submissions with HTMX

## HTMX attributes
- `hx-get="/url"` - GET request
- `hx-post="/url"` - POST request
- `hx-target="#id"` - Where to put the response
- `hx-select="#id"` - Select part of response
- `hx-swap="innerHTML"` - How to insert (innerHTML, outerHTML, beforeend, etc.)
- `hx-push-url="true"` - Update browser URL
- `hx-boost="true"` - Boost all links/forms in container
- `hx-trigger="click"` - When to trigger (click, submit, load, delay:500ms)
- `hx-indicator="#spinner"` - Loading indicator

## Django view for HTMX
```python
from django.http import HttpResponse
from django.template.loader import render_to_string

def my_view(request):
    # Check if HTMX request
    is_htmx = request.headers.get("HX-Request") == "true"
    
    if is_htmx:
        # Return partial HTML
        html = render_to_string("partials/content.html", context, request)
        return HttpResponse(html)
    
    # Return full page
    return render(request, "full_page.html", context)
```

## Boost pattern for AJAX navigation
```html
{# In base template - boosts all links/forms in container #}
<div id="content" hx-boost="true" hx-select="#content" hx-target="#content">
  {% block content %}{% endblock %}
</div>

{# Pagination links now use AJAX automatically #}
<a href="?page=2">Next</a>
```

## Dynamic filtering
```html
{# Filter links with hx-get #}
<div hx-boost="true" hx-target="#content" hx-select="#content" hx-push-url="true">
  <a href="?genre=1">Fantasy</a>
  <a href="?genre=2">Sci-Fi</a>
</div>

{# Or with explicit hx-get on each link #}
<a hx-get="?genre=1" hx-target="#content" hx-select="#content" hx-push-url="true">
  Fantasy
</a>
```

## Form submission
```html
<form hx-get="{% url 'app:search' %}" hx-target="#results" hx-push-url="true">
  <input type="text" name="q" placeholder="Search...">
  <button type="submit">Search</button>
</form>
<div id="results">
  {% include "partials/results.html" %}
</div>
```

## Table sorting
```html
<th hx-get="?sort=name&dir={% if current_sort == 'name' and current_dir == 'desc' %}asc{% else %}desc{% endif %}"
    hx-target="#content" hx-select="#content" hx-push-url="true"
    class="cursor-pointer">
  Name
</th>
```

## Loading indicator
```html
<button hx-get="/data" hx-indicator="#spinner">
  Load Data
</button>
<div id="spinner" class="htmx-indicator">Loading...</div>

<style>
.htmx-indicator { display: none; }
.htmx-request .htmx-indicator { display: inline; }
.htmx-request.htmx-indicator { display: inline; }
</style>
```

## Django template for partial response
```html
{# partials/novel_grid.html - returned by HTMX #}
<div id="content">
  <div class="grid grid-cols-4 gap-4">
    {% for novel in novels %}
    <div class="card">{{ novel.title }}</div>
    {% endfor %}
  </div>
  {% include "components/pagination.html" %}
</div>
```

## Best practices
- Use `hx-boost="true"` for simple link/form navigation
- Use explicit `hx-get/post` for specific interactions
- Always set `hx-target` and `hx-select` for partial updates
- Use `hx-push-url="true"` to update browser URL
- Return partial HTML from Django view for HTMX requests
- Keep partial templates self-contained
