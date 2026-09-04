from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.config import settings
from app.models.user import User
from app.models.review import Review
from app.models.stats import UserStats
from app.models.collection import Collection
from app.models.chat import ChatSession, ChatMessage

db_connected = False
_client: AsyncIOMotorClient | None = None


def is_db_connected() -> bool:
    return db_connected


async def init_db():
    global db_connected, _client

    _client = AsyncIOMotorClient(settings.mongo_uri)
    db = _client[settings.db_name]

    await init_beanie(
        database=db,
        document_models=[User, Review, UserStats, Collection, ChatSession, ChatMessage],
    )
    db_connected = True


async def close_db():
    """Release the connection pool on shutdown; without this the client and its
    background monitor threads outlive the app (noisy in tests and reloads)."""
    global db_connected, _client

    if _client is not None:
        _client.close()
        _client = None
    db_connected = False
