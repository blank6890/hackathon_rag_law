"""
ChromaDB-backed statute retrieval for ComplianceMind.

Auto-loads data/corpus.json into a persistent ChromaDB collection on first
use. Subsequent calls use semantic (embedding-based) search to find the
most relevant statute sections for a given business description.

This replaces the keyword-matching retrieval_stub.py with real RAG.
"""

import json
import os
import threading

import chromadb

# Persistent client — data survives across restarts. The DB lives next
# to this file so it's easy to find and clean up.
_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")
_CORPUS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "corpus.json"
)

# Lazy globals — created on first use, not at import time. This avoids
# holding a stale connection if the DB folder is deleted between runs
# (e.g. during testing), and defers the chromadb import cost.
_client = None
_collection = None

# Guard so we only check/load the corpus once per process, even under
# Streamlit's script-rerun model.
_load_lock = threading.Lock()
_loaded = False


def _get_collection():
    """Return the ChromaDB collection, creating the client on first use.

    Lazy initialization avoids holding a stale SQLite connection if the
    chroma_db folder is deleted between runs (common in test environments).
    """
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=_DB_PATH)
        _collection = _client.get_or_create_collection(name="statutes")
    return _collection


def _ensure_loaded():
    """Load the corpus into ChromaDB if the collection is empty.

    Called automatically on every retrieve_sections() call, but the
    _loaded flag + lock means the actual check happens at most once
    per process. Safe to call concurrently.
    """
    global _loaded
    if _loaded:
        return
    with _load_lock:
        if _loaded:
            return
        # Check if collection already has data (e.g. from a previous run)
        collection = _get_collection()
        existing = collection.count()
        if existing == 0:
            load_corpus(_CORPUS_PATH)
        _loaded = True


def load_corpus(path: str = _CORPUS_PATH):
    """Load corpus.json into the ChromaDB collection. Run once (or whenever
    corpus.json changes — ChromaDB will upsert by id, so re-running is safe)."""
    with open(path) as f:
        corpus = json.load(f)

    collection = _get_collection()
    # NOTE: use upsert(), not add() — add() raises on duplicate ids, which
    # would break re-running this whenever corpus.json changes.
    collection.upsert(
        ids=[item["id"] for item in corpus],
        documents=[item["text"] for item in corpus],
        metadatas=[
            {"act": item["act"], "section": item["section"], "title": item["title"]}
            for item in corpus
        ],
    )
    print(f"Loaded {len(corpus)} sections into ChromaDB at {_DB_PATH}")


# Backward-compat: expose `collection` as a property-like attribute for
# any code that still references retrieval.collection directly.
class _CollectionProxy:
    """Proxy that delegates to _get_collection() so legacy code like
    `retrieval.collection.upsert(...)` still works after a DB reset."""
    def __getattr__(self, name):
        return getattr(_get_collection(), name)


collection = _CollectionProxy()


def retrieve_sections(query: str, n_results: int = 3) -> list[dict]:
    """Return the n_results most relevant statute sections for *query*.

    Uses ChromaDB's default embedding model (all-MiniLM-L6-v2) for semantic
    search — so it finds relevant sections even when the query doesn't
    contain exact keywords from the section text.

    Interface is identical to retrieval_stub.retrieve_sections — the two
    modules are drop-in replacements for each other.
    """
    _ensure_loaded()

    results = _get_collection().query(query_texts=[query], n_results=n_results)

    sections = []
    for i in range(len(results["ids"][0])):
        sections.append({
            "act": results["metadatas"][0][i]["act"],
            "section": results["metadatas"][0][i]["section"],
            "title": results["metadatas"][0][i]["title"],
            "text": results["documents"][0][i],
        })
    return sections


if __name__ == "__main__":
    load_corpus()

    test_queries = [
        "I'm building an online store that collects customer phone numbers and emails",
        "fintech app that processes payments and stores personal data",
        "I run a small offline shop, no website",
    ]
    for q in test_queries:
        print(f"\nQuery: {q}")
        for r in retrieve_sections(q):
            print(f"  -> {r['act']} {r['section']}: {r['title']}")
