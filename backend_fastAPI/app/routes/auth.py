from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.models.user import User
from app.models.review import Review
from app.models.stats import UserStats
from app.models.collection import Collection
from app.models.chat import ChatSession, ChatMessage
from app.dependencies import get_current_user, require_db
from app.utils.security import hash_password, verify_password, create_access_token
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

    await Review.find(Review.user_id == user_id).delete()
    await UserStats.find(UserStats.user_id == user_id).delete()
    await Collection.find(Collection.user_id == user_id).delete()
    await current_user.delete()

    return MessageResponse(message="Account deleted successfully")
