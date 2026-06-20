"""
Embedding singleton for BrandForge AI.
Uses sentence-transformers/all-MiniLM-L6-v2 via LangChain HuggingFace.

First call downloads ~80MB model to ~/.cache/huggingface/
Subsequent calls in the same process use the cached instance (< 1ms).
Subsequent process starts use the disk cache (2-5s load time).

Thread-safe via module-level lock.
"""

import os
import threading

# Prevent TensorFlow imports from transformers
os.environ["USE_TF"] = "0"
os.environ["TRANSFORMERS_NO_TF"] = "1"

from langchain_huggingface import HuggingFaceEmbeddings

_embeddings: HuggingFaceEmbeddings | None = None
_lock = threading.Lock()

MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)

# Set HuggingFace cache dir from env if provided
_hf_cache = os.getenv("HF_HOME") or os.getenv("TRANSFORMERS_CACHE")
if _hf_cache:
    os.environ.setdefault("HF_HOME", _hf_cache)


def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Returns a singleton HuggingFaceEmbeddings instance.

    Model: sentence-transformers/all-MiniLM-L6-v2
      - 384-dimensional embeddings
      - ~14ms per chunk on CPU
      - No API cost — runs fully locally
      - Normalized embeddings for cosine similarity

    Thread-safe. Safe to call from multiple async nodes simultaneously.
    """
    global _embeddings
    if _embeddings is None:
        with _lock:
            if _embeddings is None:
                print(f"[embedder] Loading model: {MODEL_NAME}")
                _embeddings = HuggingFaceEmbeddings(
                    model_name=MODEL_NAME,
                    model_kwargs={
                        "device": os.getenv("EMBEDDING_DEVICE", "cpu"),
                    },
                    encode_kwargs={
                        "normalize_embeddings": True,
                        "batch_size": int(os.getenv("EMBEDDING_BATCH_SIZE", "32")),
                    },
                )
                print(f"[embedder] Model loaded: {MODEL_NAME}")
    return _embeddings


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of text strings.
    Returns a list of float vectors, one per input text.
    Convenience wrapper around get_embeddings().embed_documents().
    """
    if not texts:
        return []
    embeddings = get_embeddings()
    return embeddings.embed_documents(texts)


def embed_query(query: str) -> list[float]:
    """
    Embed a single query string for similarity search.
    Uses embed_query (may use a different prompt prefix than embed_documents
    for asymmetric models — correct for MiniLM which is symmetric).
    """
    embeddings = get_embeddings()
    return embeddings.embed_query(query)


def warmup() -> None:
    """
    Pre-load the embedding model at server startup.
    Call this in FastAPI startup event to avoid cold-start delay
    on the first real request.

    Usage in main.py:
        @app.on_event("startup")
        async def startup():
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, warmup)
    """
    print("[embedder] Warming up embedding model...")
    get_embeddings()
    # Run a dummy embed to ensure model is fully loaded into memory
    embed_query("warmup")
    print("[embedder] Embedding model ready.")