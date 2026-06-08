from .mappings import GENRE, STATUS, PTYPE


def mappings_context(request):
    return {
        "GENRE": GENRE,
        "STATUS": STATUS,
        "PTYPE": PTYPE,
    }
