import asyncio
import json
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pipeline.state import make_initial_state
from pipeline.nodes.scraper import scraper_node_async
from pipeline.nodes.brand_extractor import brand_extractor_node

async def test_extractor():
    url = "https://notion.so"
    print(f"Starting test for: {url}")
    state = make_initial_state(url, "test-job-002")
    
    # Run Scraper
    print("Scraping...")
    scraper_result = await scraper_node_async(state)
    state.update(scraper_result)
    
    # Run Extractor
    print(f"Extracting brand profile (using LLM for text, deterministic for colors)...")
    extractor_result = brand_extractor_node(state)
    
    brand_profile = extractor_result.get("brand_profile")
    brand_colors = extractor_result.get("brand_colors")
    
    print("\n✅ Extractor Finished. Result:")
    print(json.dumps(brand_profile, indent=2))
    print("\n✅ Extracted Colors (dataclass):")
    print(brand_colors)

if __name__ == "__main__":
    asyncio.run(test_extractor())
