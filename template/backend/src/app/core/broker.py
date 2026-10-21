import taskiq_fastapi
from taskiq import AsyncBroker, InMemoryBroker, TaskiqScheduler
from taskiq.middlewares import SimpleRetryMiddleware
from taskiq.middlewares.opentelemetry_middleware import OpenTelemetryMiddleware
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import RedisStreamBroker

from app.core.config import Settings, get_settings


def build_broker(settings: Settings) -> AsyncBroker:
    if settings.env == "test":
        # await_inplace: kiq() returns after the task ran, so tests share one session race-free.
        return InMemoryBroker(await_inplace=True)
    # SimpleRetryMiddleware is what honours the retry_on_error/max_retries task labels.
    return RedisStreamBroker(url=settings.redis_url).with_middlewares(
        SimpleRetryMiddleware(), OpenTelemetryMiddleware()
    )


broker = build_broker(get_settings())
scheduler = TaskiqScheduler(broker, sources=[LabelScheduleSource(broker)])
# Worker processes build the FastAPI app (lifespan => session_factory) from the factory path.
taskiq_fastapi.init(broker, "app.main:create_app")
