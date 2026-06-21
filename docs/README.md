# Project Documentation

The root [README](../README.md) is the source of truth for installation, startup,
database access, and the Django knowledge-base service.

## Integration Guides

- [Live market scraper](LIVE_SCRAPER_README.md)
- [News integration](NEWS_INTEGRATION.md)
- [Pinecone vector memory](PINECONE_VECTOR_MEMORY.md)
- [Vector quick start](VECTOR_QUICK_START.md)
- [Legacy OpenAI intent-router notes](OPENAI_INTENT_ROUTER.md)

The intent-router guide describes the original OpenAI-compatible design. The active
provider is Featherless and is configured through `FEATHERLESS_*` environment variables.

Generated logs, database files, build output, caches, and local environment files are
runtime artifacts and are intentionally excluded from Git.
