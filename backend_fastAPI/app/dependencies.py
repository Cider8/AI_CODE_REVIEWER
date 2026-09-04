from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from beanie import PydanticObjectId

from app.database import is_db_connected
from app.models.user import User
from app.utils.security import decode_access_token

# auto_error would raise 403 when the Authorization header is missing, but the
# frontend only clears the token and redirects to /login on a 401 — so the
# missing-header case is handled here and answered with 401 like the others.
bearer_scheme = HTTPBearer(auto_error=False)


async def require_db() -> None:
    """Fails fast with a clean 503 instead of a raw AttributeError/crash
    when Beanie was never initialized (e.g. MongoDB unreachable at startup)."""
    if not is_db_connected():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> User:
    """Equivalent to Express `protect` middleware.

    Decodes the JWT, loads the user from MongoDB, and returns it.
    Raises 401 if the token is missing/invalid or the user no longer exists.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = decode_access_token(credentials.credentials)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid or expired",
        )

    # A token whose `sub` is not a valid ObjectId would make User.get raise a
    # ValidationError (a 500); it is just a bad token, so treat it as one.
    if not PydanticObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid or expired",
        )

    user = await User.get(PydanticObjectId(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
