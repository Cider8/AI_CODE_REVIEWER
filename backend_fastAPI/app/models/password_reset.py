from datetime import datetime
from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field
from pymongo import IndexModel

from app.utils.time import utc_now


class PasswordReset(Document):
    """One pending forgot-password request. A user has at most one: asking
    again replaces it. The code itself is never stored, only its HMAC."""

    user_id: Indexed(PydanticObjectId)
    code_hash: str
    expires_at: datetime
    # Every verify call counts, right or wrong; capped at MAX_CODE_ATTEMPTS.
    attempts: int = 0
    # Set once the code is verified; the reset token is bound to this record,
    # so the token stops working as soon as the record is used or replaced.
    verified: bool = False
    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "password_resets"
        # MongoDB's TTL monitor deletes the document once expires_at passes,
        # so abandoned requests clean themselves up.
        indexes = [IndexModel("expires_at", expireAfterSeconds=0)]
