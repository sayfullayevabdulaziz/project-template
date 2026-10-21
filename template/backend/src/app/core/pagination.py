from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Query
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from sqlalchemy import Select


class Page[T](BaseModel):
    items: list[T]
    total: int


@dataclass
class ListParams:
    limit: int
    offset: int
    sort: str
    q: str | None


def list_params(allowed_sorts: frozenset[str]) -> Callable[..., ListParams]:
    def dependency(
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
        sort: str = "-created_at",
        q: str | None = None,
    ) -> ListParams:
        if sort.removeprefix("-") not in allowed_sorts:
            raise RequestValidationError(
                [
                    {
                        "type": "value_error",
                        "loc": ("query", "sort"),
                        "msg": f"sort must be one of {sorted(allowed_sorts)}, '-' prefix for desc",
                        "input": sort,
                    }
                ]
            )
        return ListParams(limit=limit, offset=offset, sort=sort, q=q)

    return dependency


def apply_sort[S: Select[Any]](stmt: S, model: type, sort: str) -> S:
    column = getattr(model, sort.removeprefix("-"))
    return stmt.order_by(column.desc() if sort.startswith("-") else column.asc())


def escape_like(q: str) -> str:
    return q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
