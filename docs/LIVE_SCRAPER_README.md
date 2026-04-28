# NSE Live Data Scraper & SQLite Cache

## Overview

The NSE Chatbot now includes a **automated live data scraper** with SQLite caching and background scheduling. This ensures the chatbot always has fresh stock data without blocking on live API requests.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  APScheduler (Background Task Scheduler)                 │
│  ├─ Runs every 15 minutes                                │
│  ├─ Only active 09:00–15:00 EAT (NSE trading hours)      │
│  └─ Executes scrape_and_cache() job                      │
└──────────────┬────────────────────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────────────────┐
│  scraper.py (Live Data Fetcher)                         │
│  ├─ Fetches from: https://afx.kwayisi.org/nse/          │
│  ├─ Uses: requests + BeautifulSoup4                      │
│  ├─ Parses: ticker, name, price, change%, volume        │
│  └─ Timeout: 10 seconds per request                      │
└──────────────┬────────────────────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────────────────┐
│  database.py (SQLite Manager)                           │
│  ├─ Stores: stocks table (ticker, name, price, ...)     │
│  ├─ Tracks: price_history table (ticker, price, date)   │
│  ├─ Updates: INSERT OR UPDATE on each scrape            │
│  └─ Indexes: ticker for fast lookup                      │
└──────────────┬────────────────────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────────────────┐
│  FastAPI Endpoints (Only Read, Never Scrape)            │
│  ├─ GET /api/stocks                                      │
│  ├─ GET /api/stocks/{ticker}                            │
│  └─ GET /scraper/status                                 │
└─────────────────────────────────────────────────────────┘
```

## Components

### 1. **scraper.py** – Live Data Fetcher
```python
scrape_nse_data() → dict[ticker: {name, price, change_pct, volume}]
```

**Features:**
- Scrapes from `https://afx.kwayisi.org/nse/`
- Flexible table selectors (tries multiple CSS classes)
- 10-second timeout per request
- Returns None on failure (safe fallback)
- Parses: ticker, company name, price, % change, trading volume

**Error Handling:**
- Website unavailable → logs warning, returns None
- Table structure changed → tries fallback selectors
- Invalid data → skips corrupted rows, logs debug message

### 2. **database.py** – SQLite Storage
```
SQLite: backend/data/nse_stocks.db
```

**Tables:**
```sql
stocks (
  id INTEGER PRIMARY KEY,
  ticker TEXT UNIQUE,
  name TEXT,
  price REAL,
  change_pct REAL,
  volume INTEGER,
  pe_ratio REAL,
  dividend_yield REAL,
  source TEXT,
  updated_at TIMESTAMP
)

price_history (
  id INTEGER PRIMARY KEY,
  ticker TEXT,
  price REAL,
  recorded_at TIMESTAMP,
  FOREIGN KEY (ticker) → stocks(ticker)
)
```

**Key Functions:**
- `init_db()` – Create tables & indexes
- `batch_insert_stocks(list)` – INSERT OR UPDATE stocks
- `get_all_stocks()` – Retrieve all tickers
- `get_stock_by_ticker(ticker)` – Single stock lookup
- `record_price_history(ticker, price)` – Track price over time
- `get_price_history(ticker, days)` – Retrieve historical prices
- `get_last_update_time()` – Check freshness

### 3. **APScheduler Integration** (in main.py)
```python
@app.on_event("startup")
async def startup_event():
    scheduler.add_job(
        scrape_and_cache,
        CronTrigger(hour="9-15", minute="*/15", timezone=EAT),
        id="nse_scraper"
    )
    scheduler.start()
```

**Schedule:**
- **Frequency:** Every 15 minutes (09:00, 09:15, 09:30, ..., 15:00)
- **Timezone:** EAT (Nairobi, Africa/Nairobi)
- **Window:** 09:00–15:00 (NSE trading hours only)
- **Running Jobs:** Check via GET `/scraper/status`

### 4. **FastAPI Endpoints** – No Live Scraping on Request

#### `GET /api/stocks`
Retrieve all stocks from SQLite cache.

```json
{
  "status": "success",
  "data": [
    {
      "ticker": "SCOM",
      "name": "Safaricom PLC",
      "price": 22.8,
      "change_pct": 0.44,
      "volume": 12500000,
      "pe_ratio": 19.2,
      "dividend_yield": 0.067,
      "source": "live_scrape",
      "updated_at": "2026-04-15T14:30:00"
    },
    ...
  ],
  "last_updated": "2026-04-15T14:30:00",
  "count": 22,
  "source": "sqlite_cache"
}
```

#### `GET /api/stocks/{ticker}`
Retrieve a specific stock + 30-day price history.

```json
{
  "status": "success",
  "data": {
    "ticker": "SCOM",
    "name": "Safaricom PLC",
    "price": 22.8,
    "change_pct": 0.44,
    "volume": 12500000,
    "pe_ratio": 19.2,
    "dividend_yield": 0.067,
    "updated_at": "2026-04-15T14:30:00",
    "price_history": [
      {"ticker": "SCOM", "price": 22.8, "recorded_at": "2026-04-15T14:30:00"},
      {"ticker": "SCOM", "price": 22.7, "recorded_at": "2026-04-15T14:15:00"},
      ...
    ]
  },
  "source": "sqlite_cache"
}
```

#### `GET /scraper/status`
Check scheduler and database freshness.

```json
{
  "status": "running",
  "scheduler_active": true,
  "database_populated": true,
  "stock_count": 22,
  "last_database_update": "2026-04-15T14:30:00",
  "current_time_eat": "2026-04-15T14:35:00+03:00",
  "scrape_schedule": "Every 15 minutes between 09:00-15:00 EAT"
}
```

## Usage

### 1. **Start the Backend**
```bash
cd backend
python -m uvicorn main:app --reload
```

Logs will show:
```
2026-04-15 14:00:00 INFO     Starting background scheduler
2026-04-15 14:00:00 INFO     Scheduler started with NSE scraper job
2026-04-15 14:00:00 INFO     Database initialized successfully
2026-04-15 14:15:00 INFO     Scrape job triggered
2026-04-15 14:15:01 INFO     Scraped and cached 22 stocks
```

### 2. **Check Scraper Status**
```bash
curl http://localhost:8000/scraper/status | jq
```

```json
{
  "status": "running",
  "scheduler_active": true,
  "database_populated": true,
  "stock_count": 22,
  "last_database_update": "2026-04-15T14:15:00",
  "current_time_eat": "2026-04-15T14:15:30+03:00",
  "scrape_schedule": "Every 15 minutes between 09:00-15:00 EAT"
}
```

### 3. **Fetch All Stocks**
```bash
curl http://localhost:8000/api/stocks | jq '.data[] | {ticker, price, change_pct}'
```

```json
{
  "ticker": "SCOM",
  "price": 22.8,
  "change_pct": 0.44
}
{
  "ticker": "EQTY",
  "price": 47.5,
  "change_pct": 0.21
}
...
```

### 4. **Get Single Stock with History**
```bash
curl http://localhost:8000/api/stocks/SCOM | jq '.data | {name, price, price_history: (.price_history | length)}'
```

```json
{
  "name": "Safaricom PLC",
  "price": 22.8,
  "price_history": 96
}
```

## Key Features & Benefits

| Feature | Benefit |
|---------|---------|
| **15-min refresh** | Always fresh data during trading hours |
| **No request-time scraping** | Instant API responses (never block) |
| **Background scheduler** | Runs in separate thread pool |
| **SQLite cache** | Lightweight, zero-dependency persistence |
| **Price history tracking** | Analyze trends over 90 days |
| **EAT timezone support** | Respects NSE trading window (09:00–15:00) |
| **Flexible selectors** | Handles website structure changes gracefully |
| **Fallback to seed data** | Never blocks on network errors |

## Configuration

### Change Scrape Frequency
Edit `main.py`, line ~45:
```python
CronTrigger(hour="9-15", minute="*/15", timezone=EAT)
                           ^^^^^^
                       Change interval (*/10 = every 10 min)
```

### Change Trading Window
Edit `main.py`, line ~45:
```python
CronTrigger(hour="9-15", minute="*/15", timezone=EAT)
           ^^^^^^
        Change to "8-17" for 08:00-17:00, etc.
```

### Change Timezone
Edit `main.py`, line ~12:
```python
EAT = timezone("Africa/Nairobi")
                  ^^^^^^^^^^^^^^^^
           Change to any pytz timezone
```

## Monitoring & Logs

### Scraper Logs (in stdout)
```
2026-04-15T15:00:00 INFO     Scrape job triggered
2026-04-15T15:00:01 INFO     Successfully scraped 22 stocks from afx.kwayisi.org/nse/
2026-04-15T15:00:02 INFO     Scraped and cached 22 stocks
2026-04-15T15:00:03 INFO     Batch inserted/updated 22 stocks
```

### Database Logs (in stdout)
```
2026-04-15T14:00:00 INFO     Database initialized successfully
2026-04-15T15:00:02 INFO     Batch inserted/updated 22 stocks
```

### Error Logs (if website changes)
```
2026-04-15T15:00:00 WARNING  Could not find stocks table in response - website structure may have changed
2026-04-15T15:00:00 INFO     Scrape returned no data
```

## Maintenance

### Clean Old Price History
```python
# Run manually or cron daily
database.clear_old_history(days=90)  # Delete entries > 90 days old
```

### Reset Database
```bash
# Stop the app
# Delete database file
rm backend/data/nse_stocks.db

# Restart app (will recreate empty database)
# Next scrape will populate with live data
```

### Inspect Database
```bash
# SQLite CLI
sqlite3 backend/data/nse_stocks.db

# List stocks
SELECT ticker, name, price, updated_at FROM stocks ORDER BY ticker;

# Check price history for SCOM
SELECT price, recorded_at FROM price_history
WHERE ticker='SCOM'
ORDER BY recorded_at DESC
LIMIT 10;
```

## Troubleshooting

### Issue: **Scraper returns no data**
- **Cause:** Website `afx.kwayisi.org/nse/` structure changed
- **Solution:** Update CSS selectors in `scrapy.py` (lines 40-47)
- **Fallback:** Falls back to seed data automatically

### Issue: **Scheduler not running**
- **Check:** `curl http://localhost:8000/scraper/status`
- **Cause:** App crashed or timezone mismatch
- **Solution:** Check logs, restart app with `python -m uvicorn main:app --reload`

### Issue: **Database locked/errors**
- **Cause:** Multiple processes accessing database simultaneously
- **Solution:** SQLite file locking is automatic; typically resolves in seconds
- **Note:** SQLite works fine for this use case; migrate to PostgreSQL if needed at scale

### Issue: **Old data in database**
- **Cause:** Scraper hasn't run yet (before 09:00 EAT)
- **Solution:** Wait for 09:15 EAT, or manually trigger:
  ```python
  from scraper import scrape_nse_data
  scrape_nse_data()  # Manually run scraper
  ```

## Files Modified/Created

```
backend/
├── scraper.py                    [NEW] Live data fetcher
├── database.py                   [NEW] SQLite manager
├── main.py                       [MODIFIED] Added scheduler + endpoints
├── requirements.txt              [MODIFIED] Added APScheduler==3.11.1
├── test_integration.py           [NEW] Integration test suite
└── data/
    └── nse_stocks.db            [AUTO-CREATED] SQLite database
```

## Dependencies Added

```txt
APScheduler==3.11.1      # Background job scheduling
beautifulsoup4==4.14.3   # HTML parsing (already present)
requests==2.33.0         # HTTP fetching (already present)
pytz==2026.1.post1       # Timezone support (already present)
```

## Next Steps

1. ✅ Live scraper deployed and working
2. ✅ SQLite cache persists data reliably
3. ✅ APScheduler runs every 15 minutes (09:00–15:00 EAT)
4. ✅ /api/stocks endpoint serves cached data instantly
5. ✅ No live scraping on request (zero blocking)

**Recommended enhancements:**
- Frontend: Add price chart using `price_history` data
- Frontend: Show "last updated" timestamp on pages
- Monitor: Set up alerts if scraper fails > 3 consecutive times
- Database: Migrate to PostgreSQL if scaling beyond 100+ stocks
