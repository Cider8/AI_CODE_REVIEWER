from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings

#import database for connect to mongodb

from app.database import init_db

from app.routes import auth, reviews, collections, stats


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
        print(" Api route that depend on mongodbm still failes still mongodb is running") 
    
    #shutdown
    yield  # This is where the application runs. After this point, the teardown logic will be executed.


# Create FastAPI app instance with metadata and lifespan events
app = FastAPI(
    title="Codelens AI Code_Review_API",
    version=settings.PROJECT_VERSION,
    lifespan=lifespan,
)

#cors origins for frontend and backend communication

app.add_middleware(
    CORSMiddleware,
    allow_origins= [settings.FRONTEND_URL],
    allow_credentials = True,
    allow_methods= ["*"],
    allow_headers= ["*"],
)

#routes for different functionalities of the application

app.include_router(auth.router)
app.include_router(reviews.router)
app.include_router(collections.router)
app.include_router(stats.router)

app.get("/")
async def root():
    return {"message": "Welcome to Codelens AI Code_Review_API"}

