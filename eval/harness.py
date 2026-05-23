"""Score the agent's review quality against the labeled benchmark.

For each case we: copy ``before/`` to a temp dir, confirm its tests pass, apply
``diff.patch``, re-run the tests (the execution signal that the defect is real),
run ruff (static signal), then run ``review_diff`` and score its findings
against ``labels.json``. Test-breaking defects that the agent flagged can have
their suggested fix applied and re-tested (the fix-correctness signal).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from agent.claude_client import ClaudeClient
from agent.config import Settings
from agent.indexer import index_repo
from agent.reviewer import review_diff

KINDS = ("bug", "style", "refactor")
# A finding's line may match a label within this many lines (LLMs are imprecise).
LINE_WINDOW = 3


# --------------------------------------------------------------------------- #
# Execution + static signals
# --------------------------------------------------------------------------- #
def _run_pytest(workdir: Path) -> bool:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=workdir,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def _apply_patch(workdir: Path, patch_path: Path) -> bool:
    proc = subprocess.run(
        ["git", "apply", "-p1", str(patch_path)],
        cwd=workdir,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return True
    with open(patch_path) as fh:  # fall back to patch(1)
        proc2 = subprocess.run(
            ["patch", "-p1", "-f", "-s"], cwd=workdir, stdin=fh, capture_output=True, text=True
        )
    return proc2.returncode == 0


def _ruff_command() -> list[str] | None:
    """Locate ruff, preferring the current interpreter's env (PATH-independent)."""
    sibling = Path(sys.executable).parent / "ruff"
    if sibling.exists():
        return [str(sibling)]
    on_path = shutil.which("ruff")
    if on_path:
        return [on_path]
    # Last resort: run as a module under the current interpreter.
    probe = subprocess.run(
        [sys.executable, "-m", "ruff", "--version"], capture_output=True, text=True
    )
    return [sys.executable, "-m", "ruff"] if probe.returncode == 0 else None


def _run_ruff(workdir: Path) -> int | None:
    cmd = _ruff_command()
    if cmd is None:
        return None
    proc = subprocess.run(
        [*cmd, "check", str(workdir), "--output-format=json"],
        capture_output=True,
        text=True,
    )
    try:
        return len(json.loads(proc.stdout or "[]"))
    except json.JSONDecodeError:
        return None


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #
def _matches(file: str, kind: str, line: int | None, label: dict, window: int = LINE_WINDOW) -> bool:
    if file != label["file"] or kind != label["kind"] or line is None:
        return False
    return abs(line - label["line"]) <= window


# --------------------------------------------------------------------------- #
# Fix-correctness signal
# --------------------------------------------------------------------------- #
def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return text
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines) + "\n"


def _attempt_fix(workdir: Path, finding, settings: Settings) -> bool | None:
    """Apply a finding's suggested fix via the model and re-run the tests."""
    target = workdir / finding.file
    if not target.exists():
        return None
    original = target.read_text(encoding="utf-8")
    client = ClaudeClient(settings=settings)
    system = (
        "You are applying a single, minimal code fix to a file. Return ONLY the "
        "complete corrected contents of the file — no explanation, no markdown, "
        "no code fences."
    )
    user = (
        f"File `{finding.file}`:\n\n{original}\n\n"
        f"Apply this fix:\n"
        f"Issue: {finding.summary}\n"
        f"Details: {finding.detail}\n"
        f"Suggested fix: {finding.suggested_fix}\n\n"
        "Return the full corrected file contents."
    )
    fixed = _strip_code_fences(client.complete(system, user, max_tokens=2048))
    target.write_text(fixed, encoding="utf-8")
    passed = _run_pytest(workdir)
    if not passed:  # leave the workdir consistent for any later inspection
        target.write_text(original, encoding="utf-8")
    return passed


# --------------------------------------------------------------------------- #
# Per-case evaluation
# --------------------------------------------------------------------------- #
def evaluate_case(case_dir: Path, base_settings: Settings, apply_fixes: bool = True) -> dict:
    label = json.loads((case_dir / "labels.json").read_text())
    patch_path = case_dir / "diff.patch"
    diff_text = patch_path.read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp) / "work"
        shutil.copytree(case_dir / "before", workdir)

        before_passed = _run_pytest(workdir)
        if not _apply_patch(workdir, patch_path):
            return {"case": case_dir.name, "label": label, "error": "patch failed to apply"}
        after_passed = _run_pytest(workdir)
        ruff_warnings = _run_ruff(workdir)

        # Index the patched tree so retrieval has real codebase context.
        settings = base_settings.model_copy(update={"chroma_dir": str(Path(tmp) / "chroma")})
        index_repo(str(workdir), settings=settings)
        review = review_diff(diff_text, str(workdir), settings=settings)

        findings = review.findings
        matched = [f for f in findings if _matches(f.file, f.kind, f.line, label)]

        fix_attempted = False
        fix_correct: bool | None = None
        if apply_fixes and label.get("breaks_tests") and matched:
            candidate = next((f for f in matched if f.suggested_fix), None)
            if candidate is not None:
                fix_attempted = True
                fix_correct = _attempt_fix(workdir, candidate, settings)

    return {
        "case": case_dir.name,
        "label": label,
        "before_passed": before_passed,
        "after_passed": after_passed,
        "defect_confirmed": bool(before_passed and not after_passed),
        "ruff_warnings": ruff_warnings,
        "n_findings": len(findings),
        "findings": [f.model_dump() for f in findings],
        "matched": bool(matched),
        "n_true_positive": len(matched),
        "fix_attempted": fix_attempted,
        "fix_correct": fix_correct,
    }


# --------------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------------- #
def _prf(tp: int, fp: int, labels_total: int, labels_found: int) -> dict:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = labels_found / labels_total if labels_total else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "tp": tp,
        "fp": fp,
        "labels": labels_total,
        "labels_found": labels_found,
    }


def aggregate(case_results: list[dict]) -> dict:
    cases = [c for c in case_results if "error" not in c]

    total_findings = sum(c["n_findings"] for c in cases)
    tp_findings = sum(c["n_true_positive"] for c in cases)
    overall = _prf(tp_findings, total_findings - tp_findings, len(cases), sum(c["matched"] for c in cases))

    by_kind = {}
    for kind in KINDS:
        kind_total = kind_tp = 0
        for c in cases:
            for f in c["findings"]:
                if f["kind"] != kind:
                    continue
                kind_total += 1
                if c["label"]["kind"] == kind and _matches(f["file"], f["kind"], f["line"], c["label"]):
                    kind_tp += 1
        kind_cases = [c for c in cases if c["label"]["kind"] == kind]
        by_kind[kind] = _prf(
            kind_tp,
            kind_total - kind_tp,
            len(kind_cases),
            sum(c["matched"] for c in kind_cases),
        )

    breaking = [c for c in cases if c["label"].get("breaks_tests")]
    flagged = sum(c["matched"] for c in breaking)
    fix_attempts = sum(c["fix_attempted"] for c in cases)
    fix_correct = sum(1 for c in cases if c.get("fix_correct"))

    return {
        "n_cases": len(cases),
        "overall": overall,
        "by_kind": by_kind,
        "test_breaking": {
            "total": len(breaking),
            "confirmed_green_to_red": sum(c["defect_confirmed"] for c in breaking),
            "flagged": flagged,
            "flag_rate": round(flagged / len(breaking), 3) if breaking else None,
        },
        "fix_correctness": {
            "attempts": fix_attempts,
            "correct": fix_correct,
            "rate": round(fix_correct / fix_attempts, 3) if fix_attempts else None,
        },
        "errors": [c for c in case_results if "error" in c],
    }


def discover_cases(benchmark_dir: Path) -> list[Path]:
    return sorted(
        p for p in benchmark_dir.iterdir() if p.is_dir() and (p / "labels.json").exists()
    )
