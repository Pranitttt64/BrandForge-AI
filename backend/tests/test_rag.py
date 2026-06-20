"""
Phase 2 Integration Test — RAG Pipeline
Runs: scraper -> extractor -> ingestor -> retriever queries
Target: https://stripe.com
"""

import asyncio
import json
import os
import sys

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

from pipeline.state import make_initial_state
from pipeline.nodes.scraper import scraper_node_async
from pipeline.nodes.brand_extractor import brand_extractor_node
from pipeline.nodes.rag_ingestor import rag_ingestor_node
from rag.retriever import query_brand_knowledge


async def test_rag_pipeline():
    url = "https://stripe.com"
    job_id = "test-rag-001"
    print(f"=== Phase 2 RAG Pipeline Test ===")
    print(f"Target URL: {url}")
    print(f"Job ID: {job_id}")
    print()

    # Step 1: Scrape
    print("[1/4] Scraping website...")
    state = make_initial_state(url, job_id)
    scraper_result = await scraper_node_async(state)
    state.update(scraper_result)

    page_count = len(state.get("raw_pages", {}))
    print(f"  -> Scraped {page_count} pages")
    for page_url in state["raw_pages"]:
        print(f"     - {page_url} ({len(state['raw_pages'][page_url])} chars)")
    print()

    # Step 2: Extract brand profile
    print("[2/4] Extracting brand profile (LLM call)...")
    try:
        extractor_result = brand_extractor_node(state)
        state.update(extractor_result)
    except Exception as e:
        print(f"  [!] LLM Extraction failed (missing API keys?): {e}")
        print("  [!] Using mock brand profile to continue RAG test...")
        state.update({
            "brand_profile": {
                "brand_name": "Stripe",
                "tagline": "Financial infrastructure for the internet",
                "brand_tone": "professional",
                "target_audience": "Developers and businesses",
                "usps": ["Global payments", "Fraud prevention", "Developer friendly"],
                "product_categories": ["Payments", "Billing"],
                "brand_category": "SaaS"
            },
            "brand_name": "Stripe",
            "brand_tone": "professional",
            "brand_category": "SaaS",
            "target_audience": "Developers and businesses",
            "usps": ["Global payments", "Fraud prevention", "Developer friendly"]
        })

    print(f"  -> Brand Name: {state.get('brand_name')}")
    print(f"  -> Brand Tone: {state.get('brand_tone')}")
    print(f"  -> Category: {state.get('brand_category')}")
    print(f"  -> USPs: {state.get('usps')}")
    print(f"  -> Target Audience: {state.get('target_audience')}")
    print(f"  -> Colors: {state.get('brand_colors')}")
    print()

    # Step 3: Ingest into ChromaDB
    print("[3/4] Ingesting into ChromaDB...")
    ingestor_result = rag_ingestor_node(state)
    state.update(ingestor_result)

    collection_id = state.get("chroma_collection_id")
    print(f"  -> Collection: {collection_id}")
    print()

    # Step 4: Run test queries
    print("[4/4] Running RAG queries...")
    print("=" * 60)

    queries = [
        "What problems does this company solve?",
        "What is the brand tone and communication style?",
        "Who is the target audience?",
    ]

    for i, query in enumerate(queries, 1):
        print(f"\nQuery {i}: \"{query}\"")
        print("-" * 40)
        context = query_brand_knowledge(collection_id, query, k=3)
        if context:
            # Print first 500 chars of context to keep output manageable
            preview = context[:500]
            if len(context) > 500:
                preview += "..."
            print(context)
        else:
            print("  [!] No results returned")
        print("-" * 40)

    print()
    print("=== Phase 2 Test Complete ===")
    print(f"Full brand profile:")
    print(json.dumps(state.get("brand_profile", {}), indent=2))


if __name__ == "__main__":
    asyncio.run(test_rag_pipeline())
