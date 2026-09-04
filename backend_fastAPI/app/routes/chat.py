"""Follow-up chat about a review: a session is scoped to one review, and the
messages in it alternate between the user and the model."""

from fastapi import APIRouter, Depends, HTTPException, status
from beanie import PydanticObjectId

from app.models.chat import ChatSession, ChatMessage
from app.models.review import Review
from app.models.stats import UserStats
from app.models.user import User
from app.dependencies import get_current_user, require_db
from app.utils.convert import doc_to_schema
from app.utils.gemini import chat_about_review
from app.utils.stats import get_or_create_stats
from app.utils.time import utc_now
from app.schemas.chat_schema import (
    ChatMessageOut,
    ChatSessionOut,
    SendMessageRequest,
    SendMessageResponse,
)

router = APIRouter(prefix="/api/chat", tags=["chat"], dependencies=[Depends(require_db)])

# Cap on model-answered messages per user per UTC day.
DAILY_CHAT_LIMIT = 20

# How many prior turns are replayed to the model.
HISTORY_LIMIT = 6


async def _get_owned_session(
    session_id: PydanticObjectId, user: User
) -> ChatSession:
    """404 rather than 403 for someone else's session, so the endpoint does not
    confirm that the id exists."""
    session = await ChatSession.get(session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session


def _remaining_today(stats: UserStats) -> int:
    """Quota left for the current UTC day, without charging for it. A counter
    left over from an earlier day is stale, so the full limit is still free —
    `_consume_chat_quota` is what actually persists that rollover."""
    if stats.chat_count_date != utc_now().date():
        return DAILY_CHAT_LIMIT
    return max(0, DAILY_CHAT_LIMIT - stats.daily_chat_count)


async def _consume_chat_quota(current_user: User) -> int:
    """Roll the counter over when the UTC day changes, then charge one message."""
    stats = await get_or_create_stats(current_user.id)

    today = utc_now().date()
    if stats.chat_count_date != today:
        stats.chat_count_date = today
        stats.daily_chat_count = 0

    if stats.daily_chat_count >= DAILY_CHAT_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily chat limit of {DAILY_CHAT_LIMIT} messages reached",
        )

    stats.daily_chat_count += 1
    await stats.save()
    return DAILY_CHAT_LIMIT - stats.daily_chat_count


# POST /api/chat/reviews/{review_id}/start — open a session for one review
@router.post(
    "/reviews/{review_id}/start",
    response_model=ChatSessionOut,
    status_code=status.HTTP_201_CREATED,
)
async def start_chat_session(
    review_id: PydanticObjectId,
    current_user: User = Depends(get_current_user),
):
    review = await Review.find_one(
        Review.id == review_id,
        Review.user_id == current_user.id,
    )
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Reuse the existing session so a page reload does not orphan the history.
    session = await ChatSession.find_one(
        ChatSession.review_id == review_id,
        ChatSession.user_id == current_user.id,
    )
    if not session:
        session = ChatSession(review_id=review_id, user_id=current_user.id)
        await session.insert()

    stats = await get_or_create_stats(current_user.id)
    return doc_to_schema(
        session,
        ChatSessionOut,
        remaining_messages_today=_remaining_today(stats),
    )


# GET /api/chat/sessions/{session_id}/messages
@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
async def get_chat_messages(
    session_id: PydanticObjectId,
    current_user: User = Depends(get_current_user),
):
    await _get_owned_session(session_id, current_user)

    messages = await (
        ChatMessage.find(ChatMessage.session_id == session_id)
        .sort(+ChatMessage.created_at)
        .to_list()
    )
    return [doc_to_schema(m, ChatMessageOut) for m in messages]


# POST /api/chat/sessions/{session_id}/messages — ask, and get the reply
@router.post(
    "/sessions/{session_id}/messages",
    response_model=SendMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_chat_message(
    session_id: PydanticObjectId,
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user),
):
    session = await _get_owned_session(session_id, current_user)

    review = await Review.get(session.review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review for this session no longer exists")

    remaining = await _consume_chat_quota(current_user)

    history = await (
        ChatMessage.find(ChatMessage.session_id == session_id)
        .sort(-ChatMessage.created_at)
        .limit(HISTORY_LIMIT)
        .to_list()
    )
    history.reverse()  # sorted newest-first above; the model needs oldest-first

    # Built before the call so its created_at is the ask time, which keeps it
    # strictly ahead of the reply's when the transcript is sorted.
    user_message = ChatMessage(session_id=session_id, role="user", content=body.content)

    try:
        answer = await chat_about_review(
            code=review.original_code,
            language=review.language,
            summary=review.summary or "",
            history=[{"role": m.role, "content": m.content} for m in history],
            question=body.content,
        )
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Persisted only once the model answered, so a failed call leaves no
    # dangling user turn in the transcript. Inserted one at a time rather than
    # with insert_many, which does not write the generated _id back onto the
    # documents and would leave the response schema without an id.
    reply = ChatMessage(session_id=session_id, role="model", content=answer)
    await user_message.insert()
    await reply.insert()

    return SendMessageResponse(
        user_message=doc_to_schema(user_message, ChatMessageOut),
        reply=doc_to_schema(reply, ChatMessageOut),
        remaining_messages_today=remaining
    )
