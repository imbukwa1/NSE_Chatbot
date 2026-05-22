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
