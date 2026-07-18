from datetime import datetime
from typing import Optional, Literal
from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field

from app.schemas.base import CamelModel


class Bug(CamelModel):
    line: Optional[int] = None
    severity: Literal["low", "medium", "high", "critical"]
    description: str
    suggestion: str


class SecurityIssue(CamelModel):
    line: Optional[int] = None
    type: str
    description: str
    fix: str


class PerformanceIssue(CamelModel):
    description: str
    suggestion: str
    impact: Literal["low", "medium", "high"]


class Complexity(CamelModel):
    time: Optional[str] = None
    space: Optional[str] = None


class Review(Document):
    user_id: Indexed(PydanticObjectId)

    # Input
    title: str = "Untitled Review"
    original_code: str
    language: str

    # AI Output
    summary: Optional[str] = None
    overall_score: Optional[int] = Field(default=None, ge=0, le=100)

    bugs: list[Bug] = Field(default_factory=list)
    security_issues: list[SecurityIssue] = Field(default_factory=list)
    performance_issues: list[PerformanceIssue] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    refactored_code: Optional[str] = None

    complexity: Optional[Complexity] = None
    tags: list[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "reviews"
