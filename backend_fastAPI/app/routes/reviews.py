import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from beanie import PydanticObjectId
from beanie.operators import RegEx

from app.models.user import User
from app.models.review import Review
from app.models.stats import UserStats, ScorePoint, LanguageCount
from app.dependencies import get_current_user, require_db
from app.utils.gemini import analyze_code
from app.utils.convert import doc_to_schema
from app.schemas.review_schema import (
    CreateReviewRequest,
    ReviewDetail,
    ReviewListItem,
    PaginatedReviews,
)

router = APIRouter(prefix="/api/reviews", tags=["reviews"], dependencies=[Depends(require_db)])


# POST /api/reviews — submit code for AI review
@router.post("", response_model=ReviewDetail, status_code=status.HTTP_201_CREATED)
async def create_review(
    body: CreateReviewRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        ai_result = await analyze_code(body.original_code, body.language)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

    review = Review(
        user_id=current_user.id,
        title=body.title or f"{body.language} Review",
        original_code=body.original_code,
        language=body.language,
        summary=ai_result.summary,
        overall_score=ai_result.overall_score,
        bugs=ai_result.bugs,
        security_issues=ai_result.security_issues,
        performance_issues=ai_result.performance_issues,
        improvements=ai_result.improvements,
        refactored_code=ai_result.refactored_code,
        complexity=ai_result.complexity,
        tags=ai_result.tags,
    )
    await review.insert()

    await _update_stats(current_user.id, review, ai_result)

    return doc_to_schema(review, ReviewDetail)


# GET /api/reviews — paginated list with optional search/filter
@router.get("", response_model=PaginatedReviews)
async def list_reviews(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    language: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    query = Review.find(Review.user_id == current_user.id)

    if language:
        query = query.find(Review.language == language)
    if search:
        query = query.find(RegEx(Review.title, search, "i"))

    total = await query.count()

    docs = await (
        query
        .sort(-Review.created_at)
        .skip((page - 1) * limit)
        .limit(limit)
        .to_list()
    )

    reviews = [doc_to_schema(d, ReviewListItem) for d in docs]

    return PaginatedReviews(
        reviews=reviews,
        total=total,
        page=page,
        pages=math.ceil(total / limit) if total else 0,
    )


# GET /api/reviews/{id}
@router.get("/{review_id}", response_model=ReviewDetail)
async def get_review(
    review_id: PydanticObjectId,
    current_user: User = Depends(get_current_user),
):
    review = await Review.find_one(
        Review.id == review_id,
        Review.user_id == current_user.id,
    )
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    return doc_to_schema(review, ReviewDetail)


# DELETE /api/reviews/{id}
@router.delete("/{review_id}")
async def delete_review(
    review_id: PydanticObjectId,
    current_user: User = Depends(get_current_user),
):
    review = await Review.find_one(
        Review.id == review_id,
        Review.user_id == current_user.id,
    )
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    await review.delete()
    return {"message": "Review deleted"}


# ── Helper: update UserStats after a new review ──────────────────────────
async def _update_stats(user_id: PydanticObjectId, review: Review, ai_result):
    stats = await UserStats.find_one(UserStats.user_id == user_id)
    if not stats:
        return

    new_total = stats.total_reviews + 1
    new_avg = round(
        (stats.average_score * stats.total_reviews + (ai_result.overall_score or 0)) / new_total
    )

    # Language breakdown
    lang_entry = next(
        (l for l in stats.language_breakdown if l.language == review.language), None
    )
    if lang_entry:
        lang_entry.count += 1
    else:
        stats.language_breakdown.append(LanguageCount(language=review.language, count=1))

    stats.total_reviews = new_total
    stats.average_score = new_avg
    stats.total_bugs_found += len(ai_result.bugs)
    stats.total_security_issues_found += len(ai_result.security_issues)
    stats.score_history.append(ScorePoint(score=ai_result.overall_score or 0))

    await stats.save()
