from typing import Annotated

from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.db import TimestampMixin
from app.core.pagination import ListParams, apply_sort, escape_like, list_params


class TestBase(DeclarativeBase):  # separate metadata: keep the test table out of the shared schema
    __test__ = False


class Thing(TestBase, TimestampMixin):
    __tablename__ = "pagination_test_thing"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()


app = FastAPI()


@app.get("/things")
def things(
    p: Annotated[ListParams, Depends(list_params(frozenset({"name", "created_at"})))],
) -> dict:
    return {"limit": p.limit, "offset": p.offset, "sort": p.sort, "q": p.q}


client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_limit_bounds() -> None:
    assert (await client.get("/things", params={"limit": 0})).status_code == 422
    assert (await client.get("/things", params={"limit": 101})).status_code == 422
    assert (await client.get("/things", params={"offset": -1})).status_code == 422
    r = await client.get("/things")
    assert r.status_code == 200
    assert r.json() == {"limit": 20, "offset": 0, "sort": "-created_at", "q": None}


async def test_invalid_sort_is_422() -> None:
    r = await client.get("/things", params={"sort": "password"})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail[0]["loc"] == ["query", "sort"]
    assert (await client.get("/things", params={"sort": "-name"})).status_code == 200


def sql(sort: str) -> str:
    stmt = apply_sort(select(Thing), Thing, sort)
    return str(stmt.compile(dialect=postgresql.dialect()))


def test_sort_prefix_minus_means_desc() -> None:
    assert sql("-name").endswith("ORDER BY pagination_test_thing.name DESC")
    assert sql("name").endswith("ORDER BY pagination_test_thing.name ASC")


def test_escape_like() -> None:
    assert escape_like("50%_a\\") == "50\\%\\_a\\\\"
