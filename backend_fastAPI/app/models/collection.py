from datetime import datetime
from typing import Optional
from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field

from app.utils.time import utc_now

class Collection(Document):
    
    user_id: Indexed(PydanticObjectId) #owner of the collection
    name: str
    description: Optional[str] = None
    review_ids: list[PydanticObjectId] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now) 
    updated_at: datetime = Field(default_factory=utc_now) 
    is_archived: bool = False
    
    class Settings:
        name = "collections"  # Specify the collection name in MongoDB
        
    
        
           