from datetime import datetime
from typing import Optional
from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field


class Collection(Document):
    user_id: Indexed(PydanticObjectId)
    name: str
    description: Optional[str] = None
    review_ids: list[PydanticObjectId] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "collections"
