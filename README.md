# CodeLens — AI Code Reviewer

Full-stack AI-powered code review app built with React + Express + MongoDB + Gemini AI.

## Project Structure

```
ai-code-reviewer/
├── backend/                  # Express + MongoDB
│   ├── models/
│   │   ├── User.js
│   │   ├── Review.js
│   │   ├── UserStats.js
│   │   └── Collection.js
│   ├── routes/
│   │   ├── auth.js
│   │   ├── reviews.js
│   │   ├── stats.js
│   │   └── collections.js
│   ├── middleware/
│   │   └── auth.js           # JWT protect middleware
│   ├── utils/
│   │   └── gemini.js         # Gemini AI integration
│   ├── server.js
│   ├── package.json
│   └── .env.example
│
└── frontend/                 # React + Vite
    ├── src/
    │   ├── pages/
    │   │   ├── Login.jsx
    │   │   ├── Register.jsx
    │   │   ├── Dashboard.jsx     # Charts + stats
    │   │   ├── NewReview.jsx     # Code input + AI trigger
    │   │   ├── ReviewDetail.jsx  # Full AI analysis
    │   │   ├── History.jsx       # All reviews + search
    │   │   ├── Collections.jsx
    │   │   └── Profile.jsx
    │   ├── components/layout/
    │   │   └── Layout.jsx        # Sidebar navigation
    │   ├── context/
    │   │   └── AuthContext.jsx   # Global auth state
    │   ├── services/
    │   │   └── api.js            # Axios + JWT injection
    │   ├── App.jsx               # Routes
    │   ├── main.jsx
    │   └── index.css             # Design system / CSS vars
    ├── index.html
    └── package.json
```

## Setup

### Backend
```bash
cd backend
npm install
cp .env.example .env
# Fill in MONGO_URI, JWT_SECRET, GEMINI_API_KEY in .env
npm run dev
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## API Routes

| Method | Route | Description |
|--------|-------|-------------|
| POST | /api/auth/register | Register |
| POST | /api/auth/login | Login |
| GET  | /api/auth/me | Get current user |
| POST | /api/reviews | Submit code for AI review |
| GET  | /api/reviews | Get all reviews (paginated) |
| GET  | /api/reviews/:id | Get single review |
| DELETE | /api/reviews/:id | Delete review |
| GET  | /api/stats | Dashboard stats |
| POST | /api/collections | Create collection |
| GET  | /api/collections | Get all collections |
| PATCH | /api/collections/:id/add-review | Add review to collection |
| DELETE | /api/collections/:id | Delete collection |

## Environment Variables

```env
PORT=5000
MONGO_URI=mongodb://localhost:27017/ai-code-reviewer
JWT_SECRET=your_super_secret_key
GEMINI_API_KEY=your_gemini_api_key
```

Get your Gemini API key at: https://aistudio.google.com/app/apikey

## Features
- JWT authentication (register/login)
- AI code review via Google Gemini (bugs, security, performance, refactored code)
- Score tracking over time (line chart)
- Language breakdown (pie chart)
- Review history with search + filter
- Collections to group reviews
- User stats dashboard
