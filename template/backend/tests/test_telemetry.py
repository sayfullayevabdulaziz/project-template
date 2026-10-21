import httpx
import pytest
from fastapi import APIRouter, FastAPI
from opentelemetry import metrics, trace
from opentelemetry.metrics import _internal as metrics_internal
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader, NumberDataPoint
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import SecretStr

from app import health
from app.api.admin import router as admin_router
from app.api.public import router as public_router
from app.api.tagging import tag_surface
from app.core.config import Settings
from app.core.telemetry import setup_telemetry, telemetry_config


@pytest.fixture
def span_exporter() -> InMemorySpanExporter:
    return InMemorySpanExporter()


@pytest.fixture
def tracer_provider(span_exporter: InMemorySpanExporter) -> TracerProvider:
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    return provider


def test_tag_surface_sets_attribute(
    tracer_provider: TracerProvider, span_exporter: InMemorySpanExporter
) -> None:
    with tracer_provider.get_tracer("test").start_as_current_span("req"):
        tag_surface("admin")()
    (span,) = span_exporter.get_finished_spans()
    assert span.attributes is not None
    assert span.attributes["api.surface"] == "admin"


def test_tag_surface_counter_has_attribute(monkeypatch: pytest.MonkeyPatch) -> None:
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader])
    # The global provider can be set only once per process, so route this lookup to a local one.
    monkeypatch.setattr(metrics_internal, "get_meter_provider", lambda: provider)
    tag_surface("public")()
    tag_surface("public")()
    data = reader.get_metrics_data()
    assert data is not None
    (metric,) = data.resource_metrics[0].scope_metrics[0].metrics
    assert metric.name == "app.surface.requests"
    (point,) = metric.data.data_points
    assert isinstance(point, NumberDataPoint)
    assert point.attributes == {"api.surface": "public"}
    assert point.value == 2


@pytest.mark.parametrize(("router", "name"), [(admin_router, "admin"), (public_router, "public")])
def test_surface_dependency_on_routers(
    router: APIRouter,
    name: str,
    tracer_provider: TracerProvider,
    span_exporter: InMemorySpanExporter,
) -> None:
    (dep,) = router.dependencies
    assert dep.dependency is not None
    with tracer_provider.get_tracer("test").start_as_current_span("req"):
        dep.dependency()
    (span,) = span_exporter.get_finished_spans()
    assert span.attributes is not None
    assert span.attributes["api.surface"] == name


def test_setup_telemetry_noop_without_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    tracer_before = trace.get_tracer_provider()
    meter_before = metrics.get_meter_provider()
    settings = Settings(
        env="test",
        database_url="postgresql+asyncpg://u:p@localhost/db",
        redis_url="redis://localhost:6379/0",
        jwt_secret=SecretStr("x" * 40),
    )
    setup_telemetry(settings)
    assert trace.get_tracer_provider() is tracer_before
    assert metrics.get_meter_provider() is meter_before


async def test_health_routes_excluded_from_telemetry(
    tracer_provider: TracerProvider, span_exporter: InMemorySpanExporter
) -> None:
    app = FastAPI(telemetry={**telemetry_config(), "tracer_provider": tracer_provider})
    app.include_router(health.router)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get("/health/live")).status_code == 200
        assert span_exporter.get_finished_spans() == ()
        assert (await client.get("/ping")).status_code == 200
    assert {s.name for s in span_exporter.get_finished_spans()} >= {"GET /ping"}
