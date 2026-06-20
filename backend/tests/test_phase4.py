import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # Must be before pipeline imports so API keys are visible

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pipeline.state import make_initial_state
from pipeline.graph import graph

async def test_phase4():
    url = "https://notion.so"
    job_id = "test-phase4-notion"
    
    print(f"=== Phase 4 Full Asset Generation Test ===")
    print(f"Target URL: {url}")
    print("Executing full graph...\n")
    
    state = make_initial_state(url, job_id)
    
    try:
        final_state = await graph.ainvoke(state)
        
        print("\n=== Pipeline Execution Complete ===")
        print("Events:")
        for event in final_state.get("events", []):
            print(f" - [{event['stage']}] {event['status']}")
            
        zip_path = final_state.get("zip_path")
        print(f"\n✅ Created ZIP archive: {zip_path}")
        
        # List generated files
        job_dir = Path("./outputs") / job_id
        if job_dir.exists():
            print(f"\nGenerated files in {job_dir}:")
            for file_path in job_dir.iterdir():
                if file_path.is_file():
                    size_kb = file_path.stat().st_size / 1024
                    print(f"  📄 {file_path.name} ({size_kb:.1f} KB)")
                    
    except Exception as e:
        print(f"\n[!] Pipeline failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_phase4())
