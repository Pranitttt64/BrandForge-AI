# BrandForge AI — Development Plan

**Version:** 1.0  
**Approach:** Backend-first, then frontend, then integration

---

## Overview

| Phase | Focus | Duration | Deliverable |
|---|---|---|---|
| Phase 0 | Setup & scaffolding | Day 1 | Repo, env, both servers running |
| Phase 1 | Scraper + Brand Extractor | Days 2-4 | URL → brand_profile.json working |
| Phase 2 | RAG pipeline | Days 5-6 | ChromaDB ingestion + retrieval working |
| Phase 3 | LangGraph agents (sequential) | Days 7-10 | All 4 agents + critic working |
| Phase 4 | Asset generation | Days 11-13 | PDF + PNG + HTML outputs working |
| Phase 5 | FastAPI + SSE | Days 14-15 | Full backend API with streaming |
| Phase 6 | Frontend — core | Days 16-19 | All 3 pages, SSE connected |
| Phase 7 | Polish + integration | Days 20-23 | End-to-end working, UI complete |
| Phase 8 | Deploy + portfolio write-up | Days 24-26 | Live on Vercel + Railway |

**Total: ~3.5 weeks** (working a few hours/day)

---

## Phase 0 — Setup & Scaffolding (Day 1)

### Goals
- Repo created, both servers run locally
- Environment variables set up
- All dependencies installed

### Steps

**1. Create repo structure**
```bash
mkdir brandforge-ai && cd brandforge-ai
git init

# Backend
mkdir -p backend/pipeline/nodes backend/rag backend/llm backend/assets/flyer_templates backend/assets/email_templates
touch backend/main.py backend/job_manager.py backend/requirements.txt backend/.env

# Frontend
npx create-next-app@latest frontend --typescript --tailwind --app --no-src-dir
cd frontend && npx shadcn@latest init
```

**2. Backend dependencies**
```txt
# backend/requirements.txt
fastapi==0.115.0
uvicorn[standard]==0.30.0
python-dotenv==1.0.0
httpx==0.27.0
playwright==1.45.0
beautifulsoup4==4.12.3
langchain==0.3.0
langchain-groq==0.2.0
langchain-google-genai==2.0.0
langchain-community==0.3.0
langgraph==0.2.0
chromadb==0.5.0
sentence-transformers==3.0.0
langchain-huggingface==0.1.0
pillow==10.4.0
python-multipart==0.0.9
aiofiles==24.1.0
```

```bash
pip install -r requirements.txt
playwright install chromium
```

**3. Frontend dependencies**
```bash
cd frontend
npm install framer-motion lucide-react
npx shadcn@latest add button badge tabs card input toast
```

**4. Verify both servers start**
```bash
# Terminal 1
cd backend && uvicorn main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
```

**Checkpoint:** `localhost:3000` and `localhost:8000/docs` both load. ✓

---

## Phase 1 — Scraper + Brand Extractor (Days 2-4)

### Goal
`scrape_and_extract("https://stripe.com")` → returns a `brand_profile` dict

### Day 2: Scraper Node

**File:** `backend/pipeline/nodes/scraper.py`

```python
# What to build:
# 1. Jina Reader primary: GET https://r.jina.ai/{url}
# 2. Playwright fallback
# 3. BeautifulSoup text + CSS extraction
# 4. Internal link discovery (up to 5 pages)
# 5. Return: { url: html_content } dict
```

**Test it:**
```python
# test_scraper.py
from pipeline.nodes.scraper import scraper_node
from pipeline.state import BrandForgeState

state = BrandForgeState(url="https://notion.so", job_id="test-001", ...)
result = scraper_node(state)
print(result["raw_pages"].keys())  # Should show 3-5 URLs
print(len(result["raw_pages"]["https://notion.so"]))  # Should be > 1000 chars
```

### Day 3: Color Extractor (deterministic)

**File:** `backend/pipeline/nodes/brand_extractor.py` (color part)

```python
# What to build:
# extract_colors_from_html(html) → list of hex strings
# Test against 3 different sites
# Verify: colors extracted match what you see visually
```

**Test it manually:** Run against `stripe.com`, `notion.so`, `linear.app` — verify the colors look right.

### Day 4: LLM Brand Extractor

**File:** `backend/pipeline/nodes/brand_extractor.py` (LLM part)  
**File:** `backend/llm/client.py` — set up Groq client  
**File:** `backend/llm/prompts.py` — brand extraction prompt

```python
# Prompt to use (save in prompts.py):
BRAND_EXTRACTION_PROMPT = """
You are a brand analyst. Analyze the following website content and extract brand information.

Website content:
{content}

Return ONLY a valid JSON object with these exact keys:
{{
  "brand_name": "string",
  "tagline": "string (one sentence)",
  "brand_tone": "one of: professional | bold | playful | minimal | luxurious | friendly",
  "target_audience": "string (one sentence describing who this is for)",
  "usps": ["string", "string", "string"],
  "product_categories": ["string"],
  "brand_category": "one of: SaaS | Retail | NGO | Food | Health | Agency | Other"
}}

No markdown. No explanation. JSON only.
"""
```

**Test it:**
```python
# test_extractor.py
from pipeline.nodes.brand_extractor import brand_extractor_node
result = brand_extractor_node(state_after_scraping)
print(result["brand_profile"])
# Verify: JSON is valid, all keys present, values make sense
```

**Checkpoint:** Given `stripe.com`, you get a brand_profile with accurate name, tone, USPs. ✓

---

## Phase 2 — RAG Pipeline (Days 5-6)

### Goal
ChromaDB stores brand content; RAG queries return relevant context

### Day 5: Embeddings + ChromaDB Setup

**File:** `backend/rag/chroma_client.py`
**File:** `backend/rag/embedder.py`
**File:** `backend/pipeline/nodes/rag_ingestor.py`

```python
# What to build:
# 1. HuggingFaceEmbeddings with all-MiniLM-L6-v2
# 2. ChromaDB PersistentClient at ./chroma_store
# 3. Ingestor: chunk text → embed → store with metadata
# 4. Handle duplicate ingestion (check if collection exists)
```

**Note:** First run downloads the model (~80MB). Subsequent runs use cache.

### Day 6: RAG Retriever + Test

**File:** `backend/rag/retriever.py`

```python
def query_brand(collection_id: str, question: str, k: int = 4) -> str:
    # Load collection, similarity search, return joined context
```

**Test it:**
```python
# After ingesting stripe.com:
context = query_brand("brand_test-001", "What problems does this company solve?")
print(context)
# Should return text about payment processing, fraud, etc.

context = query_brand("brand_test-001", "What is the brand tone and style?")
print(context)
# Should return text about their design philosophy, copy style
```

**Checkpoint:** RAG queries return relevant brand content, not random chunks. ✓

---

## Phase 3 — LangGraph Agents (Days 7-10)

### Goal
Full LangGraph graph runs: scrape → extract → ingest → 4 parallel agents → critic

### Day 7: LangGraph Graph Structure

**File:** `backend/pipeline/graph.py`  
**File:** `backend/pipeline/state.py`

```python
# What to build:
# 1. BrandForgeState TypedDict (full definition from ARCHITECTURE.md)
# 2. StateGraph with all nodes added
# 3. Edges defined (including parallel fan-out with Send())
# 4. Graph compiled but agents can be stubs that return dummy data

from langgraph.graph import StateGraph, END
from langgraph.constants import Send

def route_to_parallel(state):
    return [
        Send("copywriter", state),
        Send("layout_agent", state),
        Send("email_agent", state),
        Send("ad_agent", state),
    ]

builder = StateGraph(BrandForgeState)
builder.add_node("scraper", scraper_node)
builder.add_node("brand_extractor", brand_extractor_node)
builder.add_node("rag_ingestor", rag_ingestor_node)
builder.add_node("copywriter", copywriter_node)
builder.add_node("layout_agent", layout_node)
builder.add_node("email_agent", email_node)
builder.add_node("ad_agent", ad_node)
builder.add_node("critic", critic_node)
builder.add_node("asset_generator", asset_generator_node)
builder.add_node("zip_packager", zip_packager_node)

builder.set_entry_point("scraper")
builder.add_edge("scraper", "brand_extractor")
builder.add_edge("brand_extractor", "rag_ingestor")
builder.add_conditional_edges("rag_ingestor", route_to_parallel, 
                               ["copywriter", "layout_agent", "email_agent", "ad_agent"])
builder.add_edge("copywriter", "critic")
builder.add_edge("layout_agent", "critic")
builder.add_edge("email_agent", "critic")
builder.add_edge("ad_agent", "critic")
builder.add_edge("critic", "asset_generator")
builder.add_edge("asset_generator", "zip_packager")
builder.add_edge("zip_packager", END)

graph = builder.compile()
```

**Test with stubs:** Run the graph with dummy node functions. Verify the execution order is correct.

### Day 8: Copywriter + Layout Agents

**File:** `backend/pipeline/nodes/copywriter.py`  
**File:** `backend/pipeline/nodes/layout_agent.py`  
**File:** `backend/llm/prompts.py` (add prompts)

Build each agent as:
1. RAG query for relevant context
2. Build prompt with context + brand profile
3. LLM call (Groq)
4. Parse JSON response
5. Write to state

**Test each independently** before wiring into graph.

### Day 9: Email + Ad Agents

**File:** `backend/pipeline/nodes/email_agent.py`  
**File:** `backend/pipeline/nodes/ad_agent.py`

Same pattern as Day 8.

**Common issue to watch for:** Groq rate limits when testing all agents sequentially. Add `asyncio.sleep(1)` between calls during testing, or use Gemini fallback.

### Day 10: Critic Agent

**File:** `backend/pipeline/nodes/critic.py`

```python
# Critic reviews each agent's output:
# - Check tone consistency against brand_tone
# - Check no hallucinated product names (verify against brand_profile)
# - Check format compliance (ad char limits)
# - For each failure: attempt one inline revision
# - Set critic_approved = True (always in MVP — log issues but don't block)

CRITIC_PROMPT = """
You are a brand consistency critic. Review this marketing copy for {brand_name}.

Brand tone should be: {brand_tone}
Known products/services: {product_categories}

Copy to review:
{copy_output}

Return JSON:
{{
  "approved": true/false,
  "issues": ["issue 1", "issue 2"],
  "revised_copy": {{ ... }}  // only if approved=false, provide corrected version
}}
"""
```

**Checkpoint:** Full graph runs end-to-end. Input URL, get back structured copy output. ✓

---

## Phase 4 — Asset Generation (Days 11-13)

### Goal
Given brand_profile + copy_output → generate actual files (PDF, PNG, HTML)

### Day 11: Flyer PDF

**File:** `backend/pipeline/nodes/asset_generator.py`  
**File:** `backend/assets/flyer_templates/hero_left.html` (and 3 others)

**HTML Template Pattern:**
```html
<!-- flyer_templates/hero_left.html -->
<!DOCTYPE html>
<html>
<head>
<style>
  :root {
    --primary: {{PRIMARY_COLOR}};
    --secondary: {{SECONDARY_COLOR}};
    --accent: {{ACCENT_COLOR}};
    --bg: {{BG_COLOR}};
    --text: {{TEXT_COLOR}};
  }
  /* ... rest of styles */
</style>
</head>
<body>
  <div class="flyer">
    <h1>{{HEADLINE}}</h1>
    <p class="tagline">{{TAGLINE}}</p>
    <ul class="usps">
      {{USP_LIST}}
    </ul>
    <div class="cta">{{CTA_TEXT}}</div>
  </div>
</body>
</html>
```

**Render to PDF:**
```python
from playwright.async_api import async_playwright

async def render_html_to_pdf(html_content: str, output_path: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html_content)
        await page.pdf(path=output_path, format="A4", print_background=True)
        await browser.close()
```

### Day 12: Social Card (Pillow)

**File:** `backend/pipeline/nodes/asset_generator.py` (add to existing)

```python
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

def generate_social_card(brand_profile, copy_output, output_path):
    # Canvas: 1080x1080
    img = Image.new('RGB', (1080, 1080), color=brand_profile['colors']['background'])
    draw = ImageDraw.Draw(img)
    
    # Accent bar (top)
    draw.rectangle([0, 0, 1080, 12], fill=brand_profile['colors']['accent'])
    
    # Brand name (large)
    # Headline (medium)
    # Tagline (small)
    # Bottom accent bar
    
    img.save(output_path, 'PNG', quality=95)
```

**Font handling:** Download a Google Font (e.g. Syne) at startup, cache locally. Use PIL ImageFont.truetype.

### Day 13: Email HTML + Ad Copy PDF

**Email:** Simple string templating — inject copy into base HTML email template. Test renders correctly in a browser.

**Ad Copy PDF:** Generate a Markdown string → render via Playwright (same pattern as flyer).

**Checkpoint:** Given a real brand URL, you get actual downloadable files. Open them — do they look right? ✓

---

## Phase 5 — FastAPI + SSE (Days 14-15)

### Goal
Full HTTP API working. Frontend can trigger pipeline and stream events.

### Day 14: API Routes + Job Manager

**File:** `backend/main.py`
**File:** `backend/job_manager.py`

```python
# main.py structure
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="BrandForge API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], ...)

@app.post("/api/forge")           # Start pipeline → return job_id
@app.get("/api/forge/{job_id}/stream")   # SSE stream
@app.get("/api/forge/{job_id}/result")   # Full result JSON
@app.get("/api/forge/{job_id}/download") # ZIP download
```

```python
# job_manager.py
# asyncio.Queue per job_id for SSE events
# Background task runs LangGraph graph
# Each node emits events to queue

jobs: dict[str, asyncio.Queue] = {}

async def run_pipeline(job_id: str, url: str):
    queue = jobs[job_id]
    # Modify graph nodes to emit to queue
    # Run graph
    # Emit completion event
```

**SSE trick:** LangGraph doesn't natively emit to queues. Pattern: pass the queue into each node via the state (add `event_queue` to BrandForgeState), and have each node call `await state['event_queue'].put(event)`.

### Day 15: Integration Test

Run full pipeline via API:
```bash
curl -X POST http://localhost:8000/api/forge \
  -H "Content-Type: application/json" \
  -d '{"url": "https://linear.app"}'
# → {"job_id": "abc-1234"}

curl http://localhost:8000/api/forge/abc-1234/stream
# → watch SSE events stream in terminal
```

**Checkpoint:** Full pipeline runs via HTTP. Events stream correctly. ZIP downloads. ✓

---

## Phase 6 — Frontend Core (Days 16-19)

### Goal
All 3 pages built and connected to backend

### Day 16: Landing Page

**Files:** `frontend/app/page.tsx`, `frontend/components/home/Hero.tsx`

**Implementation details:**
> "Build the landing page for BrandForge AI. Dark theme (#0a0a0a background, #f59e0b amber accent). Font: Syne (Google Font) for headings, Inter for body. Hero section: large H1 'Turn any URL into a complete brand kit.', subtext, a URL input field with amber focus ring, and a 'Forge Brand Kit' button. Below: a 'How it Works' section with 4 steps. Use Framer Motion for staggered entrance animations. Tailwind for layout."

### Day 17: Forge Page (Pipeline View)

**Files:** `frontend/app/forge/[jobId]/page.tsx`, `frontend/components/forge/AgentTimeline.tsx`

This is the hardest frontend component. Build the SSE hook first, then the UI around it.

```typescript
// Start with this hook, test it returns events
function useAgentStream(jobId: string) { ... }

// Then build AgentTimeline that visualizes the state
// Then add BrandProfile that appears when brand_extraction completes
```

### Day 18: Preview / Download Page

**Files:** `frontend/app/forge/[jobId]/preview/page.tsx`

Tabs for each asset, preview rendering, download button.

### Day 19: Polish + Error States

Add all error states (see UI_DESIGN.md §9). Add loading skeletons. Test on all 3 pages.

**Checkpoint:** Full frontend working against live backend. ✓

---

## Phase 7 — Integration Polish (Days 20-23)

### Day 20: End-to-End Test (3 real URLs)

Test against: `stripe.com`, `notion.so`, one smaller brand website.

For each, verify:
- [ ] Scraping succeeds (or fallback works)
- [ ] Brand profile looks accurate
- [ ] Copy output is on-brand
- [ ] PDF renders without CSS issues
- [ ] Social card looks good
- [ ] ZIP downloads and contains all files

Fix whatever breaks.

### Day 21: Timing + Performance

- Measure total pipeline time
- If > 3 min: identify bottleneck (usually embeddings on first run or sequential LLM calls)
- Add Groq → Gemini fallback if rate limiting
- Pre-warm embedding model on startup

### Day 22: UI Animations + Final Design

- Implement all Framer Motion animations from UI_DESIGN.md §7
- Color palette swatches on brand profile
- Copy button for ad copy lines
- Confetti on download

### Day 23: README + Demo Prep

Write `README.md` with:
- Project description (portfolio-quality writing)
- Architecture diagram (copy from ARCHITECTURE.md)
- Tech stack table
- Setup instructions (should work in < 5 commands)
- Screenshots / GIF of the pipeline running

---

## Phase 8 — Deploy (Days 24-26)

### Frontend → Vercel

```bash
cd frontend
vercel deploy
# Set environment variable: NEXT_PUBLIC_API_URL=https://your-backend.railway.app
```

### Backend → Railway

```bash
# Add Dockerfile to backend/
# Railway auto-detects and deploys
# Set environment variables in Railway dashboard:
# GROQ_API_KEY, GEMINI_API_KEY, etc.
```

**Note:** ChromaDB on Railway uses ephemeral storage — data resets on redeploy. For demo purposes this is fine (just re-run a URL). For production you'd use Railway's persistent volume.

**Checkpoint:** Live URLs working. Share on GitHub with good README. ✓

---

## Testing Checklist (before sharing portfolio)

### Functional
- [ ] 3 different URLs produce correct brand profiles
- [ ] All 4 agents produce output
- [ ] Critic agent produces feedback JSON
- [ ] PDF flyer renders with correct brand colors
- [ ] Social card PNG looks visually correct
- [ ] ZIP contains all expected files
- [ ] SSE stream shows all stages
- [ ] Frontend auto-navigates to preview on completion

### Edge Cases
- [ ] Invalid URL → clear error message
- [ ] Blocked site → fallback works or graceful error
- [ ] LLM rate limit → Gemini fallback activates
- [ ] Very small website (1 page) → still works

### UI
- [ ] All 3 pages load without errors
- [ ] Animations run smoothly
- [ ] Mobile layout acceptable
- [ ] Download button works

---

## Portfolio Write-Up Outline (for Germany applications)

**Title:** BrandForge AI — Autonomous Brand Intelligence System

**Abstract (3 sentences):**
BrandForge AI is an end-to-end multi-agent system that transforms any company website URL into a complete marketing brand kit. The system employs a 7-node LangGraph pipeline with a RAG layer (ChromaDB + sentence-transformers) that gives LLM agents deep brand knowledge before generating copy, layouts, and visual assets. The architecture demonstrates practical application of agentic AI, retrieval-augmented generation, and real-time streaming in a production-grade system.

**Sections to cover:**
1. Problem & motivation
2. System architecture (reference ARCHITECTURE.md diagram)
3. Multi-agent design decisions (why LangGraph, fan-out pattern)
4. RAG pipeline design
5. Technical challenges & solutions (scraping reliability, LLM fallback)
6. Results (screenshots, example outputs)
7. Future work (Stable Diffusion, user accounts, competitive analysis)
