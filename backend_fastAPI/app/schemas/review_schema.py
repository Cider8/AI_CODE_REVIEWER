from datetime import datetime
from typing import Optional
from beanie import PydanticObjectId
from pydantic import Field

from app.schemas.base import CamelModel
from app.models.review import Bug, SecurityIssue, PerformanceIssue, Complexity


class CreateReviewRequest(CamelModel):
    title: Optional[str] = None
    language: str
    original_code: str = Field(min_length=1)


class ReviewListItem(CamelModel):
    """Lightweight view for list endpoints (no code fields)."""
    id: PydanticObjectId = Field(alias="_id")
    title: str
    language: str
    overall_score: Optional[int] = None
    created_at: datetime


class ReviewDetail(CamelModel):
    """Full review including code + AI analysis."""
    id: PydanticObjectId = Field(alias="_id")
    user_id: PydanticObjectId
    title: str
    original_code: str
    language: str

    summary: Optional[str] = None
    overall_score: Optional[int] = None

    bugs: list[Bug] = []
    security_issues: list[SecurityIssue] = []
    performance_issues: list[PerformanceIssue] = []
    improvements: list[str] = []
    refactored_code: Optional[str] = None
    complexity: Optional[Complexity] = None
    tags: list[str] = []

    created_at: datetime


class PaginatedReviews(CamelModel):
    reviews: list[ReviewListItem]
    total: int
    page: int
    pages: int


# ── AI response shape (what Gemini must return) ──────────────────────────
class AIReviewResult(CamelModel):
    summary: str
    overall_score: int = Field(ge=0, le=100)
    bugs: list[Bug] = []
    security_issues: list[SecurityIssue] = []
    performance_issues: list[PerformanceIssue] = []
    improvements: list[str] = []
    refactored_code: str
    complexity: Complexity
    tags: list[str] = []
