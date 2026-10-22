import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped
from sqlalchemy.schema import ColumnDefault

from app.core.db import Base, uuid7_pk


@pytest.fixture(scope="module", autouse=True)
async def scratch_table(engine: AsyncEngine) -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE scratch (id integer PRIMARY KEY)"))
    yield
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE scratch"))


async def test_session_rolls_back_between_tests_a(session: AsyncSession) -> None:
    await session.execute(text("INSERT INTO scratch (id) VALUES (1)"))
    await session.commit()
    assert (await session.execute(text("SELECT count(*) FROM scratch"))).scalar_one() == 1


async def test_session_rolls_back_between_tests_b(session: AsyncSession) -> None:
    assert (await session.execute(text("SELECT count(*) FROM scratch"))).scalar_one() == 0


def test_naming_convention() -> None:
    assert Base.metadata.naming_convention["pk"] == "pk_%(table_name)s"


def test_uuid7_pk_is_v7() -> None:
    class Probe(DeclarativeBase):
        pass

    class Item(Probe):
        __tablename__ = "item"
        id: Mapped[uuid.UUID] = uuid7_pk()

    default = Item.__table__.c.id.default
    assert isinstance(default, ColumnDefault)
    generated = default.arg(None)
    assert isinstance(generated, uuid.UUID)
    assert generated.version == 7
