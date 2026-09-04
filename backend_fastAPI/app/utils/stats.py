"""Shared access to a user's UserStats document.

The document is created at registration, but a user can predate that step (or
the insert can have failed), and every read path then broke: the dashboard
returned 404 and new reviews were silently not counted. Creating it on demand
keeps both paths working.
"""

from beanie import PydanticObjectId
from pymongo.errors import DuplicateKeyError

from app.models.stats import UserStats


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
