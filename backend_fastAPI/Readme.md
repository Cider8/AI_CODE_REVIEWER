# CodeLens — FastAPI Backend

Python/FastAPI rewrite of the Express backend. Same MongoDB database,
same API contract (camelCase JSON), same routes — drop-in replacement
for the React frontend.

## Stack
- **FastAPI** — web framework
- **Beanie** — async MongoDB ODM (built on Motor + Pydantic)
- **Pydantic v2** — request/response validation, with camelCase aliasing
  so the existing React frontend needs **zero changes**
- **python-jose** — JWT
- **passlib[bcrypt]** — password hashing
- **google-generativeai** — Gemini AI code analysis

## Project Structure

```
backend-fastapi/
├── app/
│   ├── main.py              # FastAPI app, CORS, lifespan (DB init)
│   ├── config.py            # pydantic-settings (.env)
│   ├── database.py          # Beanie/Motor init
│   ├── dependencies.py       # get_current_user (JWT auth)
│   ├── models/                # Beanie Documents (DB schema)
│   │   ├── user.py
│   │   ├── review.py
│   │   ├── stats.py
│   │   └── collection.py
│   ├── schemas/               # Pydantic request/response models
│   │   ├── base.py            # CamelModel (camelCase aliasing)
│   │   ├── auth_schema.py
│   │   ├── review_schema.py
│   │   └── stats_schema.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── reviews.py
│   │   ├── stats.py
│   │   └── collections.py
│   └── utils/
│       ├── security.py       # JWT + bcrypt
│       ├── gemini.py          # AI integration
│       └── convert.py         # Document -> schema helper
├── requirements.txt
└── .env.example
```

## Setup

```bash
cd backend_fastAPI
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env   # or reuse the existing .env file
# Fill in MONGO_URI, JWT_SECRET, GEMINI_API_KEY, and FRONTEND_URL if needed
# If MongoDB is not running locally, the API will still start but DB-backed routes will fail until you start it.

uvicorn app.main:app --reload --port 8000
```

API docs (Swagger UI): **http://localhost:8000/docs**

## Frontend
The `vite.config.js` proxy now points to `http://localhost:8000`
(FastAPI's default port). No other frontend changes are needed —
all JSON responses use camelCase via `CamelModel`.

## API Routes (identical to Express version)

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

## Notes on Design Decisions

- **CamelModel** (`app/schemas/base.py`): every response schema inherits
  from this. It auto-generates camelCase aliases (`overall_score` ->
  `overallScore`) so the existing React code works unmodified.
- **`doc_to_schema()`** (`app/utils/convert.py`): Beanie Documents use
  `id`, while our schemas expose `_id`/`id` for Mongo-style IDs — this
  helper bridges the two safely.
- **Manual population** in `collections.py`: Beanie has no Mongoose-style
  `.populate()`, so `review_ids` are fetched and mapped manually.
- **AI validation**: Gemini's JSON response is parsed directly into the
  `AIReviewResult` Pydantic model — if the AI returns malformed data,
  the request fails fast with a clear error instead of saving garbage.
