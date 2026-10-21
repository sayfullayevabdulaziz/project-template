import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin, uuid7_pk


class Item(TimestampMixin, Base):
    __tablename__ = "items"

    id: Mapped[uuid.UUID] = uuid7_pk()
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(2000))
    is_published: Mapped[bool] = mapped_column(default=False, index=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
