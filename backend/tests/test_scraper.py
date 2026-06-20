import asyncio
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pipeline.state import make_initial_state
from pipeline.nodes.scraper import scraper_node_async

async def test_scraper():
    url = "https://linear.app"
    print(f"Starting test for: {url}")
    state = make_initial_state(url, "test-job-001")
    
    result = await scraper_node_async(state)
    
    raw_pages = result.get("raw_pages", {})
    print(f"\n✅ Scraped {len(raw_pages)} pages.")
    
    if url in raw_pages:
        home_content = raw_pages[url]
        print(f"✅ Homepage content character count: {len(home_content)}")
        print(f"\n--- Snippet of homepage content ---\n{home_content[:500]}...\n-----------------------------------")
    else:
        print("❌ Homepage was not found in raw_pages results.")
        
    for page_url in raw_pages.keys():
        print(f"Scraped: {page_url} ({len(raw_pages[page_url])} chars)")

if __name__ == "__main__":
    asyncio.run(test_scraper())
