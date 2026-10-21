from collections.abc import Callable

from opentelemetry import metrics, trace


def tag_surface(name: str) -> Callable[[], None]:
    """Dependency factory: label the current span and count the request by API surface."""

    def _tag() -> None:
        trace.get_current_span().set_attribute("api.surface", name)
        # Resolved per call so the global provider, set at startup, is always the one used.
        metrics.get_meter("app").create_counter("app.surface.requests").add(
            1, {"api.surface": name}
        )

    return _tag
