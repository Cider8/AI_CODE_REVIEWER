# CodeLens — Implementation Guide

A detailed walkthrough of how this project is built: architecture, data
model, request flow, and the reasoning behind each design decision. For
setup/run commands and the API table, see [README.md](README.md).

## 1. Architecture Overview

```
React (Vite, port 5173)  <-- JSON/JWT -->  FastAPI (port 8000)  <-->  MongoDB Atlas
                                                  |
                                                  v
                                          Google Gemini API
```

- **Frontend**: React 19 + Vite, React Router for navigation, Recharts for
  dashboard charts, Axios for HTTP (with JWT auto-attached).
- **Backend**: FastAPI + Beanie (async MongoDB ODM built on Motor +
  Pydantic v2).
- **Database**: MongoDB (Atlas in production/dev here), one collection per
  Beanie `Document`: `users`, `reviews`, `user_stats`, `collections`.
- **AI**: Google Gemini (`google-generativeai`), called synchronously inside
  the `POST /api/reviews` request — no background job queue.

## 2. Data Model

| Document | Purpose | Key fields |
|---|---|---|
| `User` | account | `name`, `email` (`EmailStr`, unique index), `password` (bcrypt hash), `preferred_languages` |
| `Review` | one AI review | `user_id`, `original_code`, `language`, AI output: `summary`, `overall_score`, `bugs[]`, `security_issues[]`, `performance_issues[]`, `improvements[]`, `refactored_code`, `complexity`, `tags[]` |
| `UserStats` | per-user rollup, one doc per user | `total_reviews`, `average_score`, `total_bugs_found`, `total_security_issues_found`, `score_history[]`, `language_breakdown[]` |
| `Collection` | user-named group of reviews | `user_id`, `name`, `description`, `review_ids[]` |

`Bug`, `SecurityIssue`, `PerformanceIssue`, `Complexity`, `ScorePoint`, and
`LanguageCount` are embedded sub-models (not separate collections), all
inheriting `CamelModel` so they serialize as camelCase even nested inside a
`Review`.

## 3. Request Flow: Submitting a Review

`POST /api/reviews` (`app/routes/reviews.py::create_review`):

1. `require_db` router dependency checks Mongo is connected (503 if not).
2. `get_current_user` decodes the JWT bearer token, loads the `User`.
3. `analyze_code(code, language)` (`app/utils/gemini.py`) builds a prompt
   that forces Gemini to return **only** a JSON object with a fixed shape
   (summary, score, bugs, security_issues, performance_issues,
   improvements, refactored_code, complexity, tags), strips any ```json
   fences from the response, and parses it into an `AIReviewResult`
   Pydantic model. A `json.JSONDecodeError` is converted into a `ValueError`
   → the route turns that into `HTTPException(502)` — the request fails
   loudly instead of saving a garbage/partial review.
4. A `Review` document is built from the validated AI result and inserted.
5. `_update_stats()` loads the user's `UserStats` doc and updates it in the
   same request: recomputes the running `average_score`, increments
   `total_reviews`/`total_bugs_found`/`total_security_issues_found`, appends
   to `score_history` (for the dashboard's line chart) and
   `language_breakdown` (for the pie chart).
6. The saved `Review` is converted to the `ReviewDetail` response schema via
   `doc_to_schema()` and returned.

## 4. Auth Flow

- **Register/Login** (`app/routes/auth.py`): `User.find_one(User.email == ...)`
  — the `User.email` comparison only works because `init_beanie()` patches
  `Document` subclasses with query-building descriptors at startup (see §6).
  Passwords are hashed with `passlib`'s `bcrypt` scheme; a JWT is minted with
  `sub=<user_id>` and a 7-day expiry (`app/utils/security.py`).
- **Protecting routes**: `get_current_user` (`app/dependencies.py`) is a
  FastAPI dependency that decodes the bearer token via `python-jose` and
  loads the `User` by id, raising `401` on any failure (missing/invalid
  token, user deleted).

## 5. The camelCase Bridge

Python/Mongo naturally use snake_case (`overall_score`), but the existing
React code expects camelCase (`overallScore`). Rather than touch either
side's natural style, every schema inherits `CamelModel`
(`app/schemas/base.py`):

```python
class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,   # overall_score -> overallScore
        populate_by_name=True,      # accepts either name on input
        from_attributes=True,       # can build from a Beanie Document
    )
```

`doc_to_schema()` (`app/utils/convert.py`) is the glue: Beanie Documents
expose `.id`, but response schemas need `_id`/`id` in Mongo style — this
helper bridges the two safely when constructing a schema from a Document.

## 6. Startup, DB Connection, and Graceful Degradation

`app/main.py`'s `lifespan` calls `init_db()` (`app/database.py`), which:

```python
await init_beanie(database=db, document_models=[User, Review, UserStats, Collection])
db_connected = True
```

`init_beanie()` is what turns `User.email` into a queryable expression —
before it succeeds, `User` is just a plain, uninitialized Pydantic-ish
class. If Mongo is unreachable at startup, this call raises; the exception
is caught and logged, and `db_connected` stays `False`.

Every DB-touching router declares `dependencies=[Depends(require_db)]`
(`app/dependencies.py`), which checks that flag and raises a clean
`503 Database unavailable` instead of letting a route crash with a raw
`AttributeError: email` (which is what happened before this was added —
Beanie's query-building magic doesn't exist yet, so `User.email` fails a
plain attribute lookup).

## 7. Frontend Structure

- `App.jsx` — route table: public routes (`/`, `/login`, `/register`) and
  protected routes wrapped in a `<Private>` guard (redirects to `/login` if
  `useAuth()` has no user) plus a shared `<Layout>` (sidebar nav).
- `context/AuthContext.jsx` — holds the logged-in user + JWT, exposes
  `login`/`register`/`logout`.
- `services/api.js` — Axios instance with a request interceptor that
  attaches `Authorization: Bearer <token>`.
- `pages/` — one component per route: `Dashboard` (charts via Recharts),
  `NewReview` (submit code, triggers the AI call), `ReviewDetail` (full
  breakdown), `History` (paginated/searchable list), `Collections`,
  `Profile`.

## 8. Build Order (if replicating this pattern elsewhere)

1. `config.py` — `pydantic-settings` reading `.env`.
2. `models/` — Beanie `Document` classes.
3. `database.py` — Motor client + `init_beanie()`.
4. `schemas/` — Pydantic I/O models on a `CamelModel` base.
5. `utils/security.py` — password hashing + JWT encode/decode.
6. `dependencies.py` — `get_current_user`, `require_db`.
7. `routes/` — one `APIRouter` per resource, DB dependency declared at the
   router level.
8. `utils/gemini.py` (or any external API) — isolated integration module.
9. `main.py` — assemble: `FastAPI()`, CORS, `lifespan`, `include_router(...)`.

## 9. Known Issues / Gaps

- **No automated tests** — nothing under `backend_fastAPI/` or `frontend/`
  currently exercises this behavior; manual testing only so far.
- **MongoDB Atlas + rotating IPs**: if you see
  `SSL: TLSV1_ALERT_INTERNAL_ERROR` at startup, it is Atlas's Network
  Access (IP allow list) rejecting your current public IP — confirmed by
  reproducing the identical failure with a raw `openssl s_client` handshake
  (no pymongo/Python involved) and resolving it by adding the current IP
  (or `0.0.0.0/0` for local dev) in Atlas → Network Access. Networks with
  NAT'd/rotating IPs (e.g. campus WiFi) may need this redone periodically.
- **Gemini failures**: if the model returns non-JSON or a shape that
  doesn't match `AIReviewResult`, the request fails with `502` rather than
  silently saving a partial/garbage review — by design, but there's no
  retry logic yet.
