import os
import subprocess
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
async def fresh_db_url(postgres_url: str) -> AsyncIterator[str]:
    name = f"mig_{uuid.uuid4().hex}"
    admin = create_async_engine(postgres_url, isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    yield make_url(postgres_url).set(database=name).render_as_string(hide_password=False)
    async with admin.connect() as conn:
        await conn.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
    await admin.dispose()


def alembic(url: str, *args: str) -> None:
    # subprocess: env.py runs its own event loop, which cannot nest in the test loop.
    env = {**os.environ, "APP_DATABASE_URL": url, "APP_REDIS_URL": "redis://localhost:6379/0"}
    result = subprocess.run(  # noqa: S603
        ["uv", "run", "alembic", *args],  # noqa: S607
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"alembic {' '.join(args)} failed:\n{result.stdout}{result.stderr}"
    )


def test_migrations_match_models(fresh_db_url: str) -> None:
    alembic(fresh_db_url, "upgrade", "head")
    alembic(fresh_db_url, "check")


def test_downgrade_base_roundtrips(fresh_db_url: str) -> None:
    alembic(fresh_db_url, "upgrade", "head")
    alembic(fresh_db_url, "downgrade", "base")
    alembic(fresh_db_url, "upgrade", "head")
