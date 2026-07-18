from datetime import datetime
from beanie import Document, PydanticObjectId
from pydantic import Field

from app.schemas.base import CamelModel


class ScorePoint(CamelModel):
    score: int
    date: datetime = Field(default_factory=datetime.utcnow)


class LanguageCount(CamelModel):
    language: str
    count: int = 0


class UserStats(Document):
    user_id: PydanticObjectId

    total_reviews: int = 0
    average_score: float = 0
    total_bugs_found: int = 0
    total_security_issues_found: int = 0

    score_history: list[ScorePoint] = Field(default_factory=list)
    language_breakdown: list[LanguageCount] = Field(default_factory=list)
    common_weaknesses: list[str] = Field(default_factory=list)

    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "user_stats"
