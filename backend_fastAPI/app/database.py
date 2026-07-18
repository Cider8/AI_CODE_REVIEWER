from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.config import settings
from app.models.user import User
from app.models.review import Review
from app.models.stats import UserStats
from app.models.collection import Collection


async def init_db():
    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client[settings.db_name]

    await init_beanie(
        database=db,
        document_models=[User, Review, UserStats, Collection],
    )
