from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routes import auth, reviews, stats, collections


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        await init_db()
        print("✅ MongoDB connected (Beanie)")
    except Exception as exc:
        print(f"⚠️ MongoDB unavailable at startup: {exc}")
        print("   API routes that depend on MongoDB will still fail until MongoDB is running.")

    yield
    # Shutdown (nothing to clean up explicitly — Motor closes on GC)


app = FastAPI(
    title="CodeLens — AI Code Reviewer API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router)
app.include_router(reviews.router)
app.include_router(stats.router)
app.include_router(collections.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
