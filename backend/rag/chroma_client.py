"""
ChromaDB client singleton for BrandForge AI.
Uses PersistentClient so vector data survives restarts.
Thread-safe via module-level lock.
"""

import os
import threading
import chromadb
from chromadb.config import Settings

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_store")

_client: chromadb.ClientAPI | None = None
_lock = threading.Lock()


def get_chroma_client() -> chromadb.ClientAPI:
    """
    Returns a singleton ChromaDB PersistentClient.
    Thread-safe. Data persists at CHROMA_PERSIST_DIR.
    """
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                _client = chromadb.PersistentClient(
                    path=CHROMA_PERSIST_DIR,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                    ),
                )
                print(f"[chroma] Client initialised at {CHROMA_PERSIST_DIR}")
    return _client


def get_or_create_collection(
    collection_name: str,
    metadata: dict | None = None,
) -> chromadb.Collection:
    """
    Get or create a named collection with optional metadata.
    Safe to call multiple times — returns existing collection if present.
    """
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=collection_name,
        metadata=metadata or {"hnsw:space": "cosine"},
    )


def delete_collection(collection_name: str) -> None:
    """
    Delete a collection by name. Used for cleanup after job completion
    or test teardown. Silently ignores missing collections.
    """
    client = get_chroma_client()
    try:
        client.delete_collection(collection_name)
        print(f"[chroma] Deleted collection: {collection_name}")
    except Exception as e:
        print(f"[chroma] Delete skipped ({collection_name}): {e}")


def collection_exists(collection_name: str) -> bool:
    """Returns True if the named collection already exists."""
    client = get_chroma_client()
    try:
        existing = [c.name for c in client.list_collections()]
        return collection_name in existing
    except Exception:
        return False


def reset_store() -> None:
    """
    Full reset of the ChromaDB store. Only call this in tests or
    on deliberate admin action. Destroys all collections and vectors.
    """
    client = get_chroma_client()
    client.reset()
    print("[chroma] Store reset complete.")