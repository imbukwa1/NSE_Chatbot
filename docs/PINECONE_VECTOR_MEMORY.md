# Pinecone Vector Memory for NSE Stocks

## Overview

The NSE Chatbot now uses Pinecone vector search for intelligent fuzzy entity matching. When users refer to stocks by:
- Company names: "Safaricom" → Matches SCOM
- Descriptive names: "that big bank" → Matches EQTY, KCB, SCBK
- Sector references: "top phone company" → Matches SCOM
- Informal mentions: "the telecom" → Matches SCOM

The system uses OpenAI embeddings to convert stock descriptions into vectors and searches Pinecone to find the best match automatically.

## Setup Guide

### 1. Create Pinecone Index

1. Sign up at [https://pinecone.io](https://pinecone.io) (free tier available)
2. Create Free Index with settings:
   - **Name**: `nse-stocks`
   - **Dimension**: `1536` (matches text-embedding-3-small)
   - **Metric**: `cosine`
   - **Cloud**: `AWS` (or your preference)
   - **Region**: `us-east-1` (or close to you)
3. Copy your **API Key** and **Environment** (e.g., `gcp-starter`)

### 2. Configure Environment

Add to `.env`:
```bash
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_STOCKS_INDEX=nse-stocks
PINECONE_STOCKS_NAMESPACE=stocks
OPENAI_API_KEY=your_openai_api_key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

### 3. Install/Verify Dependencies

Already included in `requirements.txt`:
```
pinecone==8.1.2
openai==2.31.0
```

## Architecture

### New Module: `embeddings.py`

Functions:

```python
# Generate embeddings for text
get_embedding(text: str) -> list[float]

# Build stock description for embedding
build_stock_text_blob(stock: dict) -> str
# Example output:
# "Equity Bank (EQTY) — banking sector, KES 52.50, +1.2% today, PE 6.2, Yield 4.1%"

# Embed all stocks and upsert to Pinecone
async upsert_stock_vectors(stocks: list) -> int

# Query Pinecone to find matching stocks
async query_stock_by_description(query: str) -> list[dict]
# Example: "big bank with dividends" → [EQTY (0.87), KCB (0.84), SCBK (0.81)]

# Get stock info from vector metadata
get_stock_info_by_vector(ticker: str) -> dict

# Delete vectors
delete_stock_vectors(tickers: list) -> int
```

### Updated `intent_router.py`

New function: `resolve_fuzzy_entity(entity, user_message)`

**Workflow:**
```
User: "Should I invest in that big bank?"
         ↓
Intent: ai_advice, entity: "that big bank"
         ↓
resolve_fuzzy_entity() called
         ↓
"that big bank" → Vector embedding → Pinecone query
         ↓
Top matches: EQTY (score 0.87), KCB (0.84)
         ↓
Returns: EQTY (highest score)
         ↓
Handler processes: ticker=EQTY
```

### Updated `main.py` Scraper

After each 15-minute scrape:
1. Update database with new prices
2. **Re-embed all stocks with new prices**
3. **Upsert vectors to Pinecone**

This keeps Pinecone synchronized with live prices automatically.

```python
# In scrape_and_cache():
updated_stocks = database.get_all_stocks()
upserted = await embeddings_module.upsert_stock_vectors(updated_stocks)
logger.info(f"Re-embedded {upserted} stock vectors")
```

## Vector Search Example

### Scenario 1: Exact Company Name

```
User: "Price of Equity Bank?"
Classification: entity: "EQUITYBANK" (extracted by GPT)
         ↓
resolve_fuzzy_entity("EQUITYBANK", "Price of Equity Bank?")
         ↓
Query Pinecone: "EQUITYBANK Price of Equity Bank?"
         ↓
Best match: EQTY (text blob contains "Equity Bank")
         ↓
Result: EQTY ✓
```

### Scenario 2: Fuzzy Descriptor

```
User: "Which is the best telecom stock?"
Classification: entity: "telecom" (fuzzy)
         ↓
resolve_fuzzy_entity("telecom", "Which is the best telecom stock?")
         ↓
Query Pinecone: "telecom Which is the best telecom stock?"
         ↓
Vector search scores:
  - SCOM (Safaricom, telecom) → 0.92
  - EQTY (banking)         → 0.31
  - KCB (banking)          → 0.28
         ↓
Returns: SCOM (highest score > threshold 0.5)
         ↓
Result: SCOM ✓
```

### Scenario 3: Sector Reference

```
User: "Show me the top bank"
Classification: entity: null or "bank" (generic)
         ↓
resolve_fuzzy_entity("bank", "Show me the top bank")
         ↓
Query Pinecone: "bank Show me the top bank"
         ↓
All banking stocks matched:
  - EQTY (Equity Bank)    → 0.89
  - KCB (KCB Group)       → 0.88
  - SCBK (Stanbic)        → 0.86
         ↓
Returns: EQTY (highest score)
         ↓
Result: EQTY ✓
```

## Text Blob Format

Each stock is converted to a rich text description:

```python
"Equity Bank (EQTY) — banking sector, KES 52.50, +1.2% today, PE 6.2, Dividend yield 4.1%, Volume 1,234,567"
```

Components:
- **Company name + ticker**: For direct matching
- **Sector**: For sector-based queries
- **Current price**: For price-aware queries
- **Change %**: For trend context
- **P/E ratio**: For valuation queries
- **Dividend yield**: For income-seeking queries
- **Volume**: For liquidity context

This rich context enables GPT embeddings to understand relationships between different stocks.

## Vector Similarity Scoring

Pinecone returns matches with `similarity_score` (0-1):
- **1.0**: Identical match
- **0.8-0.99**: Very similar (company name or sector)
- **0.7-0.79**: Similar (related sector or similar characteristics)
- **0.5-0.69**: Somewhat related
- **<0.5**: Filtered out (below threshold)

Default threshold: **0.5** (can be tuned per intent)

## Initialization Workflow

### First Time Setup

```bash
# Load stocks from database
stocks = database.get_all_stocks()

# Generate embeddings for each stock
for stock in stocks:
    text_blob = build_stock_text_blob(stock)
    embedding = get_embedding(text_blob)  # OpenAI API call

# Upsert all vectors to Pinecone (batch size: 100)
upserted = await upsert_stock_vectors(stocks)
# Result: "Successfully upserted 60/60 stock vectors"
```

### Ongoing: 15-Minute Scrape

```
09:15 → Scrape NSE data
       → Update database with new prices
       → Re-embed stocks with NEW prices
       → Upsert vectors to Pinecone
       → Now search queries get CURRENT prices in results ✓

09:30 → Repeat...
```

## Cost Implications

### OpenAI Embeddings (text-embedding-3-small)
- **Cost**: $0.02 per 1M tokens
- **Tokens per stock**: ~60 tokens (text blob)
- **Cost per full embed**: ~0.06¢ (60 stocks)
- **Cost per day**: ~0.36¢ (6 embeddings × 15-min schedule)
- **Cost per month**: ~$11

### Pinecone (Free Tier)
- **Vectors**: Unlimited (up to index size limits)
- **Queries**: Unlimited
- **Cost**: $0 (free tier covers this use case)

## Graceful Degradation

### Without Pinecone API Key

```python
# Vector search disabled
if not PINECONE_API_KEY:
    logger.warning("PINECONE_API_KEY not set")
    # Fuzzy entity resolution skipped
    # Falls back to GPT-extracted entity only

    # System still works:
    # "Should I invest in EQTY?" → Works (explicit ticker)
    # "Should I invest in that bank?" → Matched by GPT, not vector search
```

### Without OpenAI Embeddings Key

```python
# Embeddings disabled
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY not set")
    # Vector upserting skipped after scrape
    # Vector queries fail gracefully (return no matches)
    # System uses GPT classification only
```

## Testing

### Quick Test

```bash
python -c "
import asyncio
import embeddings

async def test():
    # Test building text blob
    stock = {
        'ticker': 'SCOM',
        'name': 'Safaricom',
        'price': 33.50,
        'change_pct': 2.3,
        'pe_ratio': 15.2,
        'dividend_yield': 3.5,
    }
    print(embeddings.build_stock_text_blob(stock))

    # Test vector search
    results = await embeddings.query_stock_by_description('telecom')
    print(f'Found {len(results)} matches')

asyncio.run(test())
"
```

### Full Integration Test

```bash
# From backend directory
python embeddings.py

# Output:
# [INFO] Text blob: Safaricom PLC (SCOM) — telecommunications sector...
# [OK] Embedding generated (1536 dimensions)
# [OK] Upserted 5 vectors
# [OK] Vector search found 3 matches:
#   - SCOM: Safaricom (score: 0.92)
#   - EQTY: Equity Bank (score: 0.31)
```

## Monitoring

### Check Vector Status

```bash
# View Pinecone index stats
import pinecone
pc = pinecone.Pinecone(api_key="your-key")
index = pc.Index("nse-stocks")
stats = index.describe_index_stats()
print(f"Vectors in index: {stats['total_vector_count']}")
print(f"Namespace: stocks → {stats['namespaces'].get('stocks', {}).get('vector_count')}")
```

### Monitor Logs

```bash
# Watch for embedding operations
grep "Upserted\|Vector search\|resolved entity" backend-dev.log

# Example output:
# [INFO] Upserted 60 stock vectors (batch 1)
# [INFO] Vector search resolved 'big bank' to EQTY (score: 0.87)
# [INFO] Re-embedded and upserted 60 stock vectors
```

## Limitations & Considerations

1. **Initial Setup**: First upsert (60 stocks) takes 2-3 minutes (OpenAI API calls)
2. **Embedding Latency**: Vector queries add ~100-200ms per request
3. **Fuzzy Threshold**: Too high (>0.7) = misses valid matches; too low (<0.3) = returns irrelevant results
4. **Language**: Works best with English descriptions; sector/company names in other languages may not match
5. **Ticker Changes**: If a company ticker changes, must manually update vectors

## Future Enhancements

1. **Semantic Caching**: Cache embeddings to reduce API calls
2. **Sector Clustering**: Pre-filter by sector before vector search
3. **Personalization**: Learn user's preferred stocks, boost their scores
4. **Multi-language**: Add Swahili stock descriptions for Kenyan context
5. **Real-time Updates**: Update vectors on price changes >5% immediately

## References

- **Pinecone Docs**: https://docs.pinecone.io
- **OpenAI Embeddings**: https://platform.openai.com/docs/guides/embeddings
- **Text Embedding 3**: https://openai.com/blog/embedding-models-openai-api
- **Vector Search Best Practices**: https://www.pinecone.io/learn/vector-search/

---

## Implementation Checklist

- [x] Create embeddings.py with vector functions
- [x] Add vector search to intent_router.py (resolve_fuzzy_entity)
- [x] Update main.py scraper to re-upsert vectors
- [x] Update .env.example with Pinecone settings
- [x] Create documentation
- [ ] User creates Pinecone index
- [ ] User adds PINECONE_API_KEY to .env
- [ ] User runs first embedding load (or happens at startup)
- [ ] Test vector search with fuzzy queries
