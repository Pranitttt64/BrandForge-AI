import asyncio
from dotenv import load_dotenv; load_dotenv()
from pipeline.graph import graph
from pipeline.state import make_initial_state
import uuid
import sys
if sys.platform == 'win32': sys.stdout.reconfigure(encoding='utf-8', errors='replace')

async def test(url):
    print(f'\n=== Testing: {url} ===')
    state = make_initial_state(url, str(uuid.uuid4())[:8])
    result = await graph.ainvoke(state)
    print(f'Colors: {result.get("brand_colors")}')
    print(f'Assets: flyer={result.get("flyer_pdf_path")} social={result.get("social_card_path")}')

async def main():
    await test('https://notion.so')
    print("Waiting 10s to avoid rate limit...")
    await asyncio.sleep(10)
    await test('https://stripe.com')
    print("Waiting 10s to avoid rate limit...")
    await asyncio.sleep(10)
    await test('https://linear.app')

if __name__ == "__main__":
    asyncio.run(main())
