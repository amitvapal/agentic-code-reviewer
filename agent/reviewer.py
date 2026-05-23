"""Drive the three review chains over a unified diff and aggregate findings."""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from unidiff import PatchSet

from agent.chains import (
    bug_detection_chain,
    build_llm,
    refactor_chain,
    style_chain,
)
from agent.config import Settings
from agent.retriever import retrieve_for_hunk
from agent.schemas import ChainResult, Finding, Review

_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2}

# (name, chain) pairs run for every hunk.
_CHAINS = (
    ("bug", bug_detection_chain),
    ("style", style_chain),
    ("refactor", refactor_chain),
)


def _review_hunk(hunk_text: str, context: list[dict], llm) -> list[ChainResult]:
    """Run all three chains for one hunk concurrently."""
    results: list[ChainResult] = []
    with ThreadPoolExecutor(max_workers=len(_CHAINS)) as pool:
        futures = {
            pool.submit(chain, hunk_text, context, llm): name
            for name, chain in _CHAINS
        }
        for future, name in futures.items():
            try:
                results.append(future.result())
            except Exception as exc:  # noqa: BLE001 - one bad chain shouldn't abort the review
                results.append(
                    ChainResult(findings=[], reasoning=f"{name} chain failed: {exc!r}")
                )
    return results


def _dedupe(findings: list[Finding]) -> list[Finding]:
    """Collapse near-identical findings (same file+line+kind), keeping the highest severity."""
    best: dict[tuple, Finding] = {}
    for finding in findings:
        key = (finding.file, finding.line, finding.kind)
        current = best.get(key)
        if current is None or _SEVERITY_RANK[finding.severity] > _SEVERITY_RANK[current.severity]:
            best[key] = finding
    return list(best.values())


def _summarize(findings: list[Finding], hunks: int, files: set[str]) -> str:
    if not findings:
        return f"Reviewed {hunks} hunk(s) across {len(files)} file(s); no findings."
    by_kind = Counter(f.kind for f in findings)
    by_sev = Counter(f.severity for f in findings)
    kinds = ", ".join(f"{by_kind[k]} {k}" for k in ("bug", "style", "refactor") if by_kind[k])
    sev = ", ".join(f"{by_sev[s]} {s}" for s in ("high", "medium", "low") if by_sev[s])
    return (
        f"Reviewed {hunks} hunk(s) across {len(files)} file(s); "
        f"found {len(findings)} finding(s): {kinds} ({sev})."
    )


def review_diff(diff_text: str, repo_path: str, settings: Settings | None = None) -> Review:
    """Review a unified diff and return aggregated, de-duplicated findings.

    For each changed hunk: retrieve codebase context, run the bug / style /
    refactor chains concurrently, and collect their findings. Findings are then
    de-duplicated by (file, line, kind) and summarized.
    """
    settings = settings or Settings()
    patch = PatchSet(diff_text)
    llm = build_llm(settings)

    all_findings: list[Finding] = []
    files: set[str] = set()
    hunk_count = 0

    for patched_file in patch:
        file_path = patched_file.path
        files.add(file_path)
        for hunk in patched_file:
            hunk_count += 1
            hunk_text = str(hunk)
            context = retrieve_for_hunk(
                hunk_text, file_path, top_k=settings.top_k, settings=settings
            )
            for result in _review_hunk(hunk_text, context, llm):
                for finding in result.findings:
                    if not finding.file:
                        finding.file = file_path
                    all_findings.append(finding)

    deduped = _dedupe(all_findings)
    return Review(findings=deduped, summary=_summarize(deduped, hunk_count, files))
