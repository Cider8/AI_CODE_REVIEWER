from datetime import timedelta

from beanie import PydanticObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.models.user import User
from app.models.review import Review
from app.models.stats import UserStats
from app.models.collection import Collection
from app.models.chat import ChatSession, ChatMessage
from app.models.password_reset import PasswordReset
from app.dependencies import get_current_user, require_db
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_reset_code,
    hash_reset_code,
    reset_code_matches,
    create_reset_token,
    decode_reset_token,
)
from app.utils.email import email_enabled, send_password_reset_code
from app.utils.time import utc_now
from app.utils.convert import doc_to_schema
from app.utils.stats import get_or_create_stats
from app.schemas.auth_schema import (
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    UserOut,
    UpdateProfileRequest,
    ChangePasswordRequest,
    MessageResponse,
    ForgotPasswordRequest,
    VerifyResetCodeRequest,
    VerifyResetCodeResponse,
    ResetPasswordRequest,
)

router = APIRouter(prefix="/api/auth", tags=["auth"], dependencies=[Depends(require_db)])


# POST /api/auth/register
@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    existing = await User.find_one(User.email == body.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already in use")

    user = User(
        name=body.name,
        email=body.email,
        password=hash_password(body.password),
    )
    try:
        await user.insert()
    except DuplicateKeyError:
        # Two registrations for the same address raced past the check above;
        # the unique index on User.email is what actually decides.
        raise HTTPException(status_code=400, detail="Email already in use")

    # Create empty stats doc for this user
    await get_or_create_stats(user.id)

    token = create_access_token(str(user.id))
    return AuthResponse(token=token, user=doc_to_schema(user, UserOut))


# POST /api/auth/login
@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest):
    user = await User.find_one(User.email == body.email)

    if not user or not verify_password(body.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(str(user.id))
    return AuthResponse(token=token, user=doc_to_schema(user, UserOut))


# GET /api/auth/me
@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return doc_to_schema(current_user, UserOut)


# PATCH /api/auth/profile
@router.patch("/profile", response_model=UserOut)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
):
    updates = body.model_dump(exclude_unset=True, exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")

    if "name" in updates and not updates["name"].strip():
        del updates["name"]

    for field, value in updates.items():
        setattr(current_user, field, value)

    await current_user.save()
    return doc_to_schema(current_user, UserOut)


# PATCH /api/auth/password
@router.patch("/password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
):
    if not verify_password(body.current_password, current_user.password):
        # 400, not 401: the caller is authenticated, and a 401 would make the
        # client treat a typo as an expired session and log the user out.
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    current_user.password = hash_password(body.new_password)
    await current_user.save()

    return MessageResponse(message="Password updated successfully")


# DELETE /api/auth/account
@router.delete("/account", response_model=MessageResponse)
async def delete_account(current_user: User = Depends(get_current_user)):
    user_id = current_user.id

    sessions = await ChatSession.find(ChatSession.user_id == user_id).to_list()
    session_ids = [sess.id for sess in sessions]
    if session_ids:
        await ChatMessage.find({"session_id": {"$in": session_ids}}).delete()
    await ChatSession.find(ChatSession.user_id == user_id).delete()

    await PasswordReset.find(PasswordReset.user_id == user_id).delete()
    await Review.find(Review.user_id == user_id).delete()
    await UserStats.find(UserStats.user_id == user_id).delete()
    await Collection.find(Collection.user_id == user_id).delete()
    await current_user.delete()

    return MessageResponse(message="Account deleted successfully")


# ── Forgot password ──────────────────────────────────────────────────────
# Three steps: request a code by email → verify the code (returns a short-lived
# reset token) → set a new password with that token.

RESET_CODE_MINUTES = 15       # how long an emailed code is valid
RESET_TOKEN_MINUTES = 10      # how long the verified reset token is valid
RESEND_COOLDOWN_SECONDS = 60  # a new code is not sent more often than this
MAX_CODE_ATTEMPTS = 5         # verify calls per code, right or wrong

FORGOT_PASSWORD_MESSAGE = (
    "If an account exists for this email, we've sent a 6-digit code to it."
)
INVALID_CODE_MESSAGE = "Invalid or expired code"
RESET_EXPIRED_MESSAGE = "Your reset session has expired. Please start again."


async def _send_reset_code_safely(email: str, name: str, code: str, reset_id) -> None:
    """Runs after the response is sent, so the reply takes the same time whether
    or not the account exists. A failed send drops the record so the user can
    ask again straight away instead of waiting out the cooldown."""
    try:
        await send_password_reset_code(email, name, code, RESET_CODE_MINUTES)
    except Exception as e:
        print(f"Password reset email to {email} failed: {e}")
        await PasswordReset.find(PasswordReset.id == reset_id).delete()


# POST /api/auth/forgot-password
@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(body: ForgotPasswordRequest, background: BackgroundTasks):
    if not email_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password reset by email is not available right now",
        )

    # The same answer for known and unknown emails, so this endpoint cannot be
    # used to discover which addresses have accounts.
    user = await User.find_one(User.email == body.email)
    if not user:
        return MessageResponse(message=FORGOT_PASSWORD_MESSAGE)

    now = utc_now()
    existing = await PasswordReset.find_one(PasswordReset.user_id == user.id)
    if existing and (now - existing.created_at).total_seconds() < RESEND_COOLDOWN_SECONDS:
        return MessageResponse(message=FORGOT_PASSWORD_MESSAGE)

    # One pending request per user: a new code replaces the old one.
    await PasswordReset.find(PasswordReset.user_id == user.id).delete()

    code = generate_reset_code()
    reset = PasswordReset(
        user_id=user.id,
        code_hash=hash_reset_code(code),
        expires_at=now + timedelta(minutes=RESET_CODE_MINUTES),
    )
    await reset.insert()

    background.add_task(_send_reset_code_safely, user.email, user.name, code, reset.id)
    return MessageResponse(message=FORGOT_PASSWORD_MESSAGE)


# POST /api/auth/verify-reset-code
@router.post("/verify-reset-code", response_model=VerifyResetCodeResponse)
async def verify_reset_code(body: VerifyResetCodeRequest):
    user = await User.find_one(User.email == body.email)
    if not user:
        raise HTTPException(status_code=400, detail=INVALID_CODE_MESSAGE)

    # Charge the attempt atomically before comparing, so parallel guesses
    # cannot get past the cap.
    raw = await PasswordReset.get_motor_collection().find_one_and_update(
        {
            "user_id": user.id,
            "verified": False,
            "attempts": {"$lt": MAX_CODE_ATTEMPTS},
            "expires_at": {"$gt": utc_now()},
        },
        {"$inc": {"attempts": 1}},
    )
    if not raw:
        raise HTTPException(status_code=400, detail=INVALID_CODE_MESSAGE)

    reset = await PasswordReset.get(raw["_id"])
    if not reset or not reset_code_matches(body.code, reset.code_hash):
        if reset and reset.attempts >= MAX_CODE_ATTEMPTS:
            await reset.delete()  # burned: the user must request a new code
        raise HTTPException(status_code=400, detail=INVALID_CODE_MESSAGE)

    reset.verified = True
    reset.expires_at = utc_now() + timedelta(minutes=RESET_TOKEN_MINUTES)
    await reset.save()

    return VerifyResetCodeResponse(
        reset_token=create_reset_token(str(user.id), str(reset.id), RESET_TOKEN_MINUTES),
        expires_in_minutes=RESET_TOKEN_MINUTES,
    )


# POST /api/auth/reset-password
@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(body: ResetPasswordRequest):
    decoded = decode_reset_token(body.reset_token)
    if not decoded:
        raise HTTPException(status_code=400, detail=RESET_EXPIRED_MESSAGE)
    user_id, reset_id = decoded
    if not (PydanticObjectId.is_valid(user_id) and PydanticObjectId.is_valid(reset_id)):
        raise HTTPException(status_code=400, detail=RESET_EXPIRED_MESSAGE)

    # Consume the verified record atomically: a reset token works exactly once,
    # and stops working if a newer code was requested in the meantime.
    result = await PasswordReset.get_motor_collection().delete_one(
        {
            "_id": PydanticObjectId(reset_id),
            "user_id": PydanticObjectId(user_id),
            "verified": True,
            "expires_at": {"$gt": utc_now()},
        }
    )
    if result.deleted_count != 1:
        raise HTTPException(status_code=400, detail=RESET_EXPIRED_MESSAGE)

    user = await User.get(PydanticObjectId(user_id))
    if not user:
        raise HTTPException(status_code=400, detail=RESET_EXPIRED_MESSAGE)

    user.password = hash_password(body.new_password)
    await user.save()

    return MessageResponse(message="Password updated. Please sign in with your new password.")
