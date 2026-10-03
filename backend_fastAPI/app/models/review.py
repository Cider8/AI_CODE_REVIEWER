from datetime import datetime
from typing import List, Literal, Optional
from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field

from app.schemas.base import CamelModel
from app.utils.time import utc_now


class Bug(CamelModel):
    line: Optional[int] = None
    # Short label such as "Off-by-one error"; feeds the dashboard's common
    # weaknesses. Optional so reviews saved before it existed still load.
    category: Optional[str] = None
    description: str
    severity: Literal["low", "medium", "high", "critical"]
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
    time: str
    space: str


class Review(Document):
    user_id: Indexed(PydanticObjectId)  # Reference to the user who created the review

    #input
    title: str = "Untitled Review"
    original_code: str
    language: str

    #AI analysis results
    summary: Optional[str] = None
    overall_score: Optional[int] = Field(default=None, ge=0, le=100)  # Score between 0 and 100

    bugs: List[Bug] = Field(default_factory=list)
    security_issues: List[SecurityIssue] = Field(default_factory=list)
    performance_issues: List[PerformanceIssue] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    refactored_code: Optional[str] = None

    complexity: Optional[Complexity] = None
    tags: List[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "reviews"
