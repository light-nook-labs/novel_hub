from .mappings import GENRE, STATUS, PTYPE


def mappings_context(request):
    return {
        "GENRE": GENRE,
        "STATUS": STATUS,
        "PTYPE": PTYPE,
    }


def static_mode_context(request):
    return {
        "static_mode": getattr(request, "static_mode", False),
    }
