import hashlib
import unicodedata

from django import template
from django.conf import settings

register = template.Library()


def _display_width(text):
    """Calculate display width: CJK chars = 2, others = 1."""
    w = 0
    for ch in text:
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            w += 2
        else:
            w += 1
    return w


@register.filter
def truncate_cjk(text, max_width=26):
    """Truncate text by display width (CJK=2, ASCII=1). Adds '…' if truncated."""
    if text is None:
        return ""
    max_width = int(max_width)
    if _display_width(text) <= max_width:
        return text
    w = 0
    for i, ch in enumerate(text):
        cw = 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        if w + cw > max_width - 1:
            return text[:i] + "…"
        w += cw
    return text


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

    if not suffix or suffix in ("nan", "<NA>", "None"):
        url = prefix + default
    elif suffix.startswith(prefix):
        url = suffix
    elif suffix.startswith("http"):
        url = suffix
    else:
        url = prefix + suffix

    # Upgrade HTTP to HTTPS to avoid mixed content
    if url.startswith("http://"):
        url = "https://" + url[7:]

    return url


@register.filter
def humanize_num(value):
    """Format number: >=10000 as X.Xw+, else original."""
    try:
        if value is None:
            return "-"
        n = int(value)
        if n >= 10000:
            w = n / 10000
            return f"{round(w, 1)}w+"
        return str(n)
    except (ValueError, TypeError):
        return "-"


def _pill_hue(key):
    """Deterministic hue (0-359) from string key."""
    return int(hashlib.md5(key.encode()).hexdigest(), 16) % 360


@register.filter
def pill_bg(obj, model_name):
    """Generate deterministic background color from object ID + model name."""
    if obj is None:
        return ""
    h = _pill_hue(f"{model_name}_{obj.id}")
    return f"hsl({h}, 70%, 92%)"


@register.filter
def pill_bg_dark(obj, model_name):
    """Generate deterministic dark-mode background color."""
    if obj is None:
        return ""
    h = _pill_hue(f"{model_name}_{obj.id}")
    return f"hsl({h}, 60%, 20%)"


@register.filter
def pill_text(obj, model_name):
    """Generate deterministic text color from object ID + model name."""
    if obj is None:
        return ""
    h = _pill_hue(f"{model_name}_{obj.id}")
    return f"hsl({h}, 70%, 35%)"


@register.filter
def pill_text_dark(obj, model_name):
    """Generate deterministic dark-mode text color."""
    if obj is None:
        return ""
    h = _pill_hue(f"{model_name}_{obj.id}")
    return f"hsl({h}, 70%, 70%)"


@register.filter
def detail_url(obj, url_name):
    """Generate detail URL: obj|detail_url:'novels:tag_detail'."""
    from django.urls import NoReverseMatch, reverse

    try:
        return reverse(url_name, args=[obj.id])
    except (NoReverseMatch, AttributeError):
        return ""


@register.simple_tag
def banner_url(nid):
    """Generate banner image URL from nid."""
    cfg = settings.TOML
    pattern = cfg.get("urls", {}).get(
        "banner", "https://rs.sfacg.com/web/novel/images/images/beitouNew/{nid}.jpg"
    )
    return pattern.format(nid=nid)


@register.simple_tag
def novel_url(nid):
    """Generate novel page URL from nid."""
    cfg = settings.TOML
    pattern = cfg.get("urls", {}).get("novel", "https://book.sfacg.com/Novel/{nid}/")
    return pattern.format(nid=nid)


@register.simple_tag(takes_context=True)
def static_url(context, path):
    """Generate static file URL with base_path prefix in static mode."""
    base_path = context.get("base_path", "")
    if base_path:
        return f"/{base_path}/{path}"
    return f"/{path}"


@register.simple_tag(takes_context=True)
def page_url(context, path):
    """Generate page URL with base_path prefix in static mode."""
    base_path = context.get("base_path", "")
    if base_path:
        return f"/{base_path}/{path}"
    return f"/{path}"
