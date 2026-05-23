# agentic-code-review

An autonomous PR-review agent (FastAPI + Claude), deployed as a single Docker container. Skeleton — to be fleshed out.

## Evaluation

The eval harness scores review quality against a labeled benchmark (`eval/benchmark/`) using execution signals (pytest green→red), static analysis (ruff), and detection metrics (precision/recall/F1). It makes **real Claude calls**, so it costs money — runs are kept small by default.

**Recommended first run (a few cents):**

```bash
python -m eval.run --cheap
```

`--cheap` runs only bug cases, no fix application, capped at 2 cases — roughly **6 Claude calls**. It still produces real `eval/results.json` + `eval/REPORT.md` and proves the harness end-to-end.

**See the cost before spending anything:**

```bash
python -m eval.run --dry-run            # prints the plan + estimated call count, runs nothing
python -m eval.run --all --dry-run      # what the full benchmark would cost
```

**Other modes:**

| Command | What it runs |
| --- | --- |
| `python -m eval.run --cheap` | 2 bug cases, no fix (~6 calls) — **recommended** |
| `python -m eval.run` | first 2 cases, with fix (~6–8 calls) |
| `python -m eval.run --kinds bug,style --limit 3` | filter by kind, cap count |
| `python -m eval.run --no-fix` | skip the (expensive) fix-correctness signal |
| `python -m eval.run --all --yes` | full benchmark (confirmation required) |

Runs estimated above ~20 Claude calls require `--yes`. Requires `ANTHROPIC_API_KEY` in the environment (or `.env`).
