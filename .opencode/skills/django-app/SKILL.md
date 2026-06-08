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
- Each app has own header/footer/navigation (independent)
- No Chinese in code — English only
- URL namespace matches app name
- Use `uv run python manage.py` for all Django commands

## Template structure
```
app/
├── templates/
│   └── app/
│       ├── base.html
│       ├── index.html
│       └── components/
│           ├── header.html
│           └── footer.html
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
- Run `uv run python manage.py test`
