# NSE AI Advisor

FastAPI + React chatbot for Nairobi Securities Exchange market questions, stock comparisons, charts, news context, and education.

## Setup

Install backend dependencies:

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Configure `backend/.env`:

```env
FEATHERLESS_API_KEY=your_featherless_api_key
FEATHERLESS_BASE_URL=https://api.featherless.ai/v1
FEATHERLESS_CHAT_MODEL=your_featherless_chat_model

PINECONE_API_KEY=your_pinecone_api_key
NEWSAPI_KEY=your_newsapi_key
```

The backend uses the OpenAI SDK package for Featherless because Featherless is OpenAI-compatible. `OPENAI_API_KEY` is optional and only needed for legacy OpenAI embeddings/Pinecone document search.

Install frontend dependencies:

```powershell
cd ..\frontend
npm install
```

## Run

Backend:

```powershell
cd backend
venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8001
```

Frontend:

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5175 --strictPort
```

Open:

```text
http://127.0.0.1:5175
```

Health check:

```text
http://127.0.0.1:8001/health
```

## View Local Database Records

If `sqlite3` is not installed on Windows, use the included Python viewer:

```powershell
cd backend
.\venv\Scripts\python.exe view_db.py
.\venv\Scripts\python.exe view_db.py users --limit 20
.\venv\Scripts\python.exe view_db.py stocks --limit 20
```

## Generate Beginner Knowledge Base

The chatbot includes a generated beginner knowledge base for common NSE education
questions. Regenerate it with:

```powershell
cd backend
.\venv\Scripts\python.exe -m services.knowledge_base_generator
```

## Django Knowledge Base Service

The independent `django_kb` service provides persistent, admin-editable RAG retrieval
without replacing the existing FastAPI application. Its search pipeline is:

```text
keyword/tag ranking -> fuzzy matching -> optional semantic search -> NSE-only LLM fallback
```

Install and initialize it:

```powershell
cd django_kb
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py seed_knowledge_base
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8002
```

Open the editable admin at `http://127.0.0.1:8002/admin/` and search with:

```text
GET http://127.0.0.1:8002/api/kb/search?q=What%20is%20a%20dividend?
GET http://127.0.0.1:8002/api/kb/search?q=inflation&category=investment-basics
```

PostgreSQL is enabled by setting `DJANGO_DB_ENGINE=postgresql` and the `DJANGO_DB_*`
variables in `django_kb/.env`. SQLite remains the zero-configuration local development
default. Environment files are never committed.

Semantic search is optional because the model dependency is large:

```powershell
pip install -r requirements-embeddings.txt
python manage.py rebuild_kb_embeddings
```

Then set `KB_EMBEDDINGS_ENABLED=true`. Weak matches below `KB_MIN_CONFIDENCE` use the
configured Featherless model, while missing keys and provider errors fall back safely.

Run the isolated Django test suite without touching real records:

```powershell
python manage.py test knowledge.tests
```
