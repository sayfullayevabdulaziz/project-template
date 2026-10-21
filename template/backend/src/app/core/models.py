"""Imports every ORM model module so Base.metadata is complete (conftest and Alembic use this)."""

from app.auth import models as auth_models
from app.items import models as items_models
from app.users import models as users_models

__all__ = ["auth_models", "items_models", "users_models"]
