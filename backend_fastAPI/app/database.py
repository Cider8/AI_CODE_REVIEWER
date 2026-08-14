from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.config import settings
from app.models.user import User
from app.models.review import Review
from app.models.stats import UserStats
from app.models.collection import Collection

db_connected = False


def is_db_connected() -> bool:
    return db_connected


async def init_db():
    global db_connected

    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client[settings.db_name]

    await init_beanie(
        database=db,
        document_models=[User, Review, UserStats, Collection],
    )
    db_connected = True
