from datetime import date, datetime
from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import IndexModel

from app.schemas.base import CamelModel
from app.utils.time import utc_now


class ScorePoint(CamelModel):
    score: int
    date: datetime = Field(default_factory=utc_now)


class LanguageBreakdown(CamelModel):
    language: str
    count: int = 0


class UserStats(Document):
    """Aggregated user statistics from all their reviews"""
    
    user_id: PydanticObjectId
    
    total_reviews: int = 0
    average_score: float = 0.0
    total_bugs_found: int = 0
    total_security_issues_found: int = 0
    
    score_history: list[ScorePoint] = Field(default_factory=list)
    language_breakdown: list[LanguageBreakdown] = Field(default_factory=list)
    common_weaknesses: list[str] = Field(default_factory=list)
    
    updated_at: datetime = Field(default_factory=utc_now)
    
    # Daily chat quota. A count alone can never reset itself, so it is stored
    # alongside the day it belongs to: on each chat request, compare
    # chat_count_date with today's UTC date — if it is older, the day rolled
    # over, so set chat_count_date = today and daily_chat_count = 1; if it
    # matches, increment daily_chat_count and reject once it hits the cap.
    daily_chat_count: int = 0
    chat_count_date: date = Field(default_factory=lambda: utc_now().date())
    
    
    class Settings:
        name = "user_stats"
        # One stats document per user, and it is looked up by user_id on
        # every dashboard/review request.
        indexes = [IndexModel("user_id", unique=True)]
    
      