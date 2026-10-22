import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.pagination import Page
from app.users.models import Role


class UserAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: Role
    is_active: bool
    created_at: datetime


class UserAdminUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None


class UserAdminPage(Page[UserAdmin]):
    pass
