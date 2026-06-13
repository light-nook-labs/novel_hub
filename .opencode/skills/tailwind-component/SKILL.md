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
- **Pagination**: `per_page` must be a multiple of 6 (LCM of 4, 6, 8). Default: 24. Exceptions: banner (12), rank (100), detail sublists (50).
- **No pagination** for tag and contest list pages — render all items as pills.

## Color scheme

**No cold colors (blue, indigo, sky, cyan, violet, purple, fuchsia). No pure colors — use muted warm tones only.**

### Primary Palette
| Role | Light | Dark | Tailwind |
|------|-------|------|----------|
| Header gradient | Amber-200 → Orange-200 | Amber-900 → Orange-900 | `from-amber-200 to-orange-200 dark:from-amber-900 dark:to-orange-900` |
| Accent / hover | Amber-700 | Amber-300 | `hover:text-amber-700 dark:hover:text-amber-300` |
| Active filter | Gray-200 | Gray-700 | `bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200` |

### Surface & Background
| Role | Light | Dark | Tailwind |
|------|-------|------|----------|
| Page bg | Gray-50 | Gray-900 | `bg-gray-50 dark:bg-gray-900` |
| Card / surface | White | Gray-800 | `bg-white dark:bg-gray-800` |
| Border | Gray-200 | Gray-700 | `border-gray-200 dark:border-gray-700` |

### Text
| Role | Light | Dark | Tailwind |
|------|-------|------|----------|
| Primary | Gray-800 | Gray-100 | `text-gray-800 dark:text-gray-100` |
| Secondary | Gray-600 | Gray-400 | `text-gray-600 dark:text-gray-400` |
| Muted | Gray-400 | Gray-500 | `text-gray-400 dark:text-gray-500` |

### Status Badges
| Status | Light | Dark | Tailwind |
|--------|-------|------|----------|
| Finished (已完结) | Green-100/700 | Green-900/300 | `bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300` |
| Ongoing (连载中) | Red-100/700 | Red-900/300 | `bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300` |
| Died (断更) | Gray-100/700 | Gray-700/300 | `bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300` |
| Active Died (断更A) | Amber-100/700 | Amber-900/300 | `bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300` |
| Active Finished (完结A) | Teal-100/700 | Teal-900/300 | `bg-teal-100 text-teal-700 dark:bg-teal-900 dark:text-teal-300` |
| Removed (下架) | Gray-100/700 | Gray-700/300 | same as died |

### Category Badges
| Category | Light | Dark | Tailwind |
|----------|-------|------|----------|
| Genre | Orange-100/700 | Orange-900/300 | `bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300` |
| Type (ptype) | Rose-100/700 | Rose-900/300 | `bg-rose-100 text-rose-700 dark:bg-rose-900 dark:text-rose-300` |
| Contest | Orange-100/700 | Orange-900/300 | `bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300` |
| Tag / Contest pills | Deterministic HSL from `hash("{model}_{id}")` | same with dark overrides | Inline CSS custom properties |

### Interactive
| Element | Light | Dark | Tailwind |
|---------|-------|------|----------|
| Link hover | Amber-600 | Amber-400 | `hover:text-amber-600 dark:hover:text-amber-400` |
| Card hover shadow | shadow-md | shadow-md | `hover:shadow-md` |
| Button primary | Amber-600 | Amber-500 | `bg-amber-600 dark:bg-amber-500` |

### Badge component pattern
Use a reusable badge class to avoid repetitive Tailwind:
```html
<span class="badge" style="--bg:{{ obj|badge_bg:'model' }}; --tc:{{ obj|badge_text:'model' }}; --bgd:{{ obj|badge_bg_dark:'model' }}; --tcd:{{ obj|badge_text_dark:'model' }}">
  {{ label }}
</span>
```
```css
.badge { background: var(--bg); color: var(--tc); }
.dark .badge { background: var(--bgd); color: var(--tcd); }
```

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
