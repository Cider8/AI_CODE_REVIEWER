from datetime import datetime
from typing import Optional
from beanie import PydanticObjectId
from pydantic import EmailStr, Field, field_validator

from app.schemas.base import CamelModel


class RegisterRequest(CamelModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(char in "!@#$%^&+=[]{}|;:,.<>?" for char in v):
            raise ValueError("Password must contain at least one special character")
        return v


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
    new_password: str = Field(min_length=8)
    
    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v):
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(char in "!@#$%^&+=[]{}|;:,.<>?" for char in v):
            raise ValueError("Password must contain at least one special character")
        return v
    
class MessageResponse(CamelModel):
    message: str
