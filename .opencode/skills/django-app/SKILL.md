---
name: django-app
description: Create a new Django app with models, views, URLs, templates, and tests following project conventions
---

## What I do
- Create Django app with `startapp`
- Set up models, views, urls, forms, tests
- Create template directory structure
- Register in admin
- Add URL to config/urls.py
- Create migrations and migrate

## Project conventions
- App templates: `app/templates/app/base.html` extends `templates/base.html`
- Static files: `app/static/app/{js,css,images}/`
- Shared header/footer via `novels/base.html` — do not duplicate per app
- No Chinese in code — English only
- URL namespace matches app name
- Use `uv run python manage.py` for all Django commands

## Layout rules
- **Grid-first**: ListView content uses CSS Grid (`grid-cols-4 md:grid-cols-6 lg:grid-cols-8`).
- Pagination `per_page` must be a multiple of 6. Default: 24.
- Always include `dark:` variants for backgrounds, text, borders.

## Template structure
```
app/
├── templates/
│   └── app/
│       ├── base.html
│       ├── index.html
│       └── components/
├── static/
│   └── app/
│       ├── js/
│       ├── css/
│       └── images/
├── models.py
├── views.py
├── urls.py
├── forms.py
├── admin.py
└── tests.py
```

## After creation
- Run `uv run python manage.py makemigrations`
- Run `uv run python manage.py migrate`
- Run `uv run python manage.py test <app_name>`
