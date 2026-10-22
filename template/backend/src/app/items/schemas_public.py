import uuid

from pydantic import BaseModel, ConfigDict

from app.core.pagination import Page


class ItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None


class ItemPublicPage(Page[ItemPublic]):
    pass
