from fastapi import APIRouter, Depends, HTTPException

from app.models.user import User
from app.models.stats import UserStats
from app.models.review import Review
from app.dependencies import get_current_user, require_db
from app.utils.convert import doc_to_schema
from app.schemas.stats_schema import DashboardResponse, StatsOut
from app.schemas.review_schema import ReviewListItem

router = APIRouter(prefix="/api/stats", tags=["stats"], dependencies=[Depends(require_db)])


# GET /api/stats — dashboard data
@router.get("", response_model=DashboardResponse)
async def get_stats(current_user: User = Depends(get_current_user)):
    stats = await UserStats.find_one(UserStats.user_id == current_user.id)
    if not stats:
        raise HTTPException(status_code=404, detail="Stats not found")

    recent_docs = await (
        Review.find(Review.user_id == current_user.id)
        .sort(-Review.created_at)
        .limit(5)
        .to_list()
    )
    recent_reviews = [doc_to_schema(d, ReviewListItem) for d in recent_docs]

    return DashboardResponse(
        stats=doc_to_schema(stats, StatsOut),
        recent_reviews=recent_reviews,
    )
