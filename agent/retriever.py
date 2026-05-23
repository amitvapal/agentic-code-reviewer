"""Query the codebase collection for chunks relevant to a question or diff hunk."""

from __future__ import annotations

from agent.config import Settings
from agent.embeddings import embed_texts, get_collection


def _format_results(res: dict) -> list[dict]:
    """Flatten a Chroma query result (single query) into a list of chunk dicts."""
    ids = res.get("ids", [[]])[0]
    documents = res.get("documents", [[]])[0]
    metadatas = res.get("metadatas", [[]])[0]
    distances = res.get("distances", [[]])[0]

    out: list[dict] = []
    for chunk_id, doc, meta, dist in zip(ids, documents, metadatas, distances):
        meta = meta or {}
        out.append(
            {
                "id": chunk_id,
                "path": meta.get("path"),
                "start_line": meta.get("start_line"),
                "end_line": meta.get("end_line"),
                "text": doc,
                # cosine distance -> similarity in [0, 1] for normalized vectors
                "score": 1.0 - dist,
            }
        )
    return out


def retrieve(
    query: str,
    top_k: int | None = None,
    settings: Settings | None = None,
) -> list[dict]:
    """Return the ``top_k`` chunks most similar to ``query``.

    Each result has ``path``, ``start_line``, ``end_line``, ``text`` and a
    similarity ``score``.
    """
    settings = settings or Settings()
    top_k = top_k or settings.top_k
    collection = get_collection(settings)

    query_embedding = embed_texts([query], settings)
    res = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    return _format_results(res)


def retrieve_for_hunk(
    hunk_text: str,
    file_path: str,
    top_k: int | None = None,
    settings: Settings | None = None,
) -> list[dict]:
    """Retrieve context for a diff hunk, biased toward ``file_path``.

    Roughly half the slots are reserved for chunks from the same file (local
    context), and the rest are filled with the strongest cross-file matches
    (callers, definitions elsewhere). Each result is tagged with ``same_file``.
    """
    settings = settings or Settings()
    top_k = top_k or settings.top_k
    collection = get_collection(settings)

    query_embedding = embed_texts([hunk_text], settings)
    # Over-fetch so we have enough of both same-file and cross-file candidates
    # to blend after the fact.
    over_fetch = max(top_k * 4, top_k + 5)
    res = collection.query(
        query_embeddings=query_embedding,
        n_results=over_fetch,
        include=["documents", "metadatas", "distances"],
    )
    results = _format_results(res)

    same_file = [r for r in results if r["path"] == file_path]
    other_file = [r for r in results if r["path"] != file_path]

    same_quota = max(1, top_k // 2)
    picked: list[dict] = []
    picked_ids: set[str] = set()

    def take(candidates: list[dict], limit: int) -> None:
        for r in candidates:
            if len(picked) >= top_k or limit <= 0:
                return
            if r["id"] in picked_ids:
                continue
            picked.append(r)
            picked_ids.add(r["id"])
            limit -= 1

    take(same_file, same_quota)
    take(other_file, top_k - len(picked))
    # Backfill from whatever's left if one side was short.
    take(results, top_k - len(picked))

    for r in picked:
        r["same_file"] = r["path"] == file_path
    return picked[:top_k]
