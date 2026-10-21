import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.pagination import Page
from app.items.schemas import Description, Name


class ItemCreate(BaseModel):
    name: Name
    description: Description | None = None
    is_published: bool = False


class ItemUpdate(BaseModel):
    # router passes only the set fields; null name/is_published are ignored (columns are NOT NULL)
    name: Name | None = None
    description: Description | None = None
    is_published: bool | None = None


class ItemAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    is_published: bool
    created_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ItemAdminPage(Page[ItemAdmin]):
    pass
