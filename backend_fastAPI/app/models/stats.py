from datetime import datetime
from beanie import Document, PydanticObjectId
from pydantic import Field

from app.schemas.base import CamelModel


class ScorePoint(CamelModel):
    score: int
    date: datetime = Field(default_factory=datetime.utcnow)


class LanguageBreakdown(CamelModel):
    language: str
    count: int = 0


class UserStats(Document):
    """Aggregated user statistics from all their reviews"""
    
    user_id: PydanticObjectId
    
    total_reviews: int = 0
    average_score: float = 0.0
    total_bugs: int = 0
    total_security_issues_found: int = 0
    
    score_history: list[ScorePoint] = Field(default_factory=list)
    language_breakdown: list[LanguageBreakdown] = Field(default_factory=list)
    common_weaknesses: list[str] = Field(default_factory=list)
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "user_stats"
    
      