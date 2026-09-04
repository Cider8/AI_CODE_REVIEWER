# In this model, I will create two model such as chatSession and chatMessage. The chatSession will store the information about the session and the chatMessage will store the information about the message. The chatSession will have a one-to-many relationship with the chatMessage. The chatSession will have a unique id, user id, and created_at timestamp. The chatMessage will have a unique id, session id, message text, and created_at timestamp.

from datetime import datetime
from typing import Literal
from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field

from app.utils.time import utc_now


# ChatSession model
class ChatSession(Document):
    review_id: Indexed(PydanticObjectId)  # Reference to the review associated with the session
    user_id: Indexed(PydanticObjectId)  # Reference to the user who created the session
    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "chat_sessions"
        
        
# ChatMessage model
class ChatMessage(Document):
    session_id: Indexed(PydanticObjectId)  # Reference to the chat session
    role: Literal["user", "model"]  # Role of the message sender
    content: str
    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "chat_messages"
        
