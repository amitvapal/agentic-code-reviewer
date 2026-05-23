"""Index a tiny fixture repo and check retrieval surfaces the right chunk."""

from pathlib import Path

from agent.config import Settings
from agent.indexer import index_repo
from agent.retriever import retrieve, retrieve_for_hunk

FIXTURE_REPO = Path(__file__).parent / "fixtures" / "sample_repo"


def _settings(tmp_path) -> Settings:
    return Settings(_env_file=None, chroma_dir=str(tmp_path / "chroma"))


def test_retrieve_finds_defining_chunk(tmp_path):
    settings = _settings(tmp_path)
    summary = index_repo(str(FIXTURE_REPO), settings=settings)
    assert summary["files"] >= 2
    assert summary["chunks"] >= 2

    results = retrieve("how is the nth fibonacci number calculated", top_k=3, settings=settings)

    assert results
    top = results[0]
    assert top["path"] == "math_utils.py"
    assert "fibonacci" in top["text"]
    assert top["start_line"] is not None and top["end_line"] is not None


def test_retrieve_for_hunk_biases_same_file_but_keeps_cross_file(tmp_path):
    settings = _settings(tmp_path)
    index_repo(str(FIXTURE_REPO), settings=settings)

    hunk = "    a, b = b, a + b\n    return a\n"
    results = retrieve_for_hunk(hunk, file_path="math_utils.py", top_k=2, settings=settings)

    assert results
    paths = {r["path"] for r in results}
    # Same-file context is present...
    assert "math_utils.py" in paths
    # ...and cross-file context is still pulled in.
    assert any(not r["same_file"] for r in results)
