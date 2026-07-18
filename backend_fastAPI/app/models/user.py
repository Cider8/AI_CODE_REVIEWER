from datetime import datetime
from typing import Optional
from beanie import Document
from pydantic import EmailStr, Field


class User(Document):
    name: str
    email: EmailStr
    password: str  # hashed
    avatar: Optional[str] = None
    preferred_languages: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
        indexes = ["email"]

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Jane Doe",
                "email": "jane@example.com",
                "password": "hashed_password",
            }
        }
