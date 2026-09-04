# CodeLens — AI Code Reviewer

Full-stack AI-powered code review app: submit a code snippet, get back an
AI-generated analysis (bugs, security issues, performance issues, refactor
suggestions, complexity, tags) via Google Gemini, and track review history,
scores, and collections over time.

**Stack:** React (Vite) + FastAPI + MongoDB (Beanie ODM) + Gemini AI

## Project Structure

```
AI_CODE_REVIEWER/
├── backend_fastAPI/            # FastAPI backend
│   ├── app/
│   │   ├── main.py             # FastAPI app, CORS, lifespan (DB init)
│   │   ├── config.py           # pydantic-settings (.env)
│   │   ├── database.py         # Beanie/Motor init + connection status flag
│   │   ├── dependencies.py     # get_current_user (JWT auth), require_db
│   │   ├── models/             # Beanie Documents (DB schema)
│   │   │   ├── user.py
│   │   │   ├── review.py
│   │   │   ├── stats.py
│   │   │   └── collection.py
│   │   ├── schemas/            # Pydantic request/response models (camelCase)
│   │   │   ├── base.py         # CamelModel — auto camelCase aliasing
│   │   │   ├── auth_schema.py
│   │   │   ├── review_schema.py
│   │   │   └── stats_schema.py
│   │   ├── routes/
│   │   │   ├── auth.py         # register / login / me / profile / password / delete
│   │   │   ├── reviews.py      # submit / list / get / delete reviews (AI call)
│   │   │   ├── stats.py        # dashboard stats
│   │   │   └── collections.py  # group reviews into collections
│   │   └── utils/
│   │       ├── security.py     # JWT + bcrypt
│   │       ├── gemini.py       # Gemini prompt + response parsing
│   │       └── convert.py      # Beanie Document -> Pydantic schema helper
│   ├── requirements.txt
│   └── .env.example
│
└── frontend/                   # React + Vite
    ├── src/
    │   ├── pages/
    │   │   ├── Home.jsx
    │   │   ├── Login.jsx / Register.jsx
    │   │   ├── Dashboard.jsx       # charts + stats
    │   │   ├── NewReview.jsx       # code input + AI trigger
    │   │   ├── ReviewDetail.jsx    # full AI analysis
    │   │   ├── History.jsx         # all reviews + search/filter
    │   │   ├── Collections.jsx
    │   │   └── Profile.jsx
    │   ├── components/layout/Layout.jsx  # sidebar nav (protected routes)
    │   ├── context/AuthContext.jsx       # global auth state
    │   ├── services/api.js               # axios + JWT injection
    │   └── App.jsx                        # routes (public + protected)
    └── package.json
```

## How It Works

1. **Auth** — `POST /api/auth/register` / `login` issue a JWT (`python-jose`,
   HS256, 7-day expiry). Passwords are hashed with `bcrypt` via `passlib`.
   Protected routes depend on `get_current_user`, which decodes the bearer
   token and loads the `User` document from MongoDB.
2. **Submitting a review** — `POST /api/reviews` sends the code + language to
   Gemini (`google-generativeai`) with a prompt that forces a strict JSON
   response shape (summary, score, bugs, security issues, performance issues,
   refactored code, complexity, tags). The parsed result is validated against
   an `AIReviewResult` Pydantic model, saved as a `Review` document, and the
   user's `UserStats` (running average score, language breakdown, score
   history) is updated in the same request.
3. **Dashboard** — `GET /api/stats` returns the user's `UserStats` plus the 5
   most recent reviews, which the frontend renders as charts (Recharts).
4. **Collections** — group reviews under a named collection; Beanie has no
   Mongoose-style `.populate()`, so `collections.py` manually fetches and
   maps `review_ids` into full review summaries.
5. **camelCase bridge** — Mongo/Python naturally use snake_case
   (`overall_score`), but the React frontend expects camelCase
   (`overallScore`). Every response schema inherits from `CamelModel`
   (`app/schemas/base.py`), which auto-generates the camelCase alias so the
   frontend needs zero changes.

## Setup

### Backend

```bash
cd backend_fastAPI
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Fill in MONGO_URI, JWT_SECRET, GEMINI_API_KEY (and FRONTEND_URL if not localhost:5173)

uvicorn app.main:app --reload --port 8000
```

Swagger UI: **http://localhost:8000/docs**

If MongoDB isn't reachable at startup, the server still starts, but every
DB-backed route returns `503 Database unavailable` instead of crashing
(see `require_db` in `app/dependencies.py`).

> **MongoDB Atlas note:** if you see `SSL: TLSV1_ALERT_INTERNAL_ERROR` at
> startup, it's almost always Atlas's **Network Access (IP allow list)**
> rejecting your current public IP — not a code or library bug. Add your
> current IP (or `0.0.0.0/0` for local dev) under Atlas → Network Access →
> IP Access List. Networks with rotating/NAT'd IPs (e.g. campus WiFi) may
> need this redone periodically.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite dev server proxies API calls to `http://localhost:8000`.

## Environment Variables (`backend_fastAPI/.env`)

```env
MONGO_URI=mongodb://localhost:27017
DB_NAME=ai_code_reviewer
JWT_SECRET=replace_with_a_long_random_secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7
GEMINI_API_KEY=your_actual_gemini_key
FRONTEND_URL=http://localhost:5173
```

Get a Gemini API key at: https://aistudio.google.com/app/apikey

## API Routes

| Method | Route | Description |
|--------|-------|-------------|
| POST | /api/auth/register | Register |
| POST | /api/auth/login | Login |
| GET  | /api/auth/me | Get current user |
| PATCH | /api/auth/profile | Update name / preferred languages |
| PATCH | /api/auth/password | Change password |
| DELETE | /api/auth/account | Delete account + all data |
| POST | /api/reviews | Submit code for AI review |
| GET  | /api/reviews | List reviews (paginated, search, filter) |
| GET  | /api/reviews/{id} | Get single review |
| DELETE | /api/reviews/{id} | Delete review |
| GET  | /api/stats | Dashboard stats |
| POST | /api/collections | Create collection |
| GET  | /api/collections | List collections (with populated reviews) |
| PATCH | /api/collections/{id}/add-review | Add review to collection |
| DELETE | /api/collections/{id} | Delete collection |
| GET | /api/health | Health check |

## Notes on Design Decisions

- **`CamelModel`** (`app/schemas/base.py`): every response schema inherits
  from this so the existing React code works unmodified.
- **`doc_to_schema()`** (`app/utils/convert.py`): bridges Beanie's `id` field
  to the `_id`/`id` shape our schemas expose.
- **Manual population** in `collections.py`: Beanie has no
  Mongoose-style `.populate()`, so `review_ids` are fetched and mapped
  manually.
- **AI validation**: Gemini's JSON response is parsed directly into the
  `AIReviewResult` Pydantic model — malformed AI output fails the request
  with a clear `502` instead of saving garbage.
- **`require_db` dependency**: every router that touches MongoDB depends on
  it, so a down/unreachable database produces a clean `503` instead of a
  raw `AttributeError` (Beanie's query-building attributes on Document
  classes only exist after `init_beanie()` succeeds).

## Known Gaps

- No automated test suite yet.
