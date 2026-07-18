from datetime import datetime
from typing import Optional
from beanie import PydanticObjectId
from pydantic import Field

from app.schemas.base import CamelModel
from app.models.stats import ScorePoint, LanguageCount
from app.schemas.review_schema import ReviewListItem


class StatsOut(CamelModel):
    id: PydanticObjectId = Field(alias="_id")
    user_id: PydanticObjectId
    total_reviews: int
    average_score: float
    total_bugs_found: int
    total_security_issues_found: int
    score_history: list[ScorePoint]
    language_breakdown: list[LanguageCount]
    common_weaknesses: list[str]
    updated_at: datetime


class DashboardResponse(CamelModel):
    stats: StatsOut
    recent_reviews: list[ReviewListItem]


# ── Collections ──────────────────────────────────────────────────────────
class CreateCollectionRequest(CamelModel):
    name: str
    description: Optional[str] = None


class AddReviewRequest(CamelModel):
    review_id: PydanticObjectId


class CollectionOut(CamelModel):
    id: PydanticObjectId = Field(alias="_id")
    user_id: PydanticObjectId
    name: str
    description: Optional[str] = None
    review_ids: list[ReviewListItem] = []  # populated
    created_at: datetime
