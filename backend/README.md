# NSE AI Advisor Backend

FastAPI backend for an AI-powered Nairobi Securities Exchange chatbot. The backend provides stock data, market summaries, Featherless AI/Pinecone-assisted chat, authentication, user profiles, favorites, watchlists, admin management, and lightweight monitoring.

## Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Fill `.env` with your Featherless AI, Pinecone, NewsAPI, JWT, and frontend origin values.

Required AI chat settings:

```env
FEATHERLESS_API_KEY=your_featherless_api_key
FEATHERLESS_BASE_URL=https://api.featherless.ai/v1
FEATHERLESS_CHAT_MODEL=your_featherless_chat_model
```

The backend still uses the OpenAI SDK package because Featherless exposes an OpenAI-compatible API. `OPENAI_API_KEY` is optional and only needed if you continue using OpenAI embeddings for Pinecone document search.

## Run

```bash
python -m uvicorn main:app --reload --port 8001
```

## Docker

```bash
docker build -t nse-ai-advisor-backend .
docker run --env-file .env -p 8000:8000 nse-ai-advisor-backend
```

## Test

The project uses lightweight runnable unittest scripts:

```bash
venv\Scripts\python.exe tests\test_auth.py
venv\Scripts\python.exe tests\test_chat.py
venv\Scripts\python.exe tests\test_profile.py
venv\Scripts\python.exe tests\test_favorites.py
venv\Scripts\python.exe tests\test_watchlist.py
venv\Scripts\python.exe tests\test_market.py
venv\Scripts\python.exe tests\test_dashboard.py
venv\Scripts\python.exe tests\test_admin.py
venv\Scripts\python.exe tests\test_knowledge_base.py
venv\Scripts\python.exe tests\test_analytics.py
venv\Scripts\python.exe tests\test_monitoring.py
```

## API Overview

- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`
- `POST /chat`, `GET/POST /chat/sessions`
- `GET /market/overview`, `/market/top-gainers`, `/market/top-losers`
- `GET /stocks/search`, `GET /stocks/{ticker}/chart`
- `GET/POST/DELETE /users/me/favorites`
- `GET/POST/PUT/DELETE /users/me/watchlist`
- `GET /dashboard/summary`
- `GET/POST/PUT/DELETE /admin/knowledge-base`
- `GET /admin/users`, `PATCH /admin/users/{id}/status`, `PATCH /admin/users/{id}/role`
- `GET /admin/analytics`
- `GET /system/status`, `/system/scraper-status`, `/system/api-status`

All user-specific routes require JWT authentication. Admin routes require an authenticated user with the `admin` role.
