import asyncio
import json
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pipeline.state import make_initial_state
from pipeline.graph import graph
from dotenv import load_dotenv

load_dotenv()

async def test_full_pipeline():
    url = "https://linear.app"
    job_id = "test-graph-001"
    
    print(f"=== Phase 3 LangGraph Pipeline Test ===")
    print(f"Target URL: {url}")
    print("Executing full graph...")
    
    state = make_initial_state(url, job_id)
    
    try:
        # For testing, we mock LLM extraction if keys fail
        # but LangGraph manages execution.
        final_state = await graph.ainvoke(state)
        
        print("\n=== Pipeline Execution Complete ===")
        print("\nEvents Log (Execution Order):")
        for event in final_state.get("events", []):
            print(f" - [{event['stage']}] {event['status']}")
            
        print("\n=== Copywriter Output ===")
        print(json.dumps(final_state.get("copy_output", {}), indent=2))
        
        print("\n=== Layout Agent Output ===")
        print(json.dumps(final_state.get("layout_output", {}), indent=2))
        
        print("\n=== Email Agent Output ===")
        print(json.dumps(final_state.get("email_output", {}), indent=2))
        
        print("\n=== Ad Agent Output ===")
        print(json.dumps(final_state.get("ad_output", {}), indent=2))
        
        print("\n=== Critic Feedback ===")
        print(json.dumps(final_state.get("critic_feedback", {}), indent=2))
        print(f"Approved? {final_state.get('critic_approved')}")
        
    except Exception as e:
        print(f"\n[!] Pipeline failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
