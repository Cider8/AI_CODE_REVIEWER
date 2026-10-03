from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings

#import database for connect to mongodb

from app.database import init_db, close_db

from app.routes import auth, reviews, collections, stats, chat


#asynccontextmanager used for lifespan events in FastAPI, which allows you to 
# define setup and teardown logic for your application. 
# This is useful for tasks like connecting to a database, 
# initializing resources, or performing cleanup when the application starts or stops.

@asynccontextmanager
async def lifespan (app:FastAPI):
    
    #startup
    try:
        await init_db()
        print("Database connected successfully(beanie)")  
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("API routes that depend on MongoDB will return 503 until MongoDB is reachable")

    yield  # This is where the application runs.

    #shutdown
    await close_db()


# Create FastAPI app instance with metadata and lifespan events
app = FastAPI(
    title="KrishnaLens AI Code Review API",
    version=settings.project_version,
    lifespan=lifespan,
)

# FastAPI's default 422 body echoes each rejected value back under "input" —
# for a failed register or password change that is the plaintext password,
# which then lands in browser devtools, proxies and client error logs. Only
# where the error is and what is wrong are returned.
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [
        {"type": err.get("type"), "loc": list(err.get("loc", ())), "msg": err.get("msg")}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": errors},
    )


#cors origins for frontend and backend communication

app.add_middleware(
    CORSMiddleware,
    allow_origins= [settings.frontend_url],
    allow_credentials = True,
    allow_methods= ["*"],
    allow_headers= ["*"],
)

#routes for different functionalities of the application

app.include_router(auth.router)
app.include_router(reviews.router)
app.include_router(collections.router)
app.include_router(stats.router)
app.include_router(chat.router)

@app.get("/")
async def root():
    return {"message": "Welcome to KrishnaLens AI Code Review API"}

