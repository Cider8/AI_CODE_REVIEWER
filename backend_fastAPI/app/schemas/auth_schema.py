from datetime import datetime
from typing import Optional
from beanie import PydanticObjectId
from pydantic import EmailStr, Field, field_validator

from app.schemas.base import CamelModel

PASSWORD_SPECIAL_CHARS = "!@#$%^&+=[]{}|;:,.<>?"
PASSWORD_RULE_SEPARATOR = "; "


def check_password_rules(v: str) -> str:
    """Report every broken rule at once, joined by PASSWORD_RULE_SEPARATOR,
    so the user can fix them all in one go. The length rule lives here rather
    than in Field(min_length=...) because a failed Field constraint would stop
    this validator from running and hide the other rules."""
    failures = []
    if len(v) < 8:
        failures.append("Password must be at least 8 characters")
    if not any(char.isupper() for char in v):
        failures.append("Password must contain at least one uppercase letter")
    if not any(char.islower() for char in v):
        failures.append("Password must contain at least one lowercase letter")
    if not any(char in PASSWORD_SPECIAL_CHARS for char in v):
        failures.append("Password must contain at least one special character")
    if failures:
        raise ValueError(PASSWORD_RULE_SEPARATOR.join(failures))
    return v


class RegisterRequest(CamelModel):
    name: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        return check_password_rules(v)


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
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v):
        return check_password_rules(v)
    
class MessageResponse(CamelModel):
    message: str
