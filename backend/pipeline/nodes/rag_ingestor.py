"""
RAG Ingestor Node — BrandForge AI
Section-aware chunking with rich metadata so the retriever can
surface the right content for each downstream agent.
"""
from __future__ import annotations

import os

os.environ["USE_TF"] = "0"
os.environ["TRANSFORMERS_NO_TF"] = "1"

import re
from typing import Any

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from job_manager import job_manager
from pipeline.state import BrandForgeState
from rag.chroma_client import get_chroma_client
from rag.embedder import get_embeddings


# ---------------------------------------------------------------------------
# Section labels emitted by scraper.py — we parse these to chunk smartly
# ---------------------------------------------------------------------------

SECTION_PATTERNS: list[tuple[str, str]] = [
    # (regex pattern to detect section header, section_type label)
    (r"^\[SOURCE PAGE:",             "source_header"),
    (r"^Page title:",                "title"),
    (r"^OG ",                        "og_meta"),
    (r"^Meta description:",          "meta_description"),
    (r"^Meta keywords:",             "meta_keywords"),
    (r"^Structured data:",           "json_ld"),
    (r"^H1 headlines?:",             "h1"),
    (r"^H2 subheadings?:",           "h2"),
    (r"^H3 sections?:",              "h3"),
    (r"^Body text:",                 "body"),
    (r"^Feature/benefit lists?:",    "features"),
    (r"^CTAs?/Buttons?:",            "cta"),
    (r"^Brand sections?:",           "brand_section"),
    (r"^Testimonials?/Social proof:","testimonial"),
    (r"^Stats? & metrics?:",         "stats"),
    (r"^Pricing/Plans?:",            "pricing"),
    (r"^Footer content:",            "footer"),
    (r"^Jina reader text:",          "jina_text"),
    (r"^Dynamic page text:",         "dynamic_text"),
    (r"^Key numbers?:",              "stats"),
]

# Chunk sizes per section type — short for atomic facts, larger for prose
CHUNK_CONFIG: dict[str, dict[str, Any]] = {
    "title":           {"size": 150,  "overlap": 0},
    "og_meta":         {"size": 200,  "overlap": 0},
    "meta_description":{"size": 200,  "overlap": 0},
    "meta_keywords":   {"size": 150,  "overlap": 0},
    "json_ld":         {"size": 400,  "overlap": 50},
    "h1":              {"size": 200,  "overlap": 0},
    "h2":              {"size": 300,  "overlap": 30},
    "h3":              {"size": 300,  "overlap": 30},
    "body":            {"size": 700,  "overlap": 140},
    "features":        {"size": 500,  "overlap": 80},
    "cta":             {"size": 200,  "overlap": 0},
    "brand_section":   {"size": 800,  "overlap": 150},
    "testimonial":     {"size": 600,  "overlap": 80},
    "stats":           {"size": 300,  "overlap": 30},
    "pricing":         {"size": 600,  "overlap": 80},
    "footer":          {"size": 300,  "overlap": 30},
    "jina_text":       {"size": 700,  "overlap": 120},
    "dynamic_text":    {"size": 700,  "overlap": 120},
    "source_header":   {"size": 100,  "overlap": 0},
    "default":         {"size": 600,  "overlap": 100},
}

# Priority score per section — retriever uses this to rank results
SECTION_PRIORITY: dict[str, int] = {
    "brand_section":    10,
    "features":         9,
    "h1":               9,
    "json_ld":          9,
    "testimonial":      8,
    "pricing":          8,
    "og_meta":          8,
    "meta_description": 7,
    "stats":            7,
    "h2":               7,
    "body":             6,
    "h3":               6,
    "cta":              5,
    "jina_text":        5,
    "dynamic_text":     5,
    "footer":           4,
    "meta_keywords":    4,
    "title":            4,
    "source_header":    1,
    "default":          3,
}


# ---------------------------------------------------------------------------
# Section-aware text parser
# ---------------------------------------------------------------------------

def _detect_section_type(line: str) -> str | None:
    """Return section_type label if this line is a section header, else None."""
    for pattern, label in SECTION_PATTERNS:
        if re.match(pattern, line.strip(), re.IGNORECASE):
            return label
    return None


def _parse_page_into_sections(
    page_text: str,
    page_url: str,
) -> list[dict[str, Any]]:
    """
    Split a scraped page's labeled text into typed sections.
    Each section: {"type": str, "text": str, "url": str}
    """
    sections: list[dict[str, Any]] = []
    lines = page_text.splitlines()

    current_type = "default"
    current_lines: list[str] = []

    def _flush():
        nonlocal current_lines
        text = "\n".join(current_lines).strip()
        if text and len(text) >= 20:
            sections.append({
                "type": current_type,
                "text": text,
                "url": page_url,
            })
        current_lines = []

    for line in lines:
        detected = _detect_section_type(line)
        if detected:
            _flush()
            current_type = detected
            # Include the header line itself as context
            current_lines = [line]
        else:
            current_lines.append(line)

    _flush()
    return sections


def _get_splitter(section_type: str) -> RecursiveCharacterTextSplitter:
    cfg = CHUNK_CONFIG.get(section_type, CHUNK_CONFIG["default"])
    return RecursiveCharacterTextSplitter(
        chunk_size=cfg["size"],
        chunk_overlap=cfg["overlap"],
        length_function=len,
        separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
    )


# ---------------------------------------------------------------------------
# Chunk quality filtering
# ---------------------------------------------------------------------------

def _is_quality_chunk(text: str, section_type: str) -> bool:
    """Return False for chunks that are too short, noisy, or uninformative."""
    text = text.strip()
    if len(text) < 20:
        return False
    # Skip chunks that are just the section label with no content
    if re.match(r"^\[SOURCE PAGE:.*\]$", text):
        return False
    # Skip chunks that are mostly punctuation/symbols
    alpha_ratio = sum(1 for c in text if c.isalpha()) / max(len(text), 1)
    if alpha_ratio < 0.35:
        return False
    # Skip very repetitive chunks
    words = text.lower().split()
    if len(words) > 5:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.25:
            return False
    return True


def _normalize_chunk(text: str) -> str:
    """Clean up whitespace in a chunk without losing structure."""
    lines = [re.sub(r" {2,}", " ", ln).rstrip() for ln in text.splitlines()]
    # Collapse more than 2 consecutive blank lines
    result: list[str] = []
    blanks = 0
    for ln in lines:
        if ln == "":
            blanks += 1
            if blanks <= 2:
                result.append(ln)
        else:
            blanks = 0
            result.append(ln)
    return "\n".join(result).strip()


# ---------------------------------------------------------------------------
# Deduplication before indexing
# ---------------------------------------------------------------------------

def _word_overlap(a: str, b: str) -> float:
    wa = set(a.lower().split())
    wb = set(b.lower().split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / max(len(wa), len(wb))


def _deduplicate_documents(docs: list[Document]) -> list[Document]:
    """
    Remove near-duplicate chunks before embedding.
    Uses Jaccard word overlap — chunks with > 70% overlap are merged/dropped.
    Preserves the higher-priority chunk when duplicates are found.
    """
    kept: list[Document] = []
    for doc in docs:
        text = doc.page_content or ""
        is_dup = False
        for existing in kept:
            if _word_overlap(text, existing.page_content or "") > 0.70:
                # Keep the one with higher priority
                new_prio = doc.metadata.get("priority", 0)
                ex_prio = existing.metadata.get("priority", 0)
                if new_prio > ex_prio:
                    kept.remove(existing)
                    kept.append(doc)
                is_dup = True
                break
        if not is_dup:
            kept.append(doc)
    return kept


# ---------------------------------------------------------------------------
# Main ingestor node
# ---------------------------------------------------------------------------

def rag_ingestor_node(state: BrandForgeState) -> dict:
    job_id = state.get("job_id", "unknown")
    collection_name = f"brand_{job_id}"

    job_manager.emit(job_id, {
        "type": "rag_ingestor",
        "stage": "rag_ingestor",
        "status": "running",
        "message": "Chunking and indexing brand knowledge...",
    })

    raw_pages: dict[str, str] = state.get("raw_pages", {})

    if not raw_pages:
        print(f"[rag_ingestor] WARNING: No pages to ingest for job {job_id}")
        job_manager.emit(job_id, {
            "type": "rag_ingestor",
            "stage": "rag_ingestor",
            "status": "done",
            "message": "No pages found — skipping RAG indexing.",
        })
        return {"chroma_collection_id": collection_name}

    # --- Parse all pages into typed sections ---
    all_sections: list[dict[str, Any]] = []
    for page_url, page_text in raw_pages.items():
        if not page_text or len(page_text.strip()) < 30:
            continue
        sections = _parse_page_into_sections(page_text, page_url)
        all_sections.extend(sections)

    print(f"[rag_ingestor] Parsed {len(all_sections)} sections from {len(raw_pages)} pages")

    # --- Chunk each section with type-appropriate splitter ---
    documents: list[Document] = []
    section_counts: dict[str, int] = {}

    for section in all_sections:
        s_type = section["type"]
        s_text = section["text"]
        s_url = section["url"]
        priority = SECTION_PRIORITY.get(s_type, SECTION_PRIORITY["default"])

        # Skip source_header sections — no standalone value
        if s_type == "source_header":
            continue

        splitter = _get_splitter(s_type)

        try:
            chunks = splitter.split_text(s_text)
        except Exception:
            chunks = [s_text[:CHUNK_CONFIG["default"]["size"]]]

        for i, chunk in enumerate(chunks):
            chunk = _normalize_chunk(chunk)
            if not _is_quality_chunk(chunk, s_type):
                continue

            doc = Document(
                page_content=chunk,
                metadata={
                    "source": s_url,
                    "job_id": job_id,
                    "section_type": s_type,
                    "priority": priority,
                    "chunk_index": i,
                    "chunk_total": len(chunks),
                },
            )
            documents.append(doc)
            section_counts[s_type] = section_counts.get(s_type, 0) + 1

    if not documents:
        print(f"[rag_ingestor] WARNING: Zero quality chunks produced for job {job_id}")
        job_manager.emit(job_id, {
            "type": "rag_ingestor",
            "stage": "rag_ingestor",
            "status": "done",
            "message": "No quality chunks found — RAG context will be limited.",
        })
        return {"chroma_collection_id": collection_name}

    # --- Deduplicate before embedding (saves compute + improves retrieval) ---
    before_dedup = len(documents)
    documents = _deduplicate_documents(documents)
    after_dedup = len(documents)
    print(f"[rag_ingestor] Dedup: {before_dedup} -> {after_dedup} chunks")

    # --- Embed and store in ChromaDB ---
    embeddings = get_embeddings()
    client = get_chroma_client()

    # Delete existing collection for this job if it exists (clean rerun)
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    # Batch insert — Chroma handles batching internally but we cap to avoid OOM
    BATCH_SIZE = 100
    for batch_start in range(0, len(documents), BATCH_SIZE):
        batch = documents[batch_start: batch_start + BATCH_SIZE]
        try:
            Chroma.from_documents(
                documents=batch,
                embedding=embeddings,
                collection_name=collection_name,
                client=client,
            )
        except Exception as e:
            print(f"[rag_ingestor] Batch {batch_start} error: {e}")

    # --- Summary ---
    top_sections = sorted(section_counts.items(), key=lambda x: -x[1])[:5]
    top_str = ", ".join(f"{k}:{v}" for k, v in top_sections)
    message = (
        f"Indexed {after_dedup} chunks from {len(raw_pages)} pages "
        f"[{top_str}]"
    )
    print(f"[rag_ingestor] {message}")

    event = {
        "type": "rag_ingestor",
        "stage": "rag_ingestor",
        "status": "done",
        "message": message,
    }
    job_manager.emit(job_id, event)

    return {
        "chroma_collection_id": collection_name,
        "events": [event],
    }