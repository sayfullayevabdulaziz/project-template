from collections.abc import Callable


def tag_surface(name: str) -> Callable[[], None]:
    """Stub dependency factory; Task 15 replaces it with the real surface tagging."""

    def _tag() -> None:
        return None

    return _tag
