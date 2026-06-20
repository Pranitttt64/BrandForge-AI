# BrandForge AI — Architecture Document

**Version:** 1.0

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    NEXT.JS FRONTEND                      │
│         (Vercel) — REST + SSE ← → FastAPI               │
└─────────────────────────┬───────────────────────────────┘
                          │ HTTP / SSE
┌─────────────────────────▼───────────────────────────────┐
│                    FASTAPI BACKEND                       │
│                   (Railway / Local)                      │
│  ┌──────────────────────────────────────────────────┐   │
│  │              JOB MANAGER (asyncio)               │   │
│  │   Accepts URL → spawns LangGraph pipeline        │   │
│  │   Streams SSE events → client                    │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                                │
│  ┌──────────────────────▼───────────────────────────┐   │
│  │           LANGGRAPH PIPELINE (core)              │   │
│  │                                                  │   │
│  │  [Scraper] → [Extractor] → [Ingestor]            │   │
│  │                                ↓                 │   │
│  │              ┌─────────────────────────────┐     │   │
│  │              │      PARALLEL FAN-OUT       │     │   │
│  │         [Copywriter] [Layout] [Email] [Ad] │     │   │
│  │              └──────────┬──────────────────┘     │   │
│  │                         ↓                        │   │
│  │                   [Critic Agent]                 │   │
│  │                         ↓                        │   │
│  │                [Asset Generator]                 │   │
│  │                         ↓                        │   │
│  │                  [ZIP Packager]                  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────┐   │
│  │  ChromaDB    │  │  Groq / Gemini │  │   Pillow +  │   │
│  │  (vectors)   │  │  (LLM calls)  │  │  Playwright │   │
│  └──────────────┘  └───────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 2. LangGraph Agent Pipeline (Detailed)

### 2.1 State Schema

The entire pipeline shares a typed state dict. Every node reads from and writes to this state.

```python
from typing import TypedDict, Optional, List
from dataclasses import dataclass

@dataclass
class BrandColors:
    primary: str      # hex
    secondary: str    # hex
    accent: str       # hex
    background: str   # hex
    text: str         # hex

class BrandForgeState(TypedDict):
    # Input
    url: str
    job_id: str

    # Stage 1: Scraping
    raw_pages: dict[str, str]        # {url: html_content}
    scrape_status: str               # "pending" | "running" | "done" | "failed"

    # Stage 2: Extraction
    brand_profile: dict              # structured brand JSON
    brand_colors: BrandColors
    brand_tone: str                  # "professional" | "playful" | "bold" | ...
    brand_name: str
    usps: List[str]
    target_audience: str

    # Stage 3: RAG
    chroma_collection_id: str        # ID of this brand's ChromaDB collection

    # Stage 4: Agent Outputs (parallel)
    copy_output: Optional[dict]      # headlines, taglines, CTAs
    layout_output: Optional[dict]    # flyer structure decision
    email_output: Optional[dict]     # email campaign copy
    ad_output: Optional[dict]        # Google + social ad copy

    # Stage 5: Critic Output
    critic_feedback: Optional[dict]  # per-agent approval / revision notes
    critic_approved: bool

    # Stage 6: Assets
    flyer_pdf_path: Optional[str]
    social_card_path: Optional[str]
    email_html_path: Optional[str]
    ad_copy_pdf_path: Optional[str]
    zip_path: Optional[str]

    # Streaming
    events: List[dict]               # SSE event log
    error: Optional[str]
```

### 2.2 Node Definitions

#### Node 1: `scraper_node`
```
Input:  url
Output: raw_pages (dict of page content)

Logic:
  1. Try Jina Reader API: GET https://r.jina.ai/{url}
  2. If Jina fails → fall back to Playwright headless browser
  3. Parse with BeautifulSoup: extract visible text + <style> blocks + <meta> tags
  4. Discover internal links, scrape up to 5 sub-pages
  5. Store raw_pages in state

Emit SSE: { stage: "scraping", status: "running/complete" }
```

#### Node 2: `brand_extractor_node`
```
Input:  raw_pages
Output: brand_profile, brand_colors, brand_tone, usps, target_audience

Logic:
  COLOR EXTRACTION (deterministic, not LLM):
    - Parse CSS from <style> blocks and inline styles
    - Extract hex values from background-color, color, border-color
    - Rank by frequency → top 5 = brand palette
    - Map to roles: primary (most frequent on buttons), secondary, accent

  LLM EXTRACTION (Groq):
    - Prompt: "Given this website content, extract: brand name, one-sentence tagline,
      3-5 USPs, target audience description, brand tone (one word), product categories"
    - Response format: JSON (strict)
    - Parse and validate response

  Store: brand_profile.json

Emit SSE: { stage: "brand_extraction", status: "complete", data: brand_profile }
```

#### Node 3: `rag_ingestor_node`
```
Input:  raw_pages, brand_profile
Output: chroma_collection_id

Logic:
  1. Chunk all page text (chunk_size=500, overlap=50)
  2. Embed with sentence-transformers/all-MiniLM-L6-v2 (local, no API cost)
  3. Store in ChromaDB collection named f"brand_{job_id}"
  4. Add metadata: {page_url, brand_name, job_id}
  5. Return collection ID

Emit SSE: { stage: "rag_ingestion", status: "complete" }
```

#### Nodes 4a-4d: Parallel Creative Agents (Fan-Out)

LangGraph parallel execution using `Send()` API:

```python
# In graph definition:
graph.add_conditional_edges(
    "rag_ingestor",
    lambda state: ["copywriter", "layout", "email_agent", "ad_agent"],
    ["copywriter", "layout", "email_agent", "ad_agent"]
)
```

**4a: `copywriter_agent`**
```
RAG Query: "What makes this brand unique? What problems do they solve?"
Generates:
  - 5 headline options (each ≤8 words)
  - 3 tagline options
  - 3 CTA button texts
  - 5 ad headlines (Google format: ≤30 chars)
  - Copy in 3 tones: bold / friendly / professional
```

**4b: `layout_agent`**
```
RAG Query: "What type of business is this? What is their primary product category?"
Decides:
  - Brand category: SaaS | Retail | NGO | Food | Health | Agency | Other
  - Flyer template: hero-left | hero-top | split-panel | minimal-text
  - Content hierarchy: what goes in hero vs body vs footer
  - Typography mood: geometric | humanist | slab | display
```

**4c: `email_agent`**
```
RAG Query: "What is the brand tone? What are their top USPs? Who is the target audience?"
Generates full copy for:
  - Welcome email (subject + body, 150 words)
  - Promotional email (subject + body, 200 words)
  - Re-engagement email (subject + body, 120 words)
```

**4d: `ad_agent`**
```
RAG Query: "What pain points does this brand address? What is their primary CTA?"
Generates:
  - Google Ads: 3 headlines (≤30 chars) + 2 descriptions (≤90 chars) × 3 variations
  - Instagram caption: 3 variations with hashtag suggestions
  - LinkedIn post: 1 professional post (150 words)
```

#### Node 5: `critic_agent` (Fan-In)
```
Input:  all 4 agent outputs + brand_profile

Reviews each output for:
  1. Tone consistency — does copy match brand_tone?
  2. Accuracy — no hallucinated product names or claims not in RAG?
  3. Format compliance — char limits for ad copy respected?

Output:
  - Per-agent: { approved: bool, issues: [str], revised_copy: optional }
  - If any agent fails: revise inline (one retry), then mark approved

This node does NOT loop back in MVP — one pass with inline revision.
```

#### Node 6: `asset_generator_node`
```
Input:  critic-approved outputs, brand_colors, layout_output

Generates:
  1. FLYER PDF
     - Select HTML template based on layout_output.template
     - Inject: brand_colors (CSS vars), headline, tagline, logo placeholder, USPs
     - Render to PDF via Playwright page.pdf()
     - Output: flyer.pdf

  2. SOCIAL CARD (PNG 1080×1080)
     - Pillow: create canvas with brand_profile.colors.background
     - Draw: brand name (large), tagline (medium), accent bar, USP bullet
     - Font: download Google Font matching typography_mood
     - Output: social_card.png

  3. EMAIL TEMPLATES (HTML)
     - Inject email copy into base HTML email template
     - Brand colors applied via inline styles (email client safe)
     - Output: email_welcome.html, email_promo.html, email_reengagement.html

  4. AD COPY PDF
     - Markdown → PDF via Playwright
     - Output: ad_copy.pdf
```

#### Node 7: `zip_packager_node`
```
Input:  all asset paths
Output: zip_path

Creates: brandforge_kit_{brand_name}_{job_id}.zip
Contains:
  /brand_profile.json
  /assets/flyer.pdf
  /assets/social_card.png
  /assets/email_welcome.html
  /assets/email_promo.html
  /assets/email_reengagement.html
  /assets/ad_copy.pdf
  /README.txt  (explains each file)
```

---

## 3. RAG Pipeline Design

### 3.1 Chunking Strategy
```
- Chunk size: 500 tokens
- Overlap: 50 tokens
- Splitter: RecursiveCharacterTextSplitter
- Per-chunk metadata: { source_url, page_title, brand_name, job_id }
```

### 3.2 Embedding Model
```
Model: sentence-transformers/all-MiniLM-L6-v2
- Runs locally (no API cost)
- 384-dimensional embeddings
- ~14ms per chunk on CPU — fast enough
- LangChain integration: HuggingFaceEmbeddings
```

### 3.3 ChromaDB Setup
```python
import chromadb
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="./chroma_store")

# Per-job collection (isolated per brand)
vectorstore = Chroma(
    client=client,
    collection_name=f"brand_{job_id}",
    embedding_function=embeddings
)
```

### 3.4 RAG Query Pattern (used by every agent)
```python
def query_brand_knowledge(collection_id: str, question: str, k: int = 4) -> str:
    vectorstore = load_collection(collection_id)
    docs = vectorstore.similarity_search(question, k=k)
    context = "\n\n".join([doc.page_content for doc in docs])
    return context

# Agent prompt pattern:
AGENT_PROMPT = """
You are a brand strategist for {brand_name}.

Brand Context (from their website):
{rag_context}

Brand Profile:
- Tone: {brand_tone}
- Target Audience: {target_audience}
- USPs: {usps}

Task: {agent_specific_task}

Respond ONLY in valid JSON. No markdown, no explanation.
"""
```

---

## 4. SSE Streaming Design

### 4.1 FastAPI SSE Endpoint
```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio, json

@app.get("/api/forge/{job_id}/stream")
async def stream_events(job_id: str):
    async def event_generator():
        queue = get_job_queue(job_id)
        while True:
            event = await queue.get()
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("stage") == "complete":
                break
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### 4.2 Event Schema
```json
// Progress event
{ "stage": "copywriter_agent", "status": "running", "message": "Crafting headlines...", "progress": 45 }

// Data event (sends back extracted data for live UI update)
{ "stage": "brand_extraction", "status": "complete", "data": {
    "brand_name": "Acme Corp",
    "colors": ["#1a1a2e", "#e94560", "#0f3460"],
    "tone": "bold",
    "audience": "B2B SaaS buyers"
  }
}

// Error event
{ "stage": "scraping", "status": "error", "message": "Site blocked scraping. Trying fallback..." }

// Completion event
{ "stage": "complete", "status": "complete", "download_url": "/api/forge/uuid-1234/download" }
```

---

## 5. Project File Structure

```
brandforge-ai/
│
├── backend/
│   ├── main.py                    # FastAPI app, routes
│   ├── job_manager.py             # Job queue, SSE event bus
│   ├── requirements.txt
│   ├── .env.example
│   │
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── graph.py               # LangGraph graph definition
│   │   ├── state.py               # BrandForgeState TypedDict
│   │   │
│   │   └── nodes/
│   │       ├── scraper.py         # Node 1: Jina + Playwright
│   │       ├── brand_extractor.py # Node 2: Color + LLM extraction
│   │       ├── rag_ingestor.py    # Node 3: ChromaDB ingestion
│   │       ├── copywriter.py      # Node 4a
│   │       ├── layout_agent.py    # Node 4b
│   │       ├── email_agent.py     # Node 4c
│   │       ├── ad_agent.py        # Node 4d
│   │       ├── critic.py          # Node 5
│   │       ├── asset_generator.py # Node 6
│   │       └── zip_packager.py    # Node 7
│   │
│   ├── rag/
│   │   ├── embedder.py            # HuggingFace embeddings setup
│   │   ├── chroma_client.py       # ChromaDB client singleton
│   │   └── retriever.py           # RAG query helper
│   │
│   ├── llm/
│   │   ├── client.py              # Groq + Gemini with fallback
│   │   └── prompts.py             # All agent prompt templates
│   │
│   ├── assets/
│   │   ├── flyer_templates/       # HTML/CSS flyer templates (4 types)
│   │   ├── email_templates/       # Base HTML email layouts
│   │   └── fonts/                 # Google Fonts cache
│   │
│   ├── chroma_store/              # Local ChromaDB persistence (gitignored)
│   └── outputs/                   # Generated ZIPs (gitignored)
│
├── frontend/
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   │
│   └── src/
│       ├── app/
│       │   ├── page.tsx           # Landing / input page
│       │   ├── forge/[jobId]/
│       │   │   └── page.tsx       # Live progress + results page
│       │   └── layout.tsx
│       │
│       ├── components/
│       │   ├── URLInput.tsx       # Hero input component
│       │   ├── AgentTimeline.tsx  # Live SSE progress feed
│       │   ├── BrandProfile.tsx   # Extracted colors + tone display
│       │   ├── AssetPreview.tsx   # Preview cards for each asset
│       │   ├── DownloadKit.tsx    # ZIP download button
│       │   └── ui/                # shadcn components
│       │
│       └── lib/
│           ├── api.ts             # API client functions
│           └── sse.ts             # SSE hook (useSSE)
│
├── docker-compose.yml             # Local dev: backend + chromadb
├── README.md
└── .gitignore
```

---

## 6. LLM Client with Fallback

```python
# llm/client.py
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
import os

def get_llm(temperature: float = 0.7):
    """Returns Groq primary with Gemini fallback."""
    try:
        return ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=temperature
        )
    except Exception:
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=temperature
        )
```

---

## 7. Color Extraction (Deterministic)

```python
# nodes/brand_extractor.py
import re
from collections import Counter
from bs4 import BeautifulSoup

def extract_colors_from_html(html: str) -> list[str]:
    """Extract hex colors from CSS — never use LLM for this."""
    hex_pattern = r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b'
    
    soup = BeautifulSoup(html, 'html.parser')
    css_text = ""
    
    # Inline styles
    for tag in soup.find_all(style=True):
        css_text += tag['style'] + " "
    
    # <style> blocks
    for style_tag in soup.find_all('style'):
        css_text += style_tag.get_text() + " "
    
    colors = re.findall(hex_pattern, css_text)
    colors = [f"#{c}" if len(c) == 6 else f"#{c*2}" for c in colors]
    
    # Filter near-white and near-black (often defaults)
    filtered = [c for c in colors if c not in ['#ffffff', '#000000', '#fff', '#000']]
    
    # Return top 5 by frequency
    counter = Counter(filtered)
    return [color for color, _ in counter.most_common(5)]
```

---

## 8. Environment Variables

```bash
# .env.example
GROQ_API_KEY=your_groq_key_here
GEMINI_API_KEY=your_gemini_key_here
CHROMA_PERSIST_DIR=./chroma_store
OUTPUT_DIR=./outputs
FRONTEND_URL=http://localhost:3000
MAX_PAGES_TO_SCRAPE=5
```

---

## 9. Key Architectural Decisions & Rationale

| Decision | Alternative Considered | Reason Chosen |
|---|---|---|
| LangGraph over CrewAI | CrewAI | LangGraph exposes the state machine explicitly — better for portfolio, better for debugging |
| Jina Reader primary scraper | Playwright only | Jina handles JS-rendered sites without browser overhead; Playwright as fallback |
| Local sentence-transformers | OpenAI embeddings | No API cost; fast enough on CPU for demo scale |
| ChromaDB local | Pinecone | No cloud dependency; runs offline for demos |
| Playwright for PDF | WeasyPrint | Better CSS support; already in stack for scraping |
| SSE over WebSockets | WebSockets | Simpler, unidirectional — perfect for one-way progress streaming |
| Per-job ChromaDB collection | Single collection | Isolation; easy cleanup; no cross-brand contamination |
