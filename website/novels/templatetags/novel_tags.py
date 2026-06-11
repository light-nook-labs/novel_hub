from django import template
from django.conf import settings

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
    """Reconstruct full cover URL from suffix using TOML config."""
    cfg = settings.TOML
    prefix = cfg.get("scraper", {}).get("cover_prefix", "")
    default = cfg.get("scraper", {}).get("default_cover", "defaultNew.jpg")

    if not suffix or suffix == "nan":
        return prefix + default
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


@register.filter
def detail_url(obj, url_name):
    """Generate detail URL: obj|detail_url:'novels:tag_detail'."""
    from django.urls import reverse

    try:
        return reverse(url_name, args=[obj.id])
    except Exception:
        return ""


@register.simple_tag
def banner_url(nid):
    """Generate banner image URL from nid."""
    return f"https://rs.sfacg.com/web/novel/images/images/beitouNew/{nid}.jpg"


@register.simple_tag
def novel_url(nid):
    """Generate novel page URL from nid."""
    cfg = settings.TOML
    pattern = cfg.get("scraper", {}).get("novel_url", "https://book.sfacg.com/Novel/{nid}/")
    return pattern.format(nid=nid)
