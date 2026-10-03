"""Shared access to a user's UserStats document.

The document is created at registration, but a user can predate that step (or
the insert can have failed), and every read path then broke: the dashboard
returned 404 and new reviews were silently not counted. Creating it on demand
keeps both paths working.
"""

from collections import Counter

from beanie import PydanticObjectId
from pymongo.errors import DuplicateKeyError

from app.models.review import Review
from app.models.stats import LanguageBreakdown, ScorePoint, UserStats
from app.utils.time import utc_now


async def get_or_create_stats(user_id: PydanticObjectId) -> UserStats:
    stats = await UserStats.find_one(UserStats.user_id == user_id)
    if stats:
        return stats

    stats = UserStats(user_id=user_id)
    try:
        await stats.insert()
    except DuplicateKeyError:
        # Another request created it first; the unique index caught the race.
        stats = await UserStats.find_one(UserStats.user_id == user_id)
    return stats


# A weakness has to recur across reviews to count; one-off findings are noise.
WEAKNESS_MIN_REVIEWS = 2
WEAKNESS_LIMIT = 5


def _common_weaknesses(reviews: list[Review]) -> list[str]:
    """Most frequent bug categories and security issue types, counted once per
    review so a single snippet with five identical findings cannot dominate."""
    counts: Counter[str] = Counter()
    labels: dict[str, str] = {}
    for review in reviews:
        found = {b.category for b in review.bugs if b.category}
        found |= {s.type for s in review.security_issues if s.type}
        keys = set()
        for label in found:
            key = " ".join(label.split()).lower()
            if key:
                labels.setdefault(key, " ".join(label.split()))
                keys.add(key)
        counts.update(keys)

    return [
        labels[key]
        for key, n in counts.most_common()
        if n >= WEAKNESS_MIN_REVIEWS
    ][:WEAKNESS_LIMIT]


def apply_review_totals(stats: UserStats, reviews: list[Review]) -> None:
    """Rebuild every review-derived figure from the reviews the user still has,
    so the dashboard reflects current reviews rather than lifetime activity.
    Leaves the chat quota fields alone."""
    reviews = sorted(reviews, key=lambda r: r.created_at)
    scores = [r.overall_score or 0 for r in reviews]

    languages: Counter[str] = Counter(r.language for r in reviews)

    stats.total_reviews = len(reviews)
    # Kept to 2dp: the dashboard shows a decimal average.
    stats.average_score = round(sum(scores) / len(scores), 2) if scores else 0.0
    stats.total_bugs_found = sum(len(r.bugs) for r in reviews)
    stats.total_security_issues_found = sum(len(r.security_issues) for r in reviews)
    stats.score_history = [
        ScorePoint(score=s, date=r.created_at) for s, r in zip(scores, reviews)
    ]
    stats.language_breakdown = [
        LanguageBreakdown(language=lang, count=n) for lang, n in languages.most_common()
    ]
    stats.common_weaknesses = _common_weaknesses(reviews)
    stats.updated_at = utc_now()


async def recompute_stats(user_id: PydanticObjectId) -> UserStats:
    stats = await get_or_create_stats(user_id)
    reviews = await Review.find(Review.user_id == user_id).to_list()
    apply_review_totals(stats, reviews)
    await stats.save()
    return stats
