# Backend Guide for AI Code Reviewer

This document explains what is happening in the Python backend, which files are important, which parts can be rewritten for learning, and how to test the FastAPI APIs safely.

## 1) What backend is doing

The backend is a FastAPI application that does 5 major things:

1. Connects to MongoDB using Motor + Beanie
2. Handles authentication with JWT tokens
3. Stores users, reviews, stats, and collections in MongoDB
4. Sends code to Gemini AI for review
5. Exposes REST APIs for the frontend

The main app entry point is:
- backend_fastAPI/app/main.py

The database startup logic is:
- backend_fastAPI/app/database.py

The environment and app config are:
- backend_fastAPI/app/config.py


## 2) Database used

This project uses MongoDB.

Why:
- It stores documents, not tables like SQL
- The project uses Beanie and Motor
- Beanie is an async ODM for MongoDB

Important libraries:
- motor
- pymongo
- beanie

The actual database connection is initialized in:
- backend_fastAPI/app/database.py

The app sets up the database names in:
- backend_fastAPI/app/config.py

Default settings:
- Mongo URI: mongodb://localhost:27017
- Database name: ai_code_reviewer


## 3) File-by-file explanation

### Main app files

#### backend_fastAPI/app/main.py
This is the FastAPI app entrypoint.

It does:
- creates the FastAPI app
- runs startup logic
- enables CORS for the frontend
- registers route files
- exposes /api

This is the file you run with uvicorn.

#### backend_fastAPI/app/config.py
This file loads environment variables.

It defines:
- mongo_uri
- db_name
- jwt_secret
- jwt_algorithm
- jwt_expire_days
- gemini_api_key
- frontend_url

It reads from a .env file.

Important: do not delete this file if you want auth + database + AI to work.

#### backend_fastAPI/app/database.py
This file connects to MongoDB and initializes Beanie document models.

It imports all model classes and calls:
- init_beanie(database=db, document_models=[...])

This is required to make the application connect to MongoDB.


### Route files

#### backend_fastAPI/app/routes/auth.py
Responsible for:
- register
- login
- get current user
- update profile
- change password
- delete account

Routes are prefixed with:
- /api/auth

Important: this file uses JWT and password hashing.

#### backend_fastAPI/app/routes/reviews.py
Responsible for:
- create a review
- list reviews
- get one review by id
- delete review

It also calls Gemini AI using:
- app/utils/gemini.py

This file is the core of the AI review feature.

#### backend_fastAPI/app/routes/stats.py
Responsible for:
- dashboard data
- total reviews
- average score
- recent reviews
- language breakdown

#### backend_fastAPI/app/routes/collections.py
Responsible for:
- creating collections
- listing collections
- adding a review into a collection
- deleting a collection


### Dependency and auth files

#### backend_fastAPI/app/dependencies.py
This file contains reusable logic for:
- checking whether database is connected
- protecting routes using JWT

It is very important. If you remove it, all protected routes fail.

#### backend_fastAPI/app/utils/security.py
This file handles:
- hashing password
- verifying password
- creating JWT token
- decoding JWT token

This is essential for login and protected routes.

#### backend_fastAPI/app/utils/gemini.py
This file sends code to Google Gemini and parses the AI response.

It is important because this app is AI-review based.


### Model files

#### backend_fastAPI/app/models/user.py
Stores user document.

Fields include:
- name
- email
- password
- preferred_languages
- created_at

#### backend_fastAPI/app/models/review.py
Stores review data and AI findings.

Includes:
- title
- original_code
- language
- summary
- overall_score
- bugs
- security_issues
- performance_issues
- improvements
- refactored_code
- complexity
- tags

#### backend_fastAPI/app/models/stats.py
Stores dashboard stats.

Includes:
- total_reviews
- average_score
- total_bugs_found
- total_security_issues_found
- score_history
- language_breakdown

#### backend_fastAPI/app/models/collection.py
Stores a user collection with review IDs.


### Schema files

The schemas define response/request validation for FastAPI.

Folder:
- backend_fastAPI/app/schemas/

Examples:
- auth_schema.py
- review_schema.py
- stats_schema.py
- base.py

These validate incoming JSON and shape outgoing JSON responses.

Do not ignore these files when rebuilding the backend, because FastAPI uses them to validate requests.


## 4) What you should keep if you want the app to run

These are the must-keep parts:

### Install / dependencies
Keep these packages in requirements.txt:

- fastapi
- uvicorn[standard]
- beanie
- motor
- pymongo
- pydantic[email]
- pydantic-settings
- python-jose[cryptography]
- passlib[bcrypt]
- bcrypt
- python-dotenv
- google-generativeai
- python-multipart
- httpx

You should not remove these unless you are intentionally rewriting the app to a different architecture.

### Keep these files
- app/main.py
- app/config.py
- app/database.py
- app/dependencies.py
- app/utils/security.py
- app/utils/gemini.py
- app/models/*
- app/routes/*
- app/schemas/*

### Keep these concepts
- MongoDB connection
- JWT auth
- API router organization
- Pydantic validation
- async database interactions with Beanie


## 5) What you can remove or rewrite for learning

If your goal is to learn Python deeply, you can rebuild or simplify these parts:

### Safe rewrite candidates
- route logic inside auth.py, reviews.py, stats.py, collections.py
- helper functions inside utils
- custom validation logic
- business logic in routes
- response models

### Good learning approach
Rewrite the project step by step:

1. Recreate a simple FastAPI app with one route
2. Add a Pydantic model
3. Add a MongoDB connection
4. Add JWT authentication
5. Add a review route
6. Add AI integration
7. Add stats and collections

This is a good learning sequence.

### Not good to remove first
Do not remove the following before you understand them:
- config.py
- database.py
- dependencies.py
- security.py
- models
- router registration in main.py

Those are the backbone of the app.


## 6) Best order to rewrite for learning

If you want to rebuild the Python side from scratch, do it in this order:

1. Install dependencies
2. Create app/config.py
3. Create app/database.py
4. Create MongoDB models
5. Create app/utils/security.py
6. Create app/dependencies.py
7. Create routes/auth.py
8. Create routes/reviews.py
9. Create app/utils/gemini.py
10. Register routes in main.py
11. Test with Swagger UI

This order makes the project understandable.


## 7) FastAPI testing instructions

### Step 1: Create environment
Inside backend_fastAPI:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Create .env file
Create a file named .env in backend_fastAPI/

Example:

```env
MONGO_URI=mongodb://localhost:27017
DB_NAME=ai_code_reviewer
JWT_SECRET=your_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7
GEMINI_API_KEY=your_gemini_api_key
FRONTEND_URL=http://localhost:5173
```

### Step 3: Start MongoDB
Make sure MongoDB is running locally.

### Step 4: Run the app

```bash
cd backend_fastAPI
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 5: Open API docs
Open these in browser:

- http://localhost:8000/docs
- http://localhost:8000/redoc

FastAPI Swagger UI is the easiest way to test every API.

### Step 6: Test endpoints
Use Swagger UI to send requests for:
- /api/auth/register
- /api/auth/login
- /api/auth/me
- /api/reviews
- /api/stats
- /api/collections

For protected routes, click Authorize and paste the JWT token returned by login.


## 8) How to test with curl (optional)

Login example:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "123456"
  }'
```

Get stats example:

```bash
curl http://localhost:8000/api/stats \
  -H "Authorization: Bearer YOUR_TOKEN"
```


## 9) Best way to learn Python from this project

The important Python concepts used here are:

- classes and inheritance
- Pydantic models
- async/await
- dependency injection in FastAPI
- MongoDB query logic
- JWT token generation/validation
- environment variables
- API route design
- JSON serialization
- modular coding

If you want to learn deeply, rewrite one layer at a time:

- first: simple FastAPI route and Pydantic model
- second: user auth logic
- third: MongoDB models with Beanie
- fourth: AI integration route
- fifth: stats and collections

Do not try to rewrite everything at once.


## 10) Summary

This backend is a modern FastAPI + MongoDB + AI app.

Main idea:
- frontend calls API endpoints
- FastAPI validates input
- Python code interacts with MongoDB
- AI reviews code with Gemini
- results are stored and returned to frontend

The most important files to keep while learning are:
- main.py
- config.py
- database.py
- dependencies.py
- security.py
- models
- routes
- requirements.txt

You can rewrite route logic and business logic as long as the app structure remains intact.

If you want to simplify the project for learning, keep the architecture but rewrite the internals in a smaller and cleaner way.
