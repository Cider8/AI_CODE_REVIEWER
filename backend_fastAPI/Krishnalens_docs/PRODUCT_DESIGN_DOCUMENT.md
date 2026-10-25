# KrishnaLens: Product Design Document (Overview)

| | |
|---|---|
| **Version** | 2.0 |
| **Date** | 26 October 2026 |
| **Scope** | System-wide design: architecture, shared conventions, endpoint index, data model. Feature details are in the feature design docs (§6). |
| **Requirements** | `PRODUCT_REQUIREMENTS_DOCUMENT.md` (user view) |

## Contents
1. [Architecture](#1-architecture)
2. [Technology stack](#2-technology-stack)
3. [Shared conventions](#3-shared-conventions)
4. [Endpoint index](#4-endpoint-index)
5. [Data model](#5-data-model)
6. [Feature design documents](#6-feature-design-documents)
7. [Configuration and hosting](#7-configuration-and-hosting)
8. [Known limitations](#8-known-limitations)

---

## 1. Architecture

```
 Browser (React SPA, JWT in localStorage)
        │  HTTPS /api/*   Authorization: Bearer <JWT>
        ▼
 FastAPI app (uvicorn) ── routes: auth · reviews · stats · collections · chat
        │                         │
        │ Motor + Beanie          │ google-generativeai SDK
        ▼                         ▼
 MongoDB Atlas (6 collections)   Google Gemini (review + chat)
```

- **Stateless API:** one process, no queues or workers. Every request is authenticated by its JWT.
- **AI before writes:** any Gemini call finishes before the database is changed, so a failure saves nothing.
- **Code layout:** `routes/` (one router per feature), `models/` (database documents), `schemas/` (request and response shapes), `utils/` (security, Gemini, stats, time).

## 2. Technology stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite, Tailwind CSS, Recharts, Axios |
| API | FastAPI 0.115, uvicorn, Pydantic v2 |
| Database | MongoDB Atlas via Motor + Beanie |
| Auth | JWT (python-jose, HS256), bcrypt (passlib) |
| AI | Google Gemini (`gemini-3.6-flash`) via `google-generativeai` |

## 3. Shared conventions

| Topic | Rule |
|---|---|
| **Auth** | 🔒 routes need `Authorization: Bearer <JWT>`. A missing, invalid or expired token, or a deleted user, gets **401**, and the client logs out on 401. Details: `DESIGN_AUTH_AND_SECURITY.md`. |
| **Ownership** | Every query filters by `user_id`. Someone else's resource gets **404**, the same as a missing one. |
| **JSON naming** | Responses use camelCase (`overallScore`), and IDs are returned as `_id`. Requests accept camelCase or snake_case. |
| **Errors** | Always `{"detail": …}`. A **422** detail is a list of `{type, loc, msg}` only: the rejected input is never echoed back. |
| **Status codes** | 400 business rule · 401 not authenticated · 404 missing or not yours · 422 validation · 429 chat limit · 502 AI failed · 503 database down |
| **Database down** | The app still starts; every database route returns **503 "Database unavailable"**. |
| **Timestamps** | ISO-8601 UTC, no timezone suffix. |
| **CORS** | Only `FRONTEND_URL` is allowed. |

## 4. Endpoint index

| # | Method & path | Auth | Feature doc |
|---|---|---|---|
| 1 | `GET /` (health) | – | — |
| 2–7 | `POST /api/auth/register` · `POST /login` · `GET /me` · `PATCH /profile` · `PATCH /password` · `DELETE /account` | 2–3 open, 4–7 🔒 | Auth & Security |
| 8–11 | `POST /api/reviews` · `GET /api/reviews` · `GET /api/reviews/{id}` · `DELETE /api/reviews/{id}` | 🔒 | AI Code Review |
| 12 | `GET /api/stats` | 🔒 | Dashboard Stats |
| 13–18 | `POST /api/collections` · `GET` · `PATCH /{id}` · `PATCH /{id}/add-review` · `PATCH /{id}/remove-review` · `DELETE /{id}` | 🔒 | Collections |
| 19–21 | `POST /api/chat/reviews/{reviewId}/start` · `GET /api/chat/sessions/{id}/messages` · `POST /api/chat/sessions/{id}/messages` | 🔒 | Review Chat |

Request and response shapes, error messages and flows for each endpoint are in its feature doc.

## 5. Data model

```
users ──1:1── user_stats            (dashboard figures + chat quota)
  │
  ├──1:N── reviews ◄──N:M── collections.review_ids[]
  │           │
  │           └──1:1 per user── chat_sessions ──1:N── chat_messages
  └──1:N── collections
```

| Collection | Owned by feature doc | Key index |
|---|---|---|
| `users` | Auth & Security | `email` unique |
| `reviews` | AI Code Review | `user_id` |
| `user_stats` | Dashboard Stats | `user_id` unique |
| `collections` | Collections | `user_id` |
| `chat_sessions`, `chat_messages` | Review Chat | `review_id` + `user_id`, `session_id` |

**Deletes cascade in code** (no transactions):
- deleting a review removes it from collections, deletes its chat, and recalculates stats;
- deleting an account removes all of that member's data.

## 6. Feature design documents

| Doc | Covers |
|---|---|
| [`DESIGN_AUTH_AND_SECURITY.md`](DESIGN_AUTH_AND_SECURITY.md) | Sign-up and sign-in, JWT sessions, password rules, profile, account deletion, privacy rules |
| [`DESIGN_AI_CODE_REVIEW.md`](DESIGN_AI_CODE_REVIEW.md) | Gemini review prompt and validation, review create, list, search and delete |
| [`DESIGN_REVIEW_CHAT.md`](DESIGN_REVIEW_CHAT.md) | Chat sessions, Gemini chat, 6-message history, daily limit and refund |
| [`DESIGN_DASHBOARD_STATS.md`](DESIGN_DASHBOARD_STATS.md) | Dashboard figures, recalculation, common weaknesses |
| [`DESIGN_COLLECTIONS.md`](DESIGN_COLLECTIONS.md) | Grouping reviews: create, list, rename, add, remove, delete |

Rule: a feature's details live **only** in its feature doc. This overview changes only when something system-wide changes.

## 7. Configuration and hosting

| Variable | Required | Purpose |
|---|---|---|
| `MONGO_URI`, `DB_NAME` | no (local defaults) | Database connection |
| `JWT_SECRET` | **yes** | Signs login tokens |
| `JWT_EXPIRE_DAYS` | no (7) | Token lifetime |
| `GEMINI_API_KEY` | **yes** | Gemini access |
| `FRONTEND_URL` | no (`http://localhost:5173`) | Allowed CORS origin |

- **Backend:** Render, which deploys the committed code. **Frontend:** Vercel. A move to AWS is planned.
- **Local development** uses the same Atlas cluster, so test against a separate `DB_NAME` to avoid touching real data.

## 8. Known limitations

- No daily limit on code reviews (AI cost), and no timeout or retry around Gemini calls.
- Cascading deletes aren't transactional, so a crash midway can leave orphaned data.
- Login tokens can't be revoked before they expire (7 days).
- No automated tests on this branch. The QC suite lives on `feature/forgot-password-qc-fixes`.

---

## Change log

| Version | Date | Change |
|---|---|---|
| 1.0 | 4 Oct 2026 | First version (single, detailed document). |
| 1.1 | 4 Oct 2026 | Frontend contract agreement: #6 → 400, #8 provider errors → 502. |
| 2.0 | 26 Oct 2026 | Reduced to a system overview (1,107 → about 150 lines). Per-endpoint detail, flows, schemas and decisions moved to five feature design docs. |
