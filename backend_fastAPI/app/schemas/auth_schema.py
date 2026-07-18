from datetime import datetime
from typing import Optional
from beanie import PydanticObjectId
from pydantic import EmailStr, Field

from app.schemas.base import CamelModel


class RegisterRequest(CamelModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=6)


class LoginRequest(CamelModel):
    email: EmailStr
    password: str


class UserOut(CamelModel):
    id: PydanticObjectId = Field(alias="_id")
    name: str
    email: EmailStr
    avatar: Optional[str] = None
    preferred_languages: list[str] = []
    created_at: datetime


class AuthResponse(CamelModel):
    token: str
    user: UserOut


class UpdateProfileRequest(CamelModel):
    name: Optional[str] = None
    preferred_languages: Optional[list[str]] = None


class ChangePasswordRequest(CamelModel):
    current_password: str
    new_password: str = Field(min_length=6)


class MessageResponse(CamelModel):
    message: str
