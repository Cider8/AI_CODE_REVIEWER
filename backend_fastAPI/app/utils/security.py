import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.jwt_expire_days)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    # Purpose-scoped tokens (e.g. password reset) share the signing key, so
    # they must never be accepted as a login session.
    if payload.get("purpose"):
        return None
    return payload.get("sub")


# ── Forgot password ──────────────────────────────────────────────────────
RESET_PURPOSE = "password_reset"


def generate_reset_code() -> str:
    """Six random digits, from a CSPRNG."""
    return f"{secrets.randbelow(10**6):06d}"


def hash_reset_code(code: str) -> str:
    """HMAC rather than bcrypt: the code is short-lived and attempts are
    capped, and keying it with the server secret means a leaked database
    alone cannot be used to brute-force the 10^6 possible codes."""
    return hmac.new(settings.jwt_secret.encode(), code.encode(), hashlib.sha256).hexdigest()


def reset_code_matches(code: str, code_hash: str) -> bool:
    return hmac.compare_digest(hash_reset_code(code), code_hash)


def create_reset_token(user_id: str, reset_id: str, minutes: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=minutes)
    payload = {"sub": user_id, "rid": reset_id, "purpose": RESET_PURPOSE, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_reset_token(token: str) -> tuple[str, str] | None:
    """(user_id, reset_id) for a valid, unexpired reset token, else None."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    if payload.get("purpose") != RESET_PURPOSE:
        return None
    user_id, reset_id = payload.get("sub"), payload.get("rid")
    if not user_id or not reset_id:
        return None
    return user_id, reset_id
