from datetime import datetime
from typing import Optional
from beanie import Document
from pydantic import ConfigDict, EmailStr, Field
from pymongo import IndexModel

from app.utils.time import utc_now


class User(Document):
    name: str
    email: EmailStr
    password: str  # hashed
    avatar: Optional[str] = None
    preferred_languages: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "users"
        # Unique, so two concurrent registrations for the same address cannot
        # both slip past the "email already in use" check in the route.
        indexes = [IndexModel("email", unique=True)]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Jane Doe",
                "email": "jane@example.com",
                "password": "hashed_password",
            }
        }
    )
