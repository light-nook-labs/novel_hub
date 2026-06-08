---
name: tailwind-component
description: Create Tailwind CSS components following project design system
---

## What I do
- Create reusable HTML components with Tailwind utilities
- Support dark mode with `dark:` variants
- Follow project color scheme (green-800 header, amber-500 accents)
- Use consistent spacing and typography

## Project design tokens
- Header: `bg-green-800 text-white`
- Avatar/accent: `bg-amber-500`
- Primary buttons: `btn-primary` (defined in input.css)
- Secondary buttons: `btn-secondary`
- Cards: `bg-white dark:bg-gray-800 rounded-lg shadow-md p-6`
- Forms: use classes from `templates/form_styles.txt`

## Dark mode
Always include `dark:` variants:
```html
<div class="bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100">
```

## Component structure
Place in `app/templates/app/components/`:
```html
{# component_name.html #}
<div class="...">
  {% block content %}{% endblock %}
</div>
```

## After changes
Run `pnpm build` to compile Tailwind CSS.

## Form styles
Use `form.css` for form elements:
- Text inputs: `input-field`
- Select: `select-field`
- Labels: `label-text`
- Errors: `error-text`
