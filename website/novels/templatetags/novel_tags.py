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
def cover_url(suffix):
    """Reconstruct full cover URL from suffix using site_config."""
    if not suffix:
        return ""
    from config.toml import _load_config

    cfg = _load_config()
    prefix = cfg.get("scraper", {}).get("cover_prefix", "")
    if suffix.startswith(prefix):
        return suffix
    if suffix.startswith("http"):
        return suffix
    return prefix + suffix


@register.filter
def humanize_num(value):
    """Format number: >=10000 as X.XXw+, else original."""
    try:
        if value is None:
            return "-"
        n = int(value)
        if n >= 10000:
            w = n / 10000
            return f"{int(w)}w+"
        return str(n)
    except (ValueError, TypeError):
        return "-"


@register.filter
def pill_bg(obj, model_name):
    """Generate deterministic background color from object ID + model name."""
    h = hash(f"{model_name}_{obj.id}") % 360
    return f"hsl({h}, 70%, 92%)"


@register.filter
def pill_bg_dark(obj, model_name):
    """Generate deterministic dark-mode background color."""
    h = hash(f"{model_name}_{obj.id}") % 360
    return f"hsl({h}, 60%, 20%)"


@register.filter
def pill_text(obj, model_name):
    """Generate deterministic text color from object ID + model name."""
    h = hash(f"{model_name}_{obj.id}") % 360
    return f"hsl({h}, 70%, 35%)"


@register.filter
def pill_text_dark(obj, model_name):
    """Generate deterministic dark-mode text color."""
    h = hash(f"{model_name}_{obj.id}") % 360
    return f"hsl({h}, 70%, 70%)"
