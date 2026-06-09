---
name: tailwind-component
description: Create Tailwind CSS components following project design system
---

## What I do
- Create reusable HTML components with Tailwind utilities
- Support dark mode with `dark:` variants
- Follow project color scheme (see below)
- Use CSS Grid for layouts, flex only for 1D alignment

## Layout rules
- **Grid-first**: ListView content uses `grid`. Table views use `<table>`. Flex only for nav, pills, badges.
- **Grid columns**: `grid-cols-4 md:grid-cols-6 lg:grid-cols-8`
- **Pagination**: `per_page` must be a multiple of 6 (LCM of 4, 6, 8). Default: 24.
- **No pagination** for tag and contest list pages — render all items as pills.

## Color scheme

**No cold colors (blue, indigo, sky, cyan, violet, purple, fuchsia). No pure colors — use muted warm tones only.**

### Primary
- Header gradient: `from-amber-200 to-orange-200`
- Accent / hover: `text-amber-400`
- Active filter: `bg-white/20 text-white`

### Surface & Background
- Page bg: `bg-gray-50 dark:bg-gray-900`
- Card / surface: `bg-white dark:bg-gray-800`
- Border: `border-gray-200 dark:border-gray-700`

### Text
- Primary: `text-gray-900 dark:text-gray-100`
- Secondary: `text-gray-500 dark:text-gray-400`
- Muted: `text-gray-400 dark:text-gray-500`

### Status badges
- Finished: `bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300`
- Ongoing: `bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300`
- Died: `bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300`

### Category badges
- Genre: `bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300`
- Type (ptype): `bg-rose-100 text-rose-700 dark:bg-rose-900 dark:text-rose-300`
- Contest: `bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300`
- Tag / Contest pills: deterministic HSL from `hash("{model}_{id}")`, inline CSS custom properties

### Interactive
- Link hover: `hover:text-amber-600 dark:hover:text-amber-400`
- Card hover: `hover:shadow-md`
- Button primary: `bg-amber-600 dark:bg-amber-500`

## Dark mode
Always include `dark:` variants for backgrounds, text, borders, and badges.
For inline styles that need dark mode, use CSS custom properties:
```html
<a class="pill" style="--pb: hsl(120,70%,92%); --pbd: hsl(120,60,20%)">
<style>
.pill { background: var(--pb); }
.dark .pill { background: var(--pbd); }
</style>
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
