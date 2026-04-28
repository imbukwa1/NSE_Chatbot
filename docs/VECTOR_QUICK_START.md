# Quick Start: Pinecone Vector Memory Integration

## 5-Minute Setup

### Step 1: Create Pinecone Index
1. Visit [pinecone.io](https://pinecone.io) → Sign up (free)
2. Create Index:
   - Name: `nse-stocks`
   - Dimension: `1536`
   - Metric: `cosine`
3. Copy **API Key** from dashboard

### Step 2: Update .env
```bash
# Add to backend/.env
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_STOCKS_INDEX=nse-stocks
PINECONE_STOCKS_NAMESPACE=stocks
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

### Step 3: Initialize Vectors (One-time)
```bash
cd backend
python -c "
import asyncio
import database
import embeddings

async def init():
    stocks = database.get_all_stocks()
    print(f'Loading {len(stocks)} stocks...')
    result = await embeddings.upsert_stock_vectors(stocks)
    print(f'✓ Upserted {result} vectors to Pinecone')

asyncio.run(init())
"
```

## How It Works

### Fuzzy Entity Matching

```
User Query                    Classification              Vector Search
"Big bank?"         →         intent: ai_advice      →    EQTY (0.87)
                                entity: "bank"              KCB (0.84)
                                                             SCBK (0.81)
                                                      ↓
                                        resolve_fuzzy_entity()
                                                      ↓
                                        Returns EQTY (highest match)

User Query                    Classification              No Vec Search Needed
"EQTY price?"       →         intent: price_lookup   →    Already clear ticker
                                entity: "EQTY"             Use directly ✓
```

### Automatic Updates

Every 15 minutes at 09:15, 09:30, 09:45, etc. (during trading hours):
```
1. Scrape live NSE prices
2. Update database
3. Re-embed all stocks with NEW prices
4. Upsert vectors to Pinecone
5. Vector queries now return CURRENT prices ✓
```

## Testing

### Test 1: Basic Import
```bash
python -c "import embeddings; print('✓ OK')"
```

### Test 2: Build Text Blob
```bash
python -c "
import database
import embeddings
stocks = database.get_all_stocks()
if stocks:
    blob = embeddings.build_stock_text_blob(stocks[0])
    print(blob)
"
```

### Test 3: Query Vector Search
```bash
python -c "
import asyncio
import embeddings

async def test():
    results = await embeddings.query_stock_by_description('telecom')
    for r in results[:3]:
        print(f'{r[\"ticker\"]}: {r[\"name\"]} ({r[\"similarity_score\"]:.2f})')

asyncio.run(test())
"
```

## Production Checklist

- [ ] Pinecone index created (nse-stocks)
- [ ] PINECONE_API_KEY added to .env
- [ ] OPENAI_API_KEY in .env (required for embeddings)
- [ ] First vector load completed (`upsert_stock_vectors()`)
- [ ] Test fuzzy query: "big bank" → matches EQTY/KCB
- [ ] Test explicit ticker: "SCOM price" → works as before
- [ ] Verify logs show "Upserted X vectors" after scrape
- [ ] Monitor cost: Should be <$15/month with 60 stocks

## Common Issues

### Issue: "PINECONE_API_KEY not set"
**Solution**: Add to .env and restart

### Issue: Vector queries return empty
**Solution**: Run initial `upsert_stock_vectors()` to load stocks

### Issue: "Invalid dimension 1536"
**Solution**: Check your Pinecone index dimension matches (should be 1536)

### Issue: "No matches found" for fuzzy query
**Solution**: Lower threshold in `query_stock_by_description(threshold=0.3)`, or try more specific query

## Architecture Files

| File | Purpose |
|------|---------|
| `embeddings.py` | Vector embedding & Pinecone operations |
| `intent_router.py` | Fuzzy entity resolution using vectors |
| `main.py` | Scraper integration to auto-upsert |
| `PINECONE_VECTOR_MEMORY.md` | Full documentation |

## Cost Summary

- **Pinecone**: Free tier (unlimited vectors & queries)
- **OpenAI Embeddings**: ~$11/month (60 stocks × 6 daily reloads)
- **Total**: ~$11/month for auto-updating vectors

## Monitoring

Watch logs for:
```
[INFO] Upserted X stock vectors      ← Successful vector load
[INFO] Vector search resolved X to Y  ← Fuzzy match working
[ERROR] Failed to upsert             ← Check API key/index
```

---

**Next**: Head to [PINECONE_VECTOR_MEMORY.md](PINECONE_VECTOR_MEMORY.md) for deep dive.
