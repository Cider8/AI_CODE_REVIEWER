from datetime import datetime
from typing import Literal
from beanie import PydanticObjectId
from pydantic import Field

from app.schemas.base import CamelModel


class SendMessageRequest(CamelModel):
    content: str = Field(min_length=1, max_length=4000)


class ChatSessionOut(CamelModel):
    id: PydanticObjectId = Field(alias="_id")
    review_id: PydanticObjectId
    user_id: PydanticObjectId
    created_at: datetime
    # Sent on open so the client can show the quota without a second call.
    remaining_messages_today: int


class ChatMessageOut(CamelModel):
    id: PydanticObjectId = Field(alias="_id")
    session_id: PydanticObjectId
    role: Literal["user", "model"]
    content: str
    created_at: datetime


class SendMessageResponse(CamelModel):
    """Both halves of the exchange, so the client can render them in order."""
    user_message: ChatMessageOut
    reply: ChatMessageOut
    remaining_messages_today: int
    

