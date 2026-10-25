# Design: Review Chat

**Feature:** a member asks the AI follow-up questions about one review.
**Code:** `app/routes/chat.py`, `app/utils/gemini.py` (`chat_about_review`), `app/models/chat.py`

## API

| # | Method & path | Body | Success | Errors |
|---|---|---|---|---|
| 19 | `POST /api/chat/reviews/{reviewId}/start` | — | 201 `{_id, reviewId, userId, createdAt, remainingMessagesToday}` | 404 review |
| 20 | `GET /api/chat/sessions/{sessionId}/messages` | — | 200 messages, oldest first | 404 session |
| 21 | `POST /api/chat/sessions/{sessionId}/messages` | `{content}` (1–4000 chars) | 201 `{userMessage, reply, remainingMessagesToday}` | 404 · 422 · 429 limit · 502 AI failed |

All of these require sign-in. A session belongs to exactly one review and one user.

## Flow: ask a question

```
POST /messages ─► session is mine? ──no──► 404
                     │
              review still exists? ──no──► 404
                     │
              charge quota (reset on a new UTC day) ── ≥ 20 today? ──► 429
                     │
              last 6 messages + review context ─► Gemini
                     │
              failed? ──yes──► refund quota ─► 502
                     │
              save question + answer ─► 201
```

## Gemini call

Gemini has no system role, so the conversation is built as:
```
user:  instructions + the code + the review summary
model: "Understood. Ask me about this code."
…the last 6 saved messages…
user:  the new question
```
The model is told to answer only about this code and review.

## Data

| Collection | Fields |
|---|---|
| `chat_sessions` | `review_id`, `user_id` (both indexed), `created_at` |
| `chat_messages` | `session_id` (indexed), `role` (`user` or `model`), `content`, `created_at` |
| quota (on `user_stats`) | `daily_chat_count`, `chat_count_date` |

## Key decisions

| Decision | Why |
|---|---|
| One session per review, reused on `/start` | Reloading the page continues the same conversation |
| Replay only the last 6 messages | Keeps cost and prompt size bounded |
| 20 questions per member per UTC day | Caps AI cost |
| Save both messages only after the AI answers | A failure leaves no unanswered question in the history |
| Refund the quota when the AI fails | Members don't pay for errors that aren't theirs |

## Known gaps

- The quota update is read-then-write, not atomic, so simultaneous requests could slightly exceed 20.
- The 502 `detail` can pass through `ValueError` text (fixed on `feature/forgot-password-qc-fixes`).
