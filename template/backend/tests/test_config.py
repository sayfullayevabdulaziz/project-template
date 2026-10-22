import pytest
from pydantic import ValidationError

from app.core.config import Settings

DB = "postgresql+asyncpg://u:p@localhost/db"
REDIS = "redis://localhost:6379/0"


@pytest.fixture(autouse=True)
def base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("APP_JWT_SECRET", "APP_COOKIE_SECURE", "APP_CORS_ORIGINS"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("APP_DATABASE_URL", DB)
    monkeypatch.setenv("APP_REDIS_URL", REDIS)


def test_jwt_secret_required() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_jwt_secret_min_32_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_JWT_SECRET", "a" * 31)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
    monkeypatch.setenv("APP_JWT_SECRET", "a" * 32)
    assert Settings(_env_file=None).jwt_secret.get_secret_value() == "a" * 32
    # 16 chars x 2 bytes = 32 bytes
    monkeypatch.setenv("APP_JWT_SECRET", "é" * 16)
    Settings(_env_file=None)


def test_cookie_secure_defaults_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_JWT_SECRET", "a" * 32)
    assert Settings(_env_file=None).cookie_secure is True


def test_cors_origins_comma_split(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_JWT_SECRET", "a" * 32)
    monkeypatch.setenv("APP_CORS_ORIGINS", "http://a.com, http://b.com")
    assert Settings(_env_file=None).cors_origins == ["http://a.com", "http://b.com"]
    monkeypatch.setenv("APP_CORS_ORIGINS", "")
    assert Settings(_env_file=None).cors_origins == []


def test_ttls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_JWT_SECRET", "a" * 32)
    s = Settings(_env_file=None)
    assert s.access_token_ttl.total_seconds() == 900
    assert s.refresh_token_ttl.days == 30
