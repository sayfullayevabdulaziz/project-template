import enum
import uuid

from sqlalchemy import CheckConstraint, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.core.db import Base, TimestampMixin, uuid7_pk


class Role(enum.StrEnum):
    admin = "admin"
    user = "user"


class User(TimestampMixin, Base):
    __tablename__ = "users"
    # Enum with native_enum=False is a plain VARCHAR(16); the CHECK is declared explicitly below.
    __table_args__ = (CheckConstraint("role in ('admin','user')", name="role"),)

    id: Mapped[uuid.UUID] = uuid7_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String)
    role: Mapped[Role] = mapped_column(
        Enum(Role, native_enum=False, length=16, create_constraint=False), default=Role.user
    )
    is_active: Mapped[bool] = mapped_column(default=True)

    @validates("email")
    def _lowercase_email(self, _key: str, value: str) -> str:
        return value.lower()
