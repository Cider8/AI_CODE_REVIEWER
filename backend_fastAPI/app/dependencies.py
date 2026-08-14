from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.database import is_db_connected
from app.models.user import User
from app.utils.security import decode_access_token

bearer_scheme = HTTPBearer()


async def require_db() -> None:
    """Fails fast with a clean 503 instead of a raw AttributeError/crash
    when Beanie was never initialized (e.g. MongoDB unreachable at startup)."""
    if not is_db_connected():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:
    """Equivalent to Express `protect` middleware.

    Decodes the JWT, loads the user from MongoDB, and returns it.
    Raises 401 if the token is missing/invalid or the user no longer exists.
    """
    token = credentials.credentials
    user_id = decode_access_token(token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid or expired",
        )

    user = await User.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
