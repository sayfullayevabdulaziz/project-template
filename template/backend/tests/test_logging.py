import json
import logging
from collections.abc import Iterator

import pytest
import structlog
from opentelemetry.sdk.trace import TracerProvider

from app.core.logging import configure_logging


@pytest.fixture(autouse=True)
def _reset_logging() -> Iterator[None]:
    yield
    structlog.reset_defaults()
    root = logging.getLogger()
    for h in [h for h in root.handlers if getattr(h, "_app_handler", False)]:
        root.removeHandler(h)


def _last_json(capsys: pytest.CaptureFixture[str]) -> dict:
    return json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def test_logs_are_json_with_trace_ids(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging()
    log = structlog.get_logger()

    log.info("outside")
    outside = _last_json(capsys)
    assert outside["event"] == "outside"
    assert outside["level"] == "info"
    assert outside["timestamp"].endswith("Z")
    assert "trace_id" not in outside
    assert "span_id" not in outside

    tracer = TracerProvider().get_tracer("test")
    with tracer.start_as_current_span("work") as span:
        log.info("inside")
    inside = _last_json(capsys)
    assert inside["trace_id"] == format(span.get_span_context().trace_id, "032x")
    assert inside["span_id"] == format(span.get_span_context().span_id, "016x")
    assert len(inside["span_id"]) == 16


def test_stdlib_logging_is_routed_through_structlog(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging()
    tracer = TracerProvider().get_tracer("test")
    with tracer.start_as_current_span("work") as span:
        logging.getLogger("some.lib").warning("from stdlib")
    out = _last_json(capsys)
    assert out["event"] == "from stdlib"
    assert out["level"] == "warning"
    assert out["trace_id"] == format(span.get_span_context().trace_id, "032x")


def test_configure_logging_is_idempotent(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging()
    configure_logging()
    structlog.get_logger().info("once")
    assert len(capsys.readouterr().out.strip().splitlines()) == 1
