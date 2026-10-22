from typing import Annotated

from pydantic import AfterValidator, EmailStr

Email = Annotated[EmailStr, AfterValidator(str.lower)]
