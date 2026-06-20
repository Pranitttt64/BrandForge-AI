"""
RAG Retriever — BrandForge AI
Multi-strategy retrieval with section-type boosting and agent-specific
query sets so every downstream agent gets the most relevant brand context.
"""

from __future__ import annotations

import re
from typing import Literal

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from rag.chroma_client import get_chroma_client
from rag.embedder import get_embeddings


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

AgentName = Literal[
    "brand_extractor",
    "copywriter",
    "email_agent",
    "ad_agent",
    "layout_agent",
    "general",
]


# ---------------------------------------------------------------------------
# Agent-specific query banks
# Each agent retrieves context most relevant to its specific task.
# ---------------------------------------------------------------------------

AGENT_QUERIES: dict[AgentName, list[str]] = {
    "brand_extractor": [
        "company name brand identity mission vision",
        "what does the company do products services overview",
        "target audience customer who is this for",
        "unique selling proposition differentiator competitive advantage",
        "brand values culture story founding",
        "brand tone voice personality style",
        "product features capabilities platform",
        "pricing plans tiers cost",
        "testimonials reviews social proof customers",
        "statistics metrics numbers results impact",
    ],
    "copywriter": [
        "key benefits value proposition what customers get",
        "product features capabilities platform services",
        "unique differentiators why choose us competitive advantage",
        "target audience pain points problems solved",
        "results outcomes customer success proof",
        "brand voice examples tagline slogan messaging",
        "call to action get started try sign up",
        "pricing plans offers what is included",
        "testimonials customer quotes social proof",
        "headline hook attention grabbing statement",
    ],
    "email_agent": [
        "welcome onboarding getting started new user",
        "product features benefits what you can do",
        "promotional offer deal limited time pricing",
        "customer success story results testimonial",
        "re-engagement win back return come back",
        "brand story mission why we exist",
        "call to action next step try explore",
        "target audience pain points motivation",
        "trust signals guarantee security reliability",
        "product updates new features announcement",
    ],
    "ad_agent": [
        "key differentiator unique advantage over competitors",
        "short punchy value proposition benefit statement",
        "target audience pain point problem challenge",
        "call to action get started try free sign up",
        "social proof numbers results statistics",
        "product name feature capability platform",
        "pricing free trial offer promotional hook",
        "brand personality tone bold statement",
        "urgency scarcity limited time offer",
        "transformation before after outcome result",
    ],
    "layout_agent": [
        "brand visual identity colors design aesthetic",
        "product category type of business industry",
        "brand tone professional minimal bold playful luxury",
        "hero headline primary message above the fold",
        "content sections features about pricing team",
    ],
    "general": [
        "brand overview company description",
        "products services features offerings",
        "target audience customers who uses this",
        "value proposition benefits outcomes",
        "brand identity tone voice personality",
    ],
}

# Section types that are highest value for retrieval
HIGH_PRIORITY_SECTIONS = {
    "brand_section", "features", "h1", "json_ld",
    "testimonial", "pricing", "og_meta", "meta_description",
    "stats", "h2",
}

MEDIUM_PRIORITY_SECTIONS = {
    "body", "h3", "jina_text", "dynamic_text", "cta",
}


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def _word_overlap(a: str, b: str) -> float:
    """Jaccard word overlap between two strings."""
    wa = set(re.sub(r"[^\w\s]", "", a.lower()).split())
    wb = set(re.sub(r"[^\w\s]", "", b.lower()).split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / max(len(wa), len(wb))


def _dedupe(
    candidates: list[Document],
    threshold: float = 0.60,
) -> list[Document]:
    """
    Remove near-duplicate documents from a result list.
    Lower threshold than ingestor (0.60 vs 0.70) — retriever should be stricter
    to avoid the LLM getting repetitive context.
    """
    kept: list[Document] = []
    for doc in candidates:
        text = doc.page_content or ""
        if not text.strip():
            continue
        is_dup = any(
            _word_overlap(text, existing.page_content or "") > threshold
            for existing in kept
        )
        if not is_dup:
            kept.append(doc)
    return kept


# ---------------------------------------------------------------------------
# Scoring & ranking
# ---------------------------------------------------------------------------

def _score_document(doc: Document) -> float:
    """
    Compute a retrieval score for ranking.
    Combines metadata priority with content richness signals.
    """
    meta = doc.metadata or {}
    text = doc.page_content or ""

    # Base: stored priority from ingestor
    base = float(meta.get("priority", 3))

    # Section type boost
    section = meta.get("section_type", "default")
    if section in HIGH_PRIORITY_SECTIONS:
        base += 3.0
    elif section in MEDIUM_PRIORITY_SECTIONS:
        base += 1.0

    # Content richness: longer chunks with real sentences score higher
    length_score = min(len(text) / 500, 2.0)
    base += length_score

    # Presence of brand-signal words
    signal_words = (
        "we ", "our ", "you ", "your ", "the ", " is ", " are ",
        "feature", "benefit", "customer", "solution", "platform",
        "result", "trusted", "million", "thousand", "%", "$",
    )
    signal_score = sum(0.15 for w in signal_words if w in text.lower())
    base += min(signal_score, 1.5)

    return round(base, 3)


def _rank_documents(docs: list[Document]) -> list[Document]:
    """Sort by computed score descending."""
    return sorted(docs, key=_score_document, reverse=True)


# ---------------------------------------------------------------------------
# Core retrieval
# ---------------------------------------------------------------------------

def _get_vectorstore(collection_id: str) -> Chroma:
    return Chroma(
        collection_name=collection_id,
        embedding_function=get_embeddings(),
        client=get_chroma_client(),
    )


def _run_queries(
    vectorstore: Chroma,
    queries: list[str],
    k_per_query: int = 5,
) -> list[Document]:
    """
    Run multiple queries and collect all unique results.
    Each query targets a different aspect of brand knowledge.
    """
    all_docs: list[Document] = []
    seen_texts: set[str] = set()

    for query in queries:
        try:
            results = vectorstore.similarity_search(query=query, k=k_per_query)
        except Exception as e:
            print(f"[retriever] Query error '{query[:40]}': {e}")
            continue

        for doc in results:
            text = (doc.page_content or "").strip()
            if not text or text in seen_texts:
                continue
            seen_texts.add(text)
            all_docs.append(doc)

    return all_docs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def query_brand_knowledge(
    collection_id: str,
    question: str,
    k: int = 7,
    agent: AgentName = "general",
    max_chunks: int = 15,
) -> str:
    """
    Primary retrieval function called by all pipeline agents.

    Args:
        collection_id: ChromaDB collection name for this job.
        question:      The agent's specific question about the brand.
        k:             Base number of results per query (default 7).
        agent:         Which agent is calling — selects the right query bank.
        max_chunks:    Maximum chunks to include in returned context.

    Returns:
        Rich, labeled, deduplicated context string ready for LLM injection.
    """
    try:
        vectorstore = _get_vectorstore(collection_id)
    except Exception as e:
        print(f"[retriever] Could not load vectorstore '{collection_id}': {e}")
        return "No brand knowledge available."

    # Build query list: agent-specific bank + the caller's direct question
    agent_queries = AGENT_QUERIES.get(agent, AGENT_QUERIES["general"])
    all_queries = [question] + agent_queries

    # Retrieve from all queries
    raw_docs = _run_queries(vectorstore, all_queries, k_per_query=5)

    if not raw_docs:
        print(f"[retriever] No results for collection '{collection_id}'")
        return "No brand knowledge retrieved. Use general brand reasoning."

    # Rank by content quality + section priority
    ranked = _rank_documents(raw_docs)

    # Deduplicate
    deduped = _dedupe(ranked, threshold=0.60)

    # Cap at max_chunks
    final = deduped[:max_chunks]

    # Assemble context string with labels for LLM clarity
    parts: list[str] = []
    for doc in final:
        meta = doc.metadata or {}
        source = meta.get("source", "unknown")
        section = meta.get("section_type", "content")
        text = " ".join((doc.page_content or "").split())

        # Label each chunk so the LLM understands what type of content it is
        label = _section_label(section)
        parts.append(f"[{label} | {_short_url(source)}]\n{text}")

    context = "\n\n---\n\n".join(parts)
    print(
        f"[retriever] agent={agent} | "
        f"raw={len(raw_docs)} | ranked | deduped={len(deduped)} | "
        f"returning={len(final)} chunks | "
        f"{sum(len(p) for p in parts):,} chars"
    )
    return context


def query_brand_knowledge_typed(
    collection_id: str,
    section_types: list[str],
    max_chunks: int = 10,
) -> str:
    """
    Retrieve chunks of specific section types directly.
    Useful when an agent wants ONLY features, or ONLY testimonials, etc.
    Falls back to similarity search if direct filter returns nothing.
    """
    try:
        client = get_chroma_client()
        collection = client.get_collection(collection_id)
        results = collection.get(
            where={"section_type": {"$in": section_types}},
            limit=max_chunks * 2,
        )
    except Exception as e:
        print(f"[retriever] Typed query error: {e}")
        return ""

    docs_and_meta = list(zip(
        results.get("documents") or [],
        results.get("metadatas") or [],
    ))

    if not docs_and_meta:
        return ""

    # Score and sort
    scored = sorted(
        docs_and_meta,
        key=lambda dm: float((dm[1] or {}).get("priority", 3)),
        reverse=True,
    )

    parts: list[str] = []
    seen: set[str] = set()
    for text, meta in scored[:max_chunks]:
        text = (text or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        section = (meta or {}).get("section_type", "content")
        source = (meta or {}).get("source", "")
        label = _section_label(section)
        parts.append(f"[{label} | {_short_url(source)}]\n{text}")

    return "\n\n---\n\n".join(parts)


def query_brand_knowledge_with_scores(
    collection_id: str,
    question: str,
    k: int = 5,
) -> list[dict]:
    """Debug/analysis: returns chunks with relevance scores."""
    try:
        vectorstore = _get_vectorstore(collection_id)
        results = vectorstore.similarity_search_with_relevance_scores(
            query=question, k=k
        )
        return [
            {
                "text": doc.page_content,
                "metadata": doc.metadata,
                "score": round(score, 4),
                "computed_score": _score_document(doc),
            }
            for doc, score in results
        ]
    except Exception as e:
        print(f"[retriever] Score query error: {e}")
        return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _section_label(section_type: str) -> str:
    labels = {
        "brand_section":    "Brand Content",
        "features":         "Features & Benefits",
        "h1":               "Primary Headline",
        "h2":               "Section Heading",
        "h3":               "Sub-Heading",
        "json_ld":          "Structured Brand Data",
        "og_meta":          "Brand Meta",
        "meta_description": "Brand Description",
        "meta_keywords":    "Brand Keywords",
        "body":             "Body Copy",
        "testimonial":      "Customer Testimonial",
        "stats":            "Key Metrics",
        "pricing":          "Pricing & Plans",
        "cta":              "Call to Action",
        "footer":           "Footer Content",
        "jina_text":        "Page Content",
        "dynamic_text":     "Dynamic Content",
        "title":            "Page Title",
    }
    return labels.get(section_type, "Content")


def _short_url(url: str) -> str:
    """Shorten a URL to just the path for display in context labels."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.rstrip("/") or "/"
        return parsed.netloc + (path if path != "/" else "")
    except Exception:
        return url[:60]