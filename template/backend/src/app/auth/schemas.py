from typing import Annotated

from pydantic import BaseModel, Field

from app.users.schemas import Email


class LoginRequest(BaseModel):
    email: Email
    password: Annotated[str, Field(min_length=1, max_length=128)]
