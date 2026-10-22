from collections.abc import Callable

from opentelemetry import metrics, trace


def tag_surface(name: str) -> Callable[[], None]:
    """Dependency factory: label the current span and count the request by API surface."""
    # Made once per surface: the pre-startup proxy provider keeps every instrument it hands out.
    counter = metrics.get_meter("app").create_counter("app.surface.requests")

    def _tag() -> None:
        trace.get_current_span().set_attribute("api.surface", name)
        counter.add(1, {"api.surface": name})

    return _tag
