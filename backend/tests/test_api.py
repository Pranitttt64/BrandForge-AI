import httpx
import asyncio
import json
import zipfile
import os

async def main():
    url = "http://127.0.0.1:8000"
    target_url = "https://linear.app"
    
    print(f"=== POST /api/forge url={target_url} ===")
    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(f"{url}/api/forge", json={"url": target_url})
        res.raise_for_status()
        data = res.json()
        job_id = data["job_id"]
        print(f"Got job_id: {job_id}")
        
        print("\n=== Connecting to /stream... ===")
        # Stream the SSE
        async with client.stream("GET", f"{url}/api/forge/{job_id}/stream", timeout=600.0) as stream:
            async for line in stream.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    print(f"EVENT: {event['stage']} -> {event['status']}")
                    if event.get("stage") == "complete":
                        print("✅ Job complete!")
                        download_url = event["download_url"]
                        break
                    elif event.get("stage") == "error":
                        print(f"❌ Job failed! Error: {event.get('error')}")
                        return
                        
        print(f"\n=== GET {download_url} ===")
        res = await client.get(f"{url}{download_url}")
        res.raise_for_status()
        
        zip_path = f"downloaded_{job_id}.zip"
        with open(zip_path, "wb") as f:
            f.write(res.content)
            
        print(f"Saved {zip_path}")
        
        # Verify contents
        print("\n=== ZIP Contents ===")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for item in zip_ref.namelist():
                print(f" - {item}")
        
if __name__ == "__main__":
    asyncio.run(main())
