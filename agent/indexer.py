"""Walk a repository, chunk its source files, and index them into ChromaDB.

CLI:  python -m agent.indexer <repo_path>
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

from agent.config import Settings
from agent.embeddings import embed_texts, get_collection

# Source extensions worth indexing. Binaries fall outside this set and are
# skipped by construction; anything that still fails to decode as UTF-8 is
# skipped at read time.
SOURCE_EXTENSIONS = {
    ".py", ".pyi",
    ".js", ".jsx", ".mjs", ".cjs",
    ".ts", ".tsx",
    ".java", ".kt", ".scala",
    ".go", ".rs", ".rb", ".php",
    ".c", ".h", ".cc", ".cpp", ".hpp", ".cxx",
    ".cs", ".swift", ".m", ".mm",
    ".sh", ".bash", ".sql", ".lua", ".pl", ".r",
}

# Directories we never descend into, regardless of .gitignore.
ALWAYS_SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "env",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "dist", "build", ".next", ".nuxt", ".tox", "target", "vendor",
    ".idea", ".vscode", ".gradle", "coverage", ".cache",
}

CHUNK_SIZE = 60
CHUNK_OVERLAP = 10
_UPSERT_BATCH = 1000


def _load_gitignore(repo: Path):
    """Return a compiled pathspec for the repo-root .gitignore, or None."""
    gitignore = repo / ".gitignore"
    if not gitignore.exists():
        return None
    try:
        import pathspec
    except ImportError:
        return None
    lines = gitignore.read_text(encoding="utf-8", errors="ignore").splitlines()
    return pathspec.PathSpec.from_lines("gitwildmatch", lines)


def iter_source_files(repo_path: str):
    """Yield ``(abs_path, rel_path)`` for each indexable source file under ``repo_path``."""
    repo = Path(repo_path).resolve()
    spec = _load_gitignore(repo)

    for root, dirs, files in os.walk(repo):
        rel_root = Path(root).relative_to(repo)

        # Prune skipped + gitignored directories in place so os.walk won't enter them.
        pruned = []
        for d in dirs:
            if d in ALWAYS_SKIP_DIRS:
                continue
            if spec is not None:
                rel_dir = (rel_root / d).as_posix()
                if spec.match_file(rel_dir) or spec.match_file(rel_dir + "/"):
                    continue
            pruned.append(d)
        dirs[:] = pruned

        for fname in files:
            if Path(fname).suffix.lower() not in SOURCE_EXTENSIONS:
                continue
            rel_path = (rel_root / fname).as_posix()
            if spec is not None and spec.match_file(rel_path):
                continue
            yield Path(root) / fname, rel_path


def chunk_lines(
    lines: list[str],
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[tuple[int, int, str]]:
    """Split ``lines`` into overlapping windows.

    Returns ``(start_line, end_line, text)`` tuples with 1-indexed, inclusive
    line numbers.
    """
    step = max(1, chunk_size - overlap)
    chunks: list[tuple[int, int, str]] = []
    n = len(lines)
    i = 0
    while i < n:
        window = lines[i : i + chunk_size]
        start = i + 1
        end = i + len(window)
        chunks.append((start, end, "".join(window)))
        if i + chunk_size >= n:
            break
        i += step
    return chunks


def _upsert_in_batches(collection, ids, embeddings, documents, metadatas) -> None:
    for i in range(0, len(ids), _UPSERT_BATCH):
        j = i + _UPSERT_BATCH
        collection.upsert(
            ids=ids[i:j],
            embeddings=embeddings[i:j],
            documents=documents[i:j],
            metadatas=metadatas[i:j],
        )


def index_repo(repo_path: str, settings: Settings | None = None) -> dict:
    """Index every source file under ``repo_path`` into the codebase collection.

    Re-indexing is idempotent: chunk ids are ``<rel_path>:<start>-<end>`` and
    written with ``upsert``, so unchanged chunks overwrite themselves.
    """
    settings = settings or Settings()
    start_time = time.perf_counter()
    collection = get_collection(settings)

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []
    files_indexed = 0

    for abs_path, rel_path in iter_source_files(repo_path):
        try:
            text = abs_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary or unreadable — skip

        lines = text.splitlines(keepends=True)
        file_chunks = [c for c in chunk_lines(lines) if c[2].strip()]
        if not file_chunks:
            continue

        files_indexed += 1
        for start, end, chunk_text in file_chunks:
            ids.append(f"{rel_path}:{start}-{end}")
            documents.append(chunk_text)
            metadatas.append(
                {"path": rel_path, "start_line": start, "end_line": end}
            )

    chunks_created = len(ids)
    if ids:
        embeddings = embed_texts(documents, settings)
        _upsert_in_batches(collection, ids, embeddings, documents, metadatas)

    elapsed = time.perf_counter() - start_time
    print(f"Files indexed:  {files_indexed}")
    print(f"Chunks created: {chunks_created}")
    print(f"Time taken:     {elapsed:.2f}s")

    return {"files": files_indexed, "chunks": chunks_created, "seconds": elapsed}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Index a local repository checkout into the codebase vector store."
    )
    parser.add_argument("repo_path", help="Path to the repository to index")
    args = parser.parse_args(argv)
    index_repo(args.repo_path)


if __name__ == "__main__":
    main()
