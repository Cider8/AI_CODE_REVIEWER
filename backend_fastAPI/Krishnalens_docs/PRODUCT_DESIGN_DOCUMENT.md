# KrishnaLens: Product Design Document

| | |
|---|---|
| **Product** | KrishnaLens, an AI code reviewer |
| **Document type** | Product Design Document (technical design) |
| **Version** | 1.1 |
| **Date** | 4 October 2026 |
| **Owner** | Backend Engineer |
| **Companion document** | `PRODUCT_REQUIREMENTS_DOCUMENT.md` describes *what* the product does. This document describes *how* it is built. Requirement IDs (`PR-…`) refer to that document. |

---

## Table of Contents

1. [System Overview](#1-system-overview)
   - 1.1 [Purpose](#11-purpose)
   - 1.2 [Design goals](#12-design-goals)
   - 1.3 [Architecture](#13-architecture)
   - 1.4 [Technology stack](#14-technology-stack)
   - 1.5 [Backend module layout](#15-backend-module-layout)
   - 1.6 [Request lifecycle](#16-request-lifecycle)
2. [Cross-cutting Design](#2-cross-cutting-design)
   - 2.1 [Authentication](#21-authentication)
   - 2.2 [Authorisation and data isolation](#22-authorisation-and-data-isolation)
   - 2.3 [Naming convention (camelCase bridge)](#23-naming-convention-camelcase-bridge)
   - 2.4 [Error model](#24-error-model)
   - 2.5 [Database availability guard](#25-database-availability-guard)
   - 2.6 [CORS and the development proxy](#26-cors-and-the-development-proxy)
   - 2.7 [Configuration](#27-configuration)
3. [API Reference](#3-api-reference)
   - 3.1 [Conventions](#31-conventions)
   - 3.2 [Endpoint summary](#32-endpoint-summary)
   - 3.3 [Shared response objects](#33-shared-response-objects)
   - 3.4 [Health](#34-health)
   - 3.5 [Auth](#35-auth)
   - 3.6 [Reviews](#36-reviews)
   - 3.7 [Stats](#37-stats)
   - 3.8 [Collections](#38-collections)
   - 3.9 [Chat](#39-chat)
4. [Third-party Integrations](#4-third-party-integrations)
   - 4.1 [Google Gemini](#41-google-gemini)
   - 4.2 [MongoDB Atlas](#42-mongodb-atlas)
   - 4.3 [Hosting (Render)](#43-hosting-render)
5. [Data Storage Design](#5-data-storage-design)
   - 5.1 [Overview and relationships](#51-overview-and-relationships)
   - 5.2 [Collection schemas](#52-collection-schemas)
   - 5.3 [Indexes](#53-indexes)
   - 5.4 [Derived data: stats recomputation](#54-derived-data-stats-recomputation)
   - 5.5 [Deletion cascades](#55-deletion-cascades)
6. [Flow Charts](#6-flow-charts)
7. [Security Design](#7-security-design)
8. [Known Limitations and Future Work](#8-known-limitations-and-future-work)
9. [Glossary](#9-glossary)

---

## 1. System Overview

### 1.1 Purpose
KrishnaLens takes a code snippet from a signed-in member, sends it to Google
Gemini with a prompt that forces a structured JSON answer, validates and
stores that answer as a *review*, and keeps per-member statistics, collections
and a follow-up chat per review.

### 1.2 Design goals

| Goal | Design decision |
|---|---|
| Simple to run and deploy | One stateless API process plus a managed database. No queues or workers. |
| Strict per-user isolation | Every query on a user-owned document filters by `user_id`. A document the user doesn't own returns 404. |
| Trustworthy AI output | The AI must return a fixed JSON shape, which is validated by Pydantic before anything is saved. |
| Never half-save | AI calls happen before any write. A failed call writes nothing. |
| Frontend-friendly API | All JSON is camelCase, IDs are returned as `_id`, errors share one `{detail}` shape. |
| Controlled AI cost | A daily chat limit per user, and only the last 6 messages are replayed to the model. |

### 1.3 Architecture

```
 ┌──────────────────────────┐
 │        Browser           │
 │  React 19 single-page    │
 │  app (Vite build)        │
 │  - JWT in localStorage   │
 └────────────┬─────────────┘
              │ HTTPS  /api/*   (Authorization: Bearer <JWT>)
              │ dev: Vite proxy :5173 ──► BACKEND_URL
              ▼
 ┌──────────────────────────────────────────────┐
 │            FastAPI application               │
 │            (uvicorn, Python 3.13)            │
 │                                              │
 │  CORS ─► Router ─► Dependencies ─► Handler   │
 │                    · require_db  (503)       │
 │                    · get_current_user (401)  │
 │                                              │
 │  routes/   auth · reviews · stats ·          │
 │            collections · chat                │
 │  utils/    security · gemini · stats ·       │
 │            convert · time                    │
 └───────┬───────────────────────────┬──────────┘
         │ Motor (async driver)       │ google-generativeai SDK
         │ Beanie ODM                 │ (HTTPS)
         ▼                            ▼
 ┌──────────────────┐        ┌─────────────────────┐
 │  MongoDB Atlas   │        │   Google Gemini     │
 │  db: DB_NAME     │        │   gemini-3.6-flash  │
 │  6 collections   │        │   (review + chat)   │
 └──────────────────┘        └─────────────────────┘
```

### 1.4 Technology stack

| Layer | Technology | Version |
|---|---|---|
| Frontend | React, React Router, Vite, Tailwind CSS v4, Recharts, Axios, lucide-react | React 19, Vite 8 |
| API framework | FastAPI | 0.115.0 |
| ASGI server | uvicorn[standard] | 0.30.6 |
| ODM / driver | Beanie / Motor / PyMongo | 1.27.0 / 3.6.0 / 4.9.2 |
| Validation | Pydantic v2 (+ email), pydantic-settings | 2.9.2 / 2.5.2 |
| Auth | python-jose (JWT), passlib + bcrypt | 3.3.0 / 1.7.4 + 4.0.1 |
| AI | google-generativeai | 0.8.3 |
| Database | MongoDB Atlas (`mongodb+srv`) | managed |

### 1.5 Backend module layout

```
backend_fastAPI/app/
├── main.py            App, lifespan (DB connect/close), CORS, 422 handler, routers
├── config.py          Settings from .env (pydantic-settings)
├── database.py        Motor client + init_beanie, db_connected flag
├── dependencies.py    require_db (503), get_current_user (401)
├── models/            Beanie Documents = MongoDB collections
│   ├── user.py  review.py  stats.py  collection.py  chat.py
├── schemas/           Request/response models (camelCase)
│   ├── base.py (CamelModel)  auth_schema.py  review_schema.py
│   ├── stats_schema.py (stats + collections)  chat_schema.py
├── routes/            One router per resource
│   ├── auth.py  reviews.py  stats.py  collections.py  chat.py
└── utils/
    ├── security.py    bcrypt hashing, JWT create/decode
    ├── gemini.py      Prompts, Gemini calls, response parsing
    ├── stats.py       get_or_create_stats, recompute_stats
    ├── convert.py     doc_to_schema (Document → response model)
    └── time.py        utc_now (naive UTC)
```

### 1.6 Request lifecycle

```
 request ─► CORS middleware
         ─► route match (404 if none)
         ─► router dependency: require_db ──── DB not connected? ──► 503
         ─► body / path validation ────────── invalid? ───────────► 422 (sanitised)
         ─► get_current_user ──────────────── bad/missing token? ─► 401
         ─► handler: ownership-filtered queries ── not found? ───► 404
         ─► (optional) Gemini call ───────────── failed? ─────────► 502
         ─► response model → camelCase JSON ──────────────────────► 2xx
```

---

## 2. Cross-cutting Design

### 2.1 Authentication
- **Scheme:** HTTP Bearer JWT, signed with HS256 using `JWT_SECRET`.
- **Claims:** `sub` = the user's ObjectId as a string, `exp` = issue time + `JWT_EXPIRE_DAYS` (7).
- **Issued by:** `POST /api/auth/register` and `POST /api/auth/login`.
- **Stored by the client:** `localStorage["token"]`. An Axios interceptor adds `Authorization: Bearer <token>` to every request. On a 401 the client deletes the token and redirects to `/login`. **Exception:** a 401 from `POST /api/auth/login` (#3) means wrong credentials, so the client shows `detail` and stays on the page. The only endpoint that returns 401 for wrong credentials is #3; every other 401 means the session is invalid.
- **Validation (`get_current_user`):** a missing header, a non-Bearer scheme, a bad signature or expiry, a `sub` that isn't a valid ObjectId, or a user that no longer exists all return **401**. A missing header returns 401, not FastAPI's default 403, because the client only reacts to 401.
- **Passwords:** hashed with bcrypt through passlib `CryptContext`. Plaintext is never stored or logged.
- **Password policy** (`check_password_rules`): at least 8 characters, 1 uppercase letter, 1 lowercase letter, and 1 character from `!@#$%^&+=[]{}|;:,.<>?`. All failed rules are reported together, joined by `"; "`.
- **No server-side sessions:** logout is client-side (the token is discarded). Tokens can't be revoked before they expire.

### 2.2 Authorisation and data isolation
- Every user-owned document carries `user_id`. Lookups always combine the ID with the owner:
  `find_one(Model.id == id, Model.user_id == current_user.id)`.
- A document that is missing and a document owned by someone else both return **404** with the same message, so the API doesn't reveal whether the ID exists.
- Chat messages have no `user_id`. Access goes through their session, whose `user_id` is checked first.

### 2.3 Naming convention (camelCase bridge)
Python and MongoDB use snake_case (`overall_score`). The React client expects camelCase (`overallScore`).
All schemas inherit from `CamelModel` (`alias_generator=to_camel`, `populate_by_name=True`):
- **Output** is always camelCase.
- **Input** accepts both camelCase and snake_case.
- **IDs** are exposed as `_id` (alias), never `id`.

### 2.4 Error model
Every error body is `{"detail": ...}`.

| Status | When | `detail` |
|---|---|---|
| 400 | Business-rule violation, including a wrong current password on #6 | string, e.g. `"Email already in use"` |
| 401 | Not authenticated (missing/invalid/expired token), or wrong credentials on login (#3) only | string |
| 404 | Unknown route, or a resource that is missing or not owned | string |
| 422 | Request validation failed | array of `{type, loc, msg}` |
| 429 | Daily chat limit reached | string |
| 502 | AI provider failed (any error, including timeouts) or returned an invalid answer | string |
| 503 | Database not connected | `"Database unavailable"` |
| 500 | Unexpected server error | plain text |

**422 sanitisation.** A custom `RequestValidationError` handler returns only
`type`, `loc` and `msg`. FastAPI's default `input` and `ctx` fields are
removed so rejected values (e.g. a plaintext password) are never echoed back.

```json
{
  "detail": [
    { "type": "value_error", "loc": ["body", "password"],
      "msg": "Value error, Password must be at least 8 characters; Password must contain at least one special character" }
  ]
}
```

### 2.5 Database availability guard
If MongoDB is unreachable at startup, the app still starts (the error is
logged) and `db_connected` stays `False`. Every resource router declares the
`require_db` dependency, so those routes fail fast with **503 "Database
unavailable"** instead of crashing. `GET /` still works.

### 2.6 CORS and the development proxy
- CORS allows only `FRONTEND_URL` (default `http://localhost:5173`), with credentials, all methods and all headers.
- In development the client calls the relative path `/api`. Vite proxies it to `BACKEND_URL` from `frontend/.env`, which points at the Render deployment. To test against a local backend, set `BACKEND_URL=http://localhost:8000` for that Vite process only: either in its environment (current practice, a separate Vite on :5174) or in an optional `frontend/.env.local`. The project owner hasn't decided yet whether to create `.env.local`.

### 2.7 Configuration

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `MONGO_URI` | no | `mongodb://localhost:27017` | MongoDB connection string |
| `DB_NAME` | no | `ai_code_reviewer` | Database name |
| `JWT_SECRET` | **yes** | — | HMAC key for JWTs |
| `JWT_ALGORITHM` | no | `HS256` | JWT algorithm |
| `JWT_EXPIRE_DAYS` | no | `7` | Token lifetime |
| `GEMINI_API_KEY` | **yes** | — | Google AI Studio key |
| `FRONTEND_URL` | no | `http://localhost:5173` | Allowed CORS origin |

The app won't start if a required variable is missing.

---

## 3. API Reference

### 3.1 Conventions
- Base URL: `<host>/api`. Content type: `application/json`.
- 🔒 = requires `Authorization: Bearer <JWT>`.
- Every route except `GET /` also returns **503** when the database is down.
- Every 🔒 route also returns **401** for a missing or invalid token.
- Any path parameter that is an ObjectId must be a 24-character hex string, otherwise **422**.
- Timestamps are ISO-8601 UTC without a timezone suffix, e.g. `"2026-10-04T09:15:30.123000"`.

### 3.2 Endpoint summary

| # | Method | Path | Auth | Purpose | Success |
|---|---|---|---|---|---|
| 1 | GET | `/` | – | Health / welcome | 200 |
| 2 | POST | `/api/auth/register` | – | Create account | 201 |
| 3 | POST | `/api/auth/login` | – | Sign in | 200 |
| 4 | GET | `/api/auth/me` | 🔒 | Current user | 200 |
| 5 | PATCH | `/api/auth/profile` | 🔒 | Update name / preferred languages | 200 |
| 6 | PATCH | `/api/auth/password` | 🔒 | Change password | 200 |
| 7 | DELETE | `/api/auth/account` | 🔒 | Delete account and all data | 200 |
| 8 | POST | `/api/reviews` | 🔒 | Submit code for AI review | 201 |
| 9 | GET | `/api/reviews` | 🔒 | List / search / filter reviews | 200 |
| 10 | GET | `/api/reviews/{reviewId}` | 🔒 | Get one review | 200 |
| 11 | DELETE | `/api/reviews/{reviewId}` | 🔒 | Delete review (+ clean-up) | 200 |
| 12 | GET | `/api/stats` | 🔒 | Dashboard data | 200 |
| 13 | POST | `/api/collections` | 🔒 | Create collection | 201 |
| 14 | GET | `/api/collections` | 🔒 | List collections | 200 |
| 15 | PATCH | `/api/collections/{collectionId}` | 🔒 | Rename / edit description | 200 |
| 16 | PATCH | `/api/collections/{collectionId}/add-review` | 🔒 | Add review to collection | 200 |
| 17 | PATCH | `/api/collections/{collectionId}/remove-review` | 🔒 | Remove review from collection | 200 |
| 18 | DELETE | `/api/collections/{collectionId}` | 🔒 | Delete collection | 200 |
| 19 | POST | `/api/chat/reviews/{reviewId}/start` | 🔒 | Open / resume chat for a review | 201 |
| 20 | GET | `/api/chat/sessions/{sessionId}/messages` | 🔒 | Chat history | 200 |
| 21 | POST | `/api/chat/sessions/{sessionId}/messages` | 🔒 | Ask a question | 201 |

### 3.3 Shared response objects

**UserOut**
```json
{ "_id": "66fe…a1", "name": "Priya", "email": "priya@example.com",
  "avatar": null, "preferredLanguages": ["Python"], "createdAt": "2026-10-04T09:15:30" }
```

**ReviewListItem** (used in lists, dashboard and collections)
```json
{ "_id": "66fe…b2", "title": "Binary Search", "language": "Python",
  "overallScore": 78, "createdAt": "2026-10-04T09:20:00" }
```

**ReviewDetail**
```json
{
  "_id": "66fe…b2", "userId": "66fe…a1", "title": "Binary Search",
  "originalCode": "def bs(a, x): …", "language": "Python",
  "summary": "Correct overall, but …", "overallScore": 78,
  "bugs": [ { "line": 4, "category": "Off-by-one error", "severity": "medium",
              "description": "…", "suggestion": "…" } ],
  "securityIssues": [ { "line": null, "type": "Hardcoded Secret", "description": "…", "fix": "…" } ],
  "performanceIssues": [ { "description": "…", "suggestion": "…", "impact": "low" } ],
  "improvements": ["…"], "refactoredCode": "…",
  "complexity": { "time": "O(log n)", "space": "O(1)" },
  "tags": ["searching", "arrays"], "createdAt": "2026-10-04T09:20:00"
}
```
`severity` ∈ `low|medium|high|critical`. `impact` ∈ `low|medium|high`. `category` is optional; reviews created before it was added don't have it.

**CollectionOut**
```json
{ "_id": "66fe…c3", "userId": "66fe…a1", "name": "DSA Practice",
  "description": "Interview prep", "reviewIds": [ /* ReviewListItem[] */ ],
  "createdAt": "2026-10-04T10:00:00" }
```
Note: `reviewIds` holds populated **ReviewListItem objects**, not plain IDs. IDs whose review no longer exists are left out.

**ChatMessageOut**
```json
{ "_id": "66fe…d4", "sessionId": "66fe…e5", "role": "user", "content": "Why is line 4 wrong?",
  "createdAt": "2026-10-04T10:05:00" }
```
`role` ∈ `user|model`.

---

### 3.4 Health

#### `GET /`
| | |
|---|---|
| Request | — |
| 200 | `{"message": "Welcome to KrishnaLens AI Code Review API"}` |

---

### 3.5 Auth

#### `POST /api/auth/register`
Request:
```json
{ "name": "Priya", "email": "priya@example.com", "password": "Password#1" }
```
| Status | Body |
|---|---|
| **201** | `{ "token": "<JWT>", "user": UserOut }` |
| 400 | `"Email already in use"` |
| 422 | Invalid email; password rule failures (all listed in one `msg`, see §2.4); missing fields |

#### `POST /api/auth/login`
Request: `{ "email": "priya@example.com", "password": "Password#1" }`

| Status | Body |
|---|---|
| **200** | `{ "token": "<JWT>", "user": UserOut }` |
| 401 | `"Invalid email or password"` (same for unknown email and wrong password) |
| 422 | Malformed email / missing fields |

#### `GET /api/auth/me` 🔒
| Status | Body |
|---|---|
| **200** | `UserOut` (not wrapped) |
| 401 | `"Not authenticated"` / `"Token invalid or expired"` / `"User not found"` |

#### `PATCH /api/auth/profile` 🔒
Request (all optional, at least one): `{ "name": "Priya S", "preferredLanguages": ["Python","Go"] }`

| Status | Body |
|---|---|
| **200** | `UserOut` |
| 400 | `"Nothing to update"` (empty body or all values null) |

A blank `name` is ignored. It is not saved, and it is not an error.

#### `PATCH /api/auth/password` 🔒
Request: `{ "currentPassword": "Password#1", "newPassword": "NewPass#22" }`

| Status | Body |
|---|---|
| **200** | `{ "message": "Password updated successfully" }` |
| 400 | `"Current password is incorrect"` (400, not 401: the caller is authenticated) |
| 422 | `newPassword` rule failures |

Existing tokens stay valid after a password change.

#### `DELETE /api/auth/account` 🔒
| Status | Body |
|---|---|
| **200** | `{ "message": "Account deleted successfully" }` |

Deletes chat messages, chat sessions, reviews, stats, collections and the user (§5.5).

---

### 3.6 Reviews

#### `POST /api/reviews` 🔒
Request:
```json
{ "title": "Binary Search", "language": "Python", "originalCode": "def bs(a, x): …" }
```
`title` is optional and defaults to `"<language> Review"`. `originalCode` must be at least 1 character.

| Status | Body |
|---|---|
| **201** | `ReviewDetail` |
| 422 | Empty `originalCode` / missing `language` |
| 502 | `"AI response was not valid JSON: …"`, a validation message when the AI's JSON has the wrong shape, or `"AI service did not respond"` for provider/transport errors. The client shows its own fixed message for every 502. |

Side effects: inserts the review and recalculates the user's stats.

#### `GET /api/reviews` 🔒
Query parameters:

| Param | Type | Default | Rule |
|---|---|---|---|
| `page` | int | 1 | ≥ 1 |
| `limit` | int | 10 | 1–100 |
| `language` | string | — | exact match |
| `search` | string | — | case-insensitive substring of `title` (regex-escaped) |

| Status | Body |
|---|---|
| **200** | `{ "reviews": ReviewListItem[], "total": 42, "page": 1, "pages": 5 }`, sorted newest first. `pages` = ceil(total/limit), and 0 when there are no reviews. |
| 422 | Out-of-range `page` / `limit` |

#### `GET /api/reviews/{reviewId}` 🔒
| Status | Body |
|---|---|
| **200** | `ReviewDetail` |
| 404 | `"Review not found"` |

#### `DELETE /api/reviews/{reviewId}` 🔒
| Status | Body |
|---|---|
| **200** | `{ "message": "Review deleted" }` |
| 404 | `"Review not found"` |

Side effects: removes the ID from the user's collections, deletes the review's chat session and messages, deletes the review, and recalculates stats.

---

### 3.7 Stats

#### `GET /api/stats` 🔒
| Status | Body |
|---|---|
| **200** | see below |

```json
{
  "stats": {
    "_id": "…", "userId": "…",
    "totalReviews": 12, "averageScore": 71.25,
    "totalBugsFound": 30, "totalSecurityIssuesFound": 6,
    "scoreHistory": [ { "score": 64, "date": "2026-09-30T08:00:00" } ],
    "languageBreakdown": [ { "language": "Python", "count": 8 } ],
    "commonWeaknesses": ["Off-by-one error", "SQL Injection"],
    "updatedAt": "…"
  },
  "recentReviews": [ /* up to 5 ReviewListItem, newest first */ ]
}
```
The stats document is created on demand if it doesn't exist. Chat-quota fields are stored but not returned.

---

### 3.8 Collections

#### `POST /api/collections` 🔒
Request: `{ "name": "DSA Practice", "description": "optional" }`

| Status | Body |
|---|---|
| **201** | `CollectionOut` (with empty `reviewIds`) |
| 422 | Missing `name` |

#### `GET /api/collections` 🔒
| Status | Body |
|---|---|
| **200** | `CollectionOut[]` |

#### `PATCH /api/collections/{collectionId}` 🔒
Request (at least one): `{ "name": "New name", "description": "" }`

| Status | Body |
|---|---|
| **200** | `CollectionOut` |
| 400 | `"Nothing to update"` / `"Collection name cannot be empty"` |
| 404 | `"Collection not found"` |

An empty `description` clears it.

#### `PATCH /api/collections/{collectionId}/add-review` 🔒
Request: `{ "reviewId": "66fe…b2" }`

| Status | Body |
|---|---|
| **200** | `CollectionOut` (idempotent: adding twice has no effect) |
| 404 | `"Collection not found"` / `"Review not found"` (both must be the caller's) |

#### `PATCH /api/collections/{collectionId}/remove-review` 🔒
Request: `{ "reviewId": "66fe…b2" }`

| Status | Body |
|---|---|
| **200** | `CollectionOut` (idempotent: removing an ID that isn't there has no effect) |
| 404 | `"Collection not found"` |

The review itself isn't looked up, so dead IDs can still be cleared.

#### `DELETE /api/collections/{collectionId}` 🔒
| Status | Body |
|---|---|
| **200** | `{ "message": "Collection deleted" }` |
| 404 | `"Collection not found"` |

The reviews themselves are not deleted.

---

### 3.9 Chat

#### `POST /api/chat/reviews/{reviewId}/start` 🔒
Request: no body.

| Status | Body |
|---|---|
| **201** | `{ "_id", "reviewId", "userId", "createdAt", "remainingMessagesToday": 17 }` |
| 404 | `"Review not found"` |

Returns the existing session for (review, user) if there is one, so a reload resumes the same conversation. Returns 201 even when an existing session is reused.

#### `GET /api/chat/sessions/{sessionId}/messages` 🔒
| Status | Body |
|---|---|
| **200** | `ChatMessageOut[]`, oldest first |
| 404 | `"Chat session not found"` |

#### `POST /api/chat/sessions/{sessionId}/messages` 🔒
Request: `{ "content": "Why is line 4 an off-by-one?" }` (1–4000 characters)

| Status | Body |
|---|---|
| **201** | `{ "userMessage": ChatMessageOut, "reply": ChatMessageOut, "remainingMessagesToday": 16 }` |
| 404 | `"Chat session not found"` / `"Review for this session no longer exists"` |
| 422 | Empty or over-length `content` |
| 429 | `"Daily chat limit of 20 messages reached"` |
| 502 | `"AI returned an empty response"` / `"AI service did not respond"` (the quota is refunded) |

---

## 4. Third-party Integrations

### 4.1 Google Gemini

| Item | Detail |
|---|---|
| Provider | Google AI (Gemini API) |
| SDK | `google-generativeai` 0.8.3 |
| Model | `gemini-3.6-flash` |
| Auth | `GEMINI_API_KEY`, set once at import via `genai.configure(api_key=…)` |
| Call style | Async (`generate_content_async`), one request per user action, no streaming |
| Timeouts / retries | SDK defaults; no app-level retry |
| Data sent | The user's code, its language, the review summary, and up to 6 prior chat messages |
| Called from | `app/utils/gemini.py` → `analyze_code()` and `chat_about_review()` |

#### 4.1.1 Code review: `analyze_code(code, language)`
1. **Prompt.** A single text prompt casts the model as an expert reviewer for that language, embeds the code in a fenced block, and demands *"Respond ONLY with a valid JSON object in this exact structure"*:
   ```json
   {
     "summary": "2-3 sentences", "overall_score": 0-100,
     "bugs": [{ "line", "severity", "category", "description", "suggestion" }],
     "security_issues": [{ "line", "type", "description", "fix" }],
     "performance_issues": [{ "description", "suggestion", "impact" }],
     "improvements": ["…"], "refactored_code": "…",
     "complexity": { "time": "O(?)", "space": "O(?)" }, "tags": ["…"]
   }
   ```
2. **Parsing.** Strip any ```` ```json ```` / ```` ``` ```` fences, run `json.loads`, then validate with the `AIReviewResult` Pydantic model (score must be 0–100; severity, impact and type values are constrained).
3. **Failure mapping.** A JSON decode error or a schema validation error raises `ValueError`, and the route returns **502**. Nothing is persisted.

#### 4.1.2 Review chat: `chat_about_review(code, language, summary, history, question)`
1. Gemini has no system role, so the context (instructions, code, summary) is the **first user turn**, followed by a fixed model turn: *"Understood. Ask me about this code."*
2. Then come the last `HISTORY_LIMIT = 6` stored messages (oldest first), then the new question.
3. An empty reply raises `ValueError`. **Any** exception is caught by the route, which refunds the quota and returns **502**.

```
contents = [
  {role:"user",  parts:[CONTEXT(code, language, summary)]},
  {role:"model", parts:["Understood. Ask me about this code."]},
  …last 6 messages {role:"user"|"model", parts:[content]}…,
  {role:"user",  parts:[question]}
]
```

#### 4.1.3 Cost and abuse controls
- 20 chat messages per user per UTC day (`DAILY_CHAT_LIMIT`). The count is stored on `user_stats`.
- History replay is capped at 6 messages.
- One model call per review and per chat question.
- Code review has no limit yet (see §8).

### 4.2 MongoDB Atlas
- Accessed through Motor's async client, `AsyncIOMotorClient(MONGO_URI)`, with Beanie on top.
- `init_beanie` registers the 6 document models and creates the declared indexes on startup.
- The connection pool is closed on shutdown (`close_db`).
- **Note:** the local development `.env` and the Render deployment both use Atlas connection strings. Treat local testing as touching real data unless a separate database is set up.

### 4.3 Hosting (Render)
- The backend is deployed as a web service on Render (`ai-code-reviewer-mevv.onrender.com`).
- The frontend dev proxy targets it by default (`frontend/.env` → `BACKEND_URL`).
- Render runs the **committed** code, so local changes take effect there only after commit and deploy.

---

## 5. Data Storage Design

### 5.1 Overview and relationships

```
                   ┌──────────────┐
                   │    users     │
                   └──────┬───────┘
          1:1             │ 1:N            1:N
   ┌──────────────┐       │        ┌──────────────┐
   │  user_stats  │◄──────┼───────►│ collections  │
   └──────────────┘       │        └──────┬───────┘
                          ▼               │ review_ids[] (N:M, by reference)
                   ┌──────────────┐       │
                   │   reviews    │◄──────┘
                   └──────┬───────┘
                          │ 1:1 per (review, user)
                   ┌──────▼───────┐
                   │chat_sessions │
                   └──────┬───────┘
                          │ 1:N
                   ┌──────▼───────┐
                   │chat_messages │
                   └──────────────┘
```

MongoDB has no foreign keys. References are stored ObjectIds, and the code
resolves them (Beanie has no automatic populate). Bugs, security issues,
performance issues, complexity, score points and language counts are
**embedded** subdocuments.

### 5.2 Collection schemas

All documents have `_id: ObjectId`. Dates are naive UTC (`utc_now()`).

#### `users`
| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `name` | string | ✔ | | |
| `email` | string (email) | ✔ | | **unique** |
| `password` | string | ✔ | | bcrypt hash |
| `avatar` | string \| null | | null | not used by the UI yet |
| `preferred_languages` | string[] | | [] | |
| `created_at` | date | | now | |

#### `reviews`
| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `user_id` | ObjectId | ✔ | | owner, **indexed** |
| `title` | string | | `"Untitled Review"` | route sets `"<language> Review"` |
| `original_code` | string | ✔ | | |
| `language` | string | ✔ | | |
| `summary` | string \| null | | null | |
| `overall_score` | int 0–100 \| null | | null | |
| `bugs` | Bug[] | | [] | embedded |
| `security_issues` | SecurityIssue[] | | [] | embedded |
| `performance_issues` | PerformanceIssue[] | | [] | embedded |
| `improvements` | string[] | | [] | |
| `refactored_code` | string \| null | | null | |
| `complexity` | {time, space} \| null | | null | embedded |
| `tags` | string[] | | [] | |
| `created_at` | date | | now | sort key |

Embedded types:

| Type | Fields |
|---|---|
| Bug | `line` int\|null · `category` string\|null · `severity` low/medium/high/critical · `description` · `suggestion` |
| SecurityIssue | `line` int\|null · `type` · `description` · `fix` |
| PerformanceIssue | `description` · `suggestion` · `impact` low/medium/high |
| Complexity | `time` · `space` |

#### `user_stats`
| Field | Type | Default | Notes |
|---|---|---|---|
| `user_id` | ObjectId | | **unique** |
| `total_reviews` | int | 0 | derived |
| `average_score` | float | 0.0 | derived, 2 decimal places |
| `total_bugs_found` | int | 0 | derived |
| `total_security_issues_found` | int | 0 | derived |
| `score_history` | {score, date}[] | [] | derived, one per review, oldest first |
| `language_breakdown` | {language, count}[] | [] | derived, most used first |
| `common_weaknesses` | string[] | [] | derived, ≤ 5 |
| `updated_at` | date | now | |
| `daily_chat_count` | int | 0 | chat quota counter |
| `chat_count_date` | date | today (UTC) | day the counter belongs to |

#### `collections`
| Field | Type | Default | Notes |
|---|---|---|---|
| `user_id` | ObjectId | | owner, **indexed** |
| `name` | string | | |
| `description` | string \| null | null | |
| `review_ids` | ObjectId[] | [] | references to `reviews` |
| `created_at` | date | now | |
| `updated_at` | date | now | set on add/remove/rename |
| `is_archived` | bool | false | reserved, not exposed |

#### `chat_sessions`
| Field | Type | Notes |
|---|---|---|
| `review_id` | ObjectId | **indexed** |
| `user_id` | ObjectId | **indexed** |
| `created_at` | date | |

#### `chat_messages`
| Field | Type | Notes |
|---|---|---|
| `session_id` | ObjectId | **indexed** |
| `role` | `"user"` \| `"model"` | |
| `content` | string | ≤ 4000 for user messages |
| `created_at` | date | sort key |

### 5.3 Indexes

| Collection | Index | Purpose |
|---|---|---|
| users | `email` (unique) | Login lookup; stops duplicate sign-ups even under a race |
| reviews | `user_id` | Every list or lookup is per user |
| user_stats | `user_id` (unique) | One stats document per user; race-safe creation |
| collections | `user_id` | Per-user listing |
| chat_sessions | `review_id`, `user_id` | Find or resume the session for a review |
| chat_messages | `session_id` | Load the transcript |

### 5.4 Derived data: stats recomputation
`recompute_stats(user_id)` loads all of the user's reviews and rebuilds every
review-derived field. It runs after **every review create and delete**, so the
dashboard always reflects the reviews the user currently has. Chat-quota fields
are not touched.

```
reviews (sorted by created_at)
  ├─► total_reviews        = count
  ├─► average_score        = round(mean(overall_score or 0), 2)
  ├─► total_bugs_found     = Σ len(bugs)
  ├─► total_security_...   = Σ len(security_issues)
  ├─► score_history        = [(score, created_at)] oldest → newest
  ├─► language_breakdown   = counts per language, most used first
  └─► common_weaknesses    = labels from bug.category ∪ security_issue.type,
                             normalised (case/space), counted once per review,
                             kept if seen in ≥ 2 reviews, top 5
```
Cost is O(number of the user's reviews) per write. That is fine at current scale; see §8.

### 5.5 Deletion cascades

| Action | Removes |
|---|---|
| Delete review | the review ID from the user's collections (`$pull`) → the session's chat messages → the chat session → the review → then stats are recalculated |
| Delete collection | the collection only (reviews are kept) |
| Delete account | chat messages → chat sessions → reviews → user_stats → collections → user |

Cascades run as sequential operations without a transaction, so a crash
partway through can leave orphans (see §8).

---

## 6. Flow Charts

### 6.1 Register: `POST /api/auth/register`
```
Client ──► POST /register {name, email, password}
             │
             ▼
     DB connected? ──no──► 503
             │yes
             ▼
     Body valid? (email format, password rules) ──no──► 422 (all failed rules)
             │yes
             ▼
     Email already exists? ──yes──► 400 "Email already in use"
             │no
             ▼
     Hash password (bcrypt) → insert user
             │
       DuplicateKeyError? (race) ──yes──► 400 "Email already in use"
             │no
             ▼
     Create empty user_stats
             │
             ▼
     Sign JWT (sub=userId, exp=+7d)
             │
             ▼
     201 {token, user}
```

### 6.2 Login: `POST /api/auth/login`
```
Client ──► POST /login {email, password}
             │
             ▼
     Find user by email ──none──┐
             │found             │
             ▼                  ▼
     bcrypt verify ──fail──► 401 "Invalid email or password"
             │ok
             ▼
     Sign JWT ──► 200 {token, user}
```

### 6.3 Authenticated request guard (all 🔒 routes)
```
Request ──► Authorization header present & "Bearer"? ──no──► 401 "Not authenticated"
                │yes
                ▼
        Decode JWT (signature, exp) ──fail──► 401 "Token invalid or expired"
                │ok
                ▼
        sub is a valid ObjectId? ──no──► 401 "Token invalid or expired"
                │yes
                ▼
        Load user ──missing──► 401 "User not found"
                │
                ▼
        current_user ──► route handler
```

### 6.4 Me / profile / password
```
GET /me ──► guard ──► 200 UserOut

PATCH /profile ──► guard ──► any non-null field? ──no──► 400 "Nothing to update"
                                   │yes
                                   ▼
                        drop blank name → save user → 200 UserOut

PATCH /password ──► guard ──► newPassword passes rules? ──no──► 422
                                   │yes
                                   ▼
                     bcrypt verify currentPassword ──fail──► 400
                                   │ok
                                   ▼
                     hash + save ──► 200 {message}
```

### 6.5 Delete account: `DELETE /api/auth/account`
```
guard ──► find user's chat sessions
            │
            ▼
      delete chat_messages (session_id ∈ sessions)
            │
            ▼
      delete chat_sessions ──► delete reviews ──► delete user_stats
            │
            ▼
      delete collections ──► delete user ──► 200 {message}
            │
   (client discards JWT and redirects)
```

### 6.6 Create review: `POST /api/reviews`
```
Client ──► POST /reviews {title?, language, originalCode}
             │
             ▼
     guard ──► body valid? ──no──► 422
             │yes
             ▼
     Build prompt ──► Gemini generate_content_async ──error──► 502 "AI service did not respond"
             │
             ▼
     Strip ``` fences ──► json.loads ──fail──► 502 "AI response was not valid JSON"
             │ok
             ▼
     Validate AIReviewResult ──fail──► 502
             │ok
             ▼
     Insert review (title default "<language> Review")
             │
             ▼
     recompute_stats(user)
             │
             ▼
     201 ReviewDetail
```

### 6.7 List reviews: `GET /api/reviews`
```
guard ──► query = reviews where user_id = me
            │
            ├─ language? ──► AND language = ?
            ├─ search?   ──► AND title ~ /escape(search)/i
            ▼
      total = count(query)
            │
            ▼
      sort created_at desc → skip (page-1)*limit → limit
            │
            ▼
      200 {reviews, total, page, pages=ceil(total/limit)}
```

### 6.8 Get review: `GET /api/reviews/{id}`
```
guard ──► find review (id AND user_id = me) ──none──► 404 "Review not found"
                     │found
                     ▼
               200 ReviewDetail
```

### 6.9 Delete review: `DELETE /api/reviews/{id}`
```
guard ──► find review (id AND owner) ──none──► 404
            │found
            ▼
      $pull id from user's collections.review_ids
            │
            ▼
      find chat sessions for review ──► delete their messages ──► delete sessions
            │
            ▼
      delete review ──► recompute_stats(user) ──► 200 {message}
```

### 6.10 Dashboard: `GET /api/stats`
```
guard ──► get_or_create user_stats
            │
            ▼
      5 newest reviews of user
            │
            ▼
      200 {stats, recentReviews}
```

### 6.11 Collections
```
POST   /collections            guard ─► insert {name, description} ─► 201 CollectionOut

GET    /collections            guard ─► find by user ─► for each: fetch reviews in review_ids
                                                       ─► 200 CollectionOut[]

PATCH  /collections/{id}       guard ─► owned collection? ─no─► 404
                                         │yes
                                         ▼
                               any field? ─no─► 400 "Nothing to update"
                                         │
                               name given & blank? ─yes─► 400 "...cannot be empty"
                                         │
                               apply name/description, updated_at ─► 200

PATCH  /{id}/add-review        guard ─► owned collection? ─no─► 404 "Collection not found"
                                         │
                               owned review? ─no─► 404 "Review not found"
                                         │
                               already in list? ─yes─► (no change)
                                         │no
                               append + updated_at ─► 200 CollectionOut

PATCH  /{id}/remove-review     guard ─► owned collection? ─no─► 404
                                         │
                               id in list? ─yes─► remove + updated_at
                                         │
                                         ▼
                               200 CollectionOut

DELETE /collections/{id}       guard ─► owned collection? ─no─► 404
                                         │
                               delete collection (reviews kept) ─► 200
```

### 6.12 Start chat: `POST /api/chat/reviews/{reviewId}/start`
```
guard ──► owned review? ──no──► 404 "Review not found"
            │yes
            ▼
      session for (review, user) exists? ──yes──► reuse
            │no
            ▼
      insert new session
            │
            ▼
      remaining = day rolled over ? 20 : 20 - daily_chat_count
            │
            ▼
      201 {session…, remainingMessagesToday}
```

### 6.13 Get messages: `GET /api/chat/sessions/{id}/messages`
```
guard ──► session exists AND session.user_id = me? ──no──► 404
            │yes
            ▼
      messages by session_id, created_at asc ──► 200 ChatMessageOut[]
```

### 6.14 Send message: `POST /api/chat/sessions/{id}/messages`
```
guard ──► content 1..4000? ──no──► 422
            │
            ▼
      owned session? ──no──► 404 "Chat session not found"
            │
            ▼
      review still exists? ──no──► 404 "Review for this session no longer exists"
            │
            ▼
      ┌── consume quota ─────────────────────────────┐
      │ new UTC day? → reset counter to 0            │
      │ counter ≥ 20? ──yes──► 429                   │
      │ counter += 1, save                           │
      └──────────────────────────────────────────────┘
            │
            ▼
      load last 6 messages (oldest first)
            │
            ▼
      Gemini chat(context + history + question)
            │
        failed? ──yes──► refund quota (same day) ──► 502
            │no
            ▼
      insert user message, insert model reply
            │
            ▼
      201 {userMessage, reply, remainingMessagesToday}
```

### 6.15 Startup and database guard
```
uvicorn start ──► lifespan: init_db()
                     │
          Atlas reachable? ──no──► log error, db_connected = False
                     │yes             (app still serves; resource routes → 503)
                     ▼
          init_beanie(6 models, create indexes) → db_connected = True
                     │
                     ▼
               serve requests ──► shutdown: close Motor client
```

---

## 7. Security Design

| Threat | Mitigation |
|---|---|
| Password theft from DB | bcrypt hashes only |
| Passwords echoed in errors | 422 handler removes `input`/`ctx` (§2.4) |
| Account enumeration | Same login error for unknown email and wrong password. Not-owned resources return 404. |
| Cross-user data access | Owner filter on every query; chat access goes through the session owner |
| Regex injection / ReDoS in search | `re.escape` on `search` |
| Duplicate accounts under a race | Unique index on `users.email`, and `DuplicateKeyError` mapped to 400 |
| Cross-origin abuse | CORS limited to `FRONTEND_URL` |
| AI cost abuse via chat | Daily quota and capped history |
| Malformed AI output stored | Strict schema validation before insert |
| Secrets in source | `.env` only. `.env.example` lists keys without values. |

---

## 8. Known Limitations and Future Work

| # | Item | Impact | Suggested direction |
|---|---|---|---|
| L1 | ~~Gemini provider errors on review creation surfaced as 500~~ **Fixed in v1.1:** now 502 | — | — |
| L2 | No rate limit on review creation | AI cost exposure | Daily review quota similar to chat |
| L3 | No timeout or retry around Gemini calls | Requests can hang on provider slowness | Request timeout plus one retry with backoff |
| L4 | Cascading deletes aren't transactional | Rare orphans after a crash | MongoDB multi-document transactions (Atlas replica set supports them) |
| L5 | `recompute_stats` is O(n) per write | Slower writes for heavy users | Incremental updates or an aggregation pipeline |
| L6 | JWTs can't be revoked; a password change doesn't invalidate old tokens | Stolen token valid up to 7 days | Token version on the user, checked in `get_current_user` |
| L7 | Token stored in `localStorage` | XSS could read it | httpOnly cookie plus CSRF protection |
| L8 | `reviewIds` on collections returns objects, not IDs | Confusing name | Rename (breaking change: coordinate with the frontend) |
| L9 | `POST /chat/.../start` returns 201 even when reusing a session | Minor HTTP semantics | 200 on reuse |
| L10 | No automated tests | Regressions | pytest + a test database; contract tests for §3 |
| L11 | Local development uses the Atlas cluster | Test data mixes with real data | Separate dev database (`DB_NAME`) or local MongoDB |

---

## 9. Glossary

| Term | Meaning |
|---|---|
| **ODM** | Object-Document Mapper. Beanie maps Python classes to MongoDB collections. |
| **JWT** | JSON Web Token. A signed token proving who the caller is. |
| **Bearer token** | A token sent as `Authorization: Bearer <token>`. |
| **ObjectId** | MongoDB's 12-byte ID, shown as 24 hex characters. |
| **CORS** | Cross-Origin Resource Sharing: browser rules for which sites may call the API. |
| **Lifespan** | FastAPI startup/shutdown hook used to connect and disconnect the DB. |
| **Idempotent** | Repeating the request gives the same result as doing it once. |
| **Cascade** | Deleting dependent data when its parent is deleted. |
| **Quota refund** | Giving back a chat message that was charged when the AI failed to answer. |

---

## Change log

| Version | Date | Change |
|---|---|---|
| 1.0 | 4 Oct 2026 | First version. |
| 1.1 | 4 Oct 2026 | Contract agreement with the frontend: #6 wrong current password 401 → **400**; #8 Gemini provider errors 500 → **502**; §2.1 401 handling clarified (only #3 uses 401 for wrong credentials); §2.6 local-proxy wording. All 21 endpoints agreed. |

*End of document.*
