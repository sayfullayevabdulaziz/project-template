import uuid
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.users.schemas import Email


class RegisterRequest(BaseModel):
    email: Email
    password: Annotated[str, Field(min_length=12, max_length=128)]


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
