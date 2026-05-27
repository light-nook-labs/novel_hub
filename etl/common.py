from database import COVER_BASE, DEFAULT_COVER


def compress_cover_url(url: str) -> str | None:
    """
    http://rs.sfacg.com/web/novel/images/NovelCover/Big/2026/05/c5a77c0d-a493-43f6-8ba6-e11a8b3494b3.jpg
    """
    if not isinstance(url, str):
        return None
    if url.startswith(COVER_BASE):
        s_url = url[len(COVER_BASE) :]
        if s_url == DEFAULT_COVER:
            return None
        return s_url
    return None


__all__ = ["compress_cover_url"]

if __name__ == "__main__":
    print(
        compress_cover_url(
            "http://rs.sfacg.com/web/novel/images/NovelCover/Big/2026/05/c5a77c0d-a493-43f6-8ba6-e11a8b3494b3.jpg"
        )
    )
    print(
        compress_cover_url(
            "http://rs.sfacg.com/web/novel/images/NovelCover/Big/defaultNew.jpg"
        )
    )
