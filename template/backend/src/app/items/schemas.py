import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.core.pagination import Page

Name = Annotated[str, Field(min_length=1, max_length=200)]
Description = Annotated[str, Field(max_length=2000)]


class ItemCreate(BaseModel):
    name: Name
    description: Description | None = None
    is_published: bool = False


class ItemUpdate(BaseModel):
    # model_fields_set drives the patch; null name/is_published are ignored (columns are NOT NULL)
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


class ItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None


class ItemAdminPage(Page[ItemAdmin]):
    pass


class ItemPublicPage(Page[ItemPublic]):
    pass
