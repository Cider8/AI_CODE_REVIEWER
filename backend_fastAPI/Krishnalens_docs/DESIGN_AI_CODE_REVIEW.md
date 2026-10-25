# Design: AI Code Review

**Feature:** a member submits a snippet, Gemini reviews it, and the result is saved as a review.
**Code:** `app/routes/reviews.py`, `app/utils/gemini.py`, `app/models/review.py`

## API

| # | Method & path | Body / params | Success | Errors |
|---|---|---|---|---|
| 8 | `POST /api/reviews` | `{title?, language, originalCode}` | 201 review | 422 empty code · 502 AI failed |
| 9 | `GET /api/reviews` | `page`, `limit` (1–100), `language?`, `search?` | 200 `{reviews, total, page, pages}` | 422 bad params |
| 10 | `GET /api/reviews/{id}` | — | 200 review | 404 |
| 11 | `DELETE /api/reviews/{id}` | — | 200 `{message}` | 404 |

All of these require sign-in. Another user's review returns 404.

## Flow: create a review

```
POST /reviews ─► build prompt (language + code)
                     │
              Gemini generate ──error──────────► 502 "AI service did not respond"
                     │
              strip ``` fences, json.loads ─fail► 502 "AI response was not valid JSON…"
                     │
              validate AIReviewResult ──fail────► 502
                     │
              save review ─► recompute dashboard stats ─► 201
```
If the AI fails, nothing is saved.

## Gemini call

- Model `gemini-3.6-flash`, one async call per review, no streaming and no retries.
- The prompt asks for **JSON only**, in this shape:
  `summary, overall_score (0–100), bugs[{line, severity, category, description, suggestion}],
  security_issues[{line, type, description, fix}], performance_issues[{description, suggestion, impact}],
  improvements[], refactored_code, complexity{time, space}, tags[]`.
- The reply is checked against `AIReviewResult` (a Pydantic model). Enum values (`severity`, `impact`) and the score range are enforced.

## Data: `reviews` collection

| Field | Notes |
|---|---|
| `user_id` | owner, indexed |
| `title`, `language`, `original_code` | input; the title defaults to `"<language> Review"` |
| `summary`, `overall_score` | AI result |
| `bugs[]`, `security_issues[]`, `performance_issues[]` | embedded objects |
| `improvements[]`, `refactored_code`, `complexity{time, space}`, `tags[]` | AI result |
| `created_at` | list sort key |

## Key decisions

| Decision | Why |
|---|---|
| Force a JSON shape and validate it before saving | Gemini output varies; nothing malformed is ever stored |
| Call the AI before any database write | A failure leaves no half-saved review |
| Search escapes the user's text before using it as a regex | Stops regex injection and slow pathological patterns |
| Deleting a review also removes it from collections, deletes its chat, and recalculates stats | No dangling references; the dashboard stays accurate |

## Known gaps on this branch

- A blocked Gemini reply can surface raw SDK text in the 502 `detail` (fixed on `feature/forgot-password-qc-fixes`).
- There's no limit on how many reviews a member can create per day, so AI cost isn't capped.
