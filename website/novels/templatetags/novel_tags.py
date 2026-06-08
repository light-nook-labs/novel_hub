from django import template

register = template.Library()


@register.filter
def get_attr(obj, attr):
    """Get attribute from object by name. Supports __ lookups."""
    try:
        for part in attr.split("__"):
            obj = getattr(obj, part)
        if callable(obj):
            return obj()
        return obj
    except (AttributeError, TypeError):
        return ""


@register.filter
def humanize_num(value):
    """Format number: >=10000 as X.XXw+, else original."""
    try:
        if value is None:
            return "-"
        n = int(value)
        if n >= 10000:
            w = n / 10000
            return f"{w:.2f}w+"
        return str(n)
    except (ValueError, TypeError):
        return "-"
