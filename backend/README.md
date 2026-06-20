# BrandForge AI — Backend

FastAPI + LangGraph pipeline. See root [README.md](../README.md) for full project overview.

## Run locally

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env  # add your API keys
python main.py
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/forge` | Start a new brand kit generation job |
| GET | `/api/forge/{job_id}/stream` | SSE stream of pipeline progress |
| GET | `/api/forge/{job_id}/result` | Full structured result once complete |
| GET | `/api/forge/{job_id}/download` | Download the ZIP brand kit |
| GET | `/api/forge/{job_id}/assets/{filename}` | Preview individual assets |
| POST | `/api/validate-url` | Pre-flight URL reachability check |
| GET | `/health` | Health check |

## Pipeline Stages

1. `scraper` — Real link discovery + Jina/Playwright scraping
2. `brand_extractor` — LLM extraction + deterministic color parsing
3. `rag_ingestor` — Chunk, embed, store in ChromaDB
4. `copywriter` / `layout_agent` / `email_agent` / `ad_agent` — parallel
5. `critic` — Quality and tone validation
6. `asset_generator` — Playwright HTML→PDF/PNG rendering
7. `zip_packager` — Final bundle creation

## Environment Variables

See `.env.example` for all required and optional variables.
