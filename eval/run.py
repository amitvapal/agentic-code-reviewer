"""Run the benchmark and write results.json + REPORT.md.

This makes real Claude calls — it is a measurement, not a unit test. To keep
cost low it runs only a few cases by default; use --all for the full benchmark.

    python -m eval.run --cheap        # ~few cents: 2 bug cases, no fix (recommended)
    python -m eval.run                # small default: first 2 cases, with fix
    python -m eval.run --dry-run      # print the plan + call estimate, run nothing
    python -m eval.run --all --yes    # full benchmark (confirmation required)

Cost is dominated by Claude calls: 3 chains per case, plus up to one extra call
per flagged test-breaking case when fix application is on. Embeddings/indexing
run locally and don't hit the API.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from agent.config import Settings
from eval.harness import aggregate, discover_cases, evaluate_case

EVAL_DIR = Path(__file__).parent
BENCHMARK_DIR = EVAL_DIR / "benchmark"

DEFAULT_LIMIT = 2          # cases to run when neither --limit nor --all is given
CHAINS_PER_CASE = 3        # bug + style + refactor
CONFIRM_THRESHOLD = 20     # estimated Claude calls above which --yes is required
VALID_KINDS = {"bug", "style", "refactor"}


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.0f}%"


def _prf_row(name: str, m: dict) -> str:
    return (
        f"| {name} | {m['precision']:.2f} | {m['recall']:.2f} | {m['f1']:.2f} | "
        f"{m['tp']} | {m['fp']} | {m['labels_found']}/{m['labels']} |"
    )


def write_report(summary: dict, case_results: list[dict], path: Path) -> None:
    tb = summary["test_breaking"]
    fix = summary["fix_correctness"]
    lines = [
        "# Agentic Code Review — Eval Report",
        "",
        f"_Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}_",
        "",
        f"- **Cases:** {summary['n_cases']}",
        f"- **Test-breaking defects flagged:** {tb['flagged']}/{tb['total']} "
        f"({_pct(tb['flag_rate'])}) — the signal that matters most",
        f"- **Defects confirmed green→red:** {tb['confirmed_green_to_red']}/{tb['total']}",
        f"- **Fix correctness:** {fix['correct']}/{fix['attempts']} ({_pct(fix['rate'])})",
        "",
        "## Detection quality",
        "",
        "Precision is finding-level (matched findings / all findings); recall is "
        "label-level (labels found / labels). A finding matches a label on "
        "(file, kind, line ± 3).",
        "",
        "| Scope | Precision | Recall | F1 | TP | FP | Labels found |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        _prf_row("overall", summary["overall"]),
    ]
    for kind, m in summary["by_kind"].items():
        lines.append(_prf_row(kind, m))

    lines += [
        "",
        "## Per-case results",
        "",
        "| Case | Kind | Breaks tests | green→red | Flagged | Findings | Ruff warns | Fix |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for c in case_results:
        if "error" in c:
            lines.append(f"| {c['case']} | {c['label']['kind']} | — | — | — | — | — | ERROR: {c['error']} |")
            continue
        fix_cell = "—" if not c["fix_attempted"] else ("✅" if c["fix_correct"] else "❌")
        ruff = "—" if c["ruff_warnings"] is None else str(c["ruff_warnings"])
        lines.append(
            f"| {c['case']} | {c['label']['kind']} | {c['label']['breaks_tests']} | "
            f"{'✅' if c['defect_confirmed'] else ('—' if not c['label']['breaks_tests'] else '❌')} | "
            f"{'✅' if c['matched'] else '❌'} | {c['n_findings']} | {ruff} | {fix_cell} |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _select_cases(
    benchmark_dir: Path, kinds: set[str] | None, limit: int | None
) -> list[tuple[Path, dict]]:
    """Return (case_dir, label) pairs filtered by kind and capped at limit."""
    selected: list[tuple[Path, dict]] = []
    for case_dir in discover_cases(benchmark_dir):
        label = json.loads((case_dir / "labels.json").read_text())
        if kinds and label["kind"] not in kinds:
            continue
        selected.append((case_dir, label))
    if limit is not None:
        selected = selected[:limit]
    return selected


def _print_plan(
    selected: list[tuple[Path, dict]],
    kinds: set[str] | None,
    apply_fixes: bool,
    est_low: int,
    est_high: int,
) -> None:
    kind_label = ",".join(sorted(kinds)) if kinds else "all"
    breaking = sum(1 for _, lbl in selected if lbl.get("breaks_tests"))
    est = f"~{est_low}" if est_low == est_high else f"~{est_low}–{est_high}"
    print("Eval plan:")
    print(f"  Cases selected:         {len(selected)}  (kinds: {kind_label})")
    print(f"  Chains per case:        {CHAINS_PER_CASE}  -> {len(selected) * CHAINS_PER_CASE} chain calls")
    print("  Single-shot baseline:   no")
    if apply_fixes:
        print(f"  Fix application:        enabled (up to {breaking} extra calls on flagged test-breaking cases)")
    else:
        print("  Fix application:        disabled")
    print(f"  Estimated Claude calls: {est}  (rough; excludes local embeddings, +1 per chain on JSON repair)")
    for case_dir, label in selected:
        print(f"    - {case_dir.name} [{label['kind']}]")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the review-agent eval benchmark.")
    parser.add_argument("--limit", type=int, default=None, help=f"Run only the first N cases (default {DEFAULT_LIMIT}).")
    parser.add_argument("--all", action="store_true", help="Run the full benchmark (overrides --limit).")
    parser.add_argument("--kinds", default=None, help="Comma-separated label kinds to include, e.g. 'bug' or 'bug,style'.")
    parser.add_argument("--no-fix", action="store_true", help="Skip suggested-fix application and test reruns.")
    parser.add_argument("--cheap", action="store_true", help="Cheapest useful run: bug cases only, no fix, small limit.")
    parser.add_argument("--yes", action="store_true", help="Proceed without confirmation for expensive runs.")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan + call estimate and exit (no API calls).")
    parser.add_argument("--benchmark", default=str(BENCHMARK_DIR), help="Benchmark directory.")
    args = parser.parse_args(argv)

    # Resolve kinds.
    kinds: set[str] | None = None
    if args.kinds:
        kinds = {k.strip() for k in args.kinds.split(",") if k.strip()}
        unknown = kinds - VALID_KINDS
        if unknown:
            raise SystemExit(f"Unknown kind(s): {sorted(unknown)}; valid: {sorted(VALID_KINDS)}")

    # Resolve fixes + limit, applying --cheap defaults only where not set explicitly.
    apply_fixes = not args.no_fix
    if args.cheap:
        apply_fixes = False
        if kinds is None:
            kinds = {"bug"}
    limit = None if args.all else (args.limit if args.limit is not None else DEFAULT_LIMIT)

    selected = _select_cases(Path(args.benchmark), kinds, limit)
    if not selected:
        raise SystemExit("No matching cases. Check --kinds / --benchmark.")

    chain_calls = len(selected) * CHAINS_PER_CASE
    fix_upper = sum(1 for _, lbl in selected if lbl.get("breaks_tests")) if apply_fixes else 0
    est_low, est_high = chain_calls, chain_calls + fix_upper

    _print_plan(selected, kinds, apply_fixes, est_low, est_high)

    if args.dry_run:
        print("\nDry run — nothing executed.")
        return

    if est_high > CONFIRM_THRESHOLD and not args.yes:
        raise SystemExit(
            f"\nThis run may make ~{est_high} Claude calls (> {CONFIRM_THRESHOLD}). "
            "Re-run with --yes to proceed, or use --cheap / --limit for a smaller run."
        )

    settings = Settings()
    results = []
    for case_dir, _label in selected:
        print(f"Evaluating {case_dir.name} ...")
        results.append(evaluate_case(case_dir, settings, apply_fixes=apply_fixes))

    summary = aggregate(results)
    (EVAL_DIR / "results.json").write_text(
        json.dumps({"summary": summary, "cases": results}, indent=2) + "\n", encoding="utf-8"
    )
    write_report(summary, results, EVAL_DIR / "REPORT.md")

    tb = summary["test_breaking"]
    print(
        f"\nDone: {summary['n_cases']} cases | "
        f"overall F1 {summary['overall']['f1']:.2f} | "
        f"test-breaking flagged {tb['flagged']}/{tb['total']} | "
        f"results.json + REPORT.md written to {EVAL_DIR}"
    )


if __name__ == "__main__":
    main()
