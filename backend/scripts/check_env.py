import os
from dotenv import load_dotenv
load_dotenv()

required = ["GROQ_API_KEY", "GEMINI_API_KEY", "CHROMA_PERSIST_DIR", "OUTPUT_DIR"]
missing = [k for k in required if not os.getenv(k)]
if missing:
    print(f"[ERR] Missing env vars: {missing}")
    exit(1)
else:
    print("[OK] All environment variables are set.")
