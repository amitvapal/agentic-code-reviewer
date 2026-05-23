"""Shared embedding model + ChromaDB collection access.

Both the indexer and the retriever go through here so they always use the same
model and the same persistent collection.
"""

from __future__ import annotations

from functools import lru_cache

import chromadb
from sentence_transformers import SentenceTransformer

from agent.config import Settings

COLLECTION_NAME = "codebase"


@lru_cache(maxsize=2)
def get_embedder(model_name: str) -> SentenceTransformer:
    """Load (and cache) the sentence-transformers model by name."""
    return SentenceTransformer(model_name)


@lru_cache(maxsize=None)
def _get_client(chroma_dir: str) -> chromadb.ClientAPI:
    """Cache one persistent client per on-disk path."""
    return chromadb.PersistentClient(path=chroma_dir)


def get_collection(settings: Settings):
    """Return the persistent codebase collection, creating it (HNSW/cosine) if needed."""
    client = _get_client(settings.chroma_dir)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def embed_texts(texts: list[str], settings: Settings) -> list[list[float]]:
    """Embed a batch of texts with the configured model (L2-normalized)."""
    embedder = get_embedder(settings.embed_model)
    vectors = embedder.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vectors.tolist()
