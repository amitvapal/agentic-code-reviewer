"""FastAPI service for the read-only review demo + dashboard.

Routes:
    GET  /api/health   -> {"status": "ok"}
    POST /api/review   -> review a public PR's diff (read-only; no posting back)
    GET  /api/metrics  -> the eval results.json the dashboard renders
    /                  -> the static dashboard (mounted LAST so it can't shadow /api)

Heavy imports (the agent pipeline) are deferred into the review handler so the
health check, metrics, and static assets stay fast and dependency-light.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent.config import Settings

# Repo root locally; /app inside the container.
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(os.environ.get("STATIC_DIR", BASE_DIR / "frontend"))
METRICS_CANDIDATES = [BASE_DIR / "eval" / "results.json", BASE_DIR / "eval" / "results.sample.json"]

PR_URL_RE = re.compile(r"^https?://github\.com/([^/\s]+)/([^/\s]+)/pull/(\d+)")

REVIEW_RATE_LIMIT = 5          # requests
REVIEW_RATE_PERIOD = 60.0      # per this many seconds, per client IP

app = FastAPI(title="Agentic Code Review", description="Read-only PR review demo")


class _RateLimiter:
    """A tiny in-memory sliding-window limiter (single-container demo)."""

    def __init__(self, max_calls: int, period: float) -> None:
        self.max_calls = max_calls
        self.period = period
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.period
        with self._lock:
            recent = [t for t in self._hits[key] if t > cutoff]
            if len(recent) >= self.max_calls:
                self._hits[key] = recent
                return False
            recent.append(now)
            self._hits[key] = recent
            return True


review_limiter = _RateLimiter(REVIEW_RATE_LIMIT, REVIEW_RATE_PERIOD)


class ReviewRequest(BaseModel):
    pr_url: str


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/metrics")
def metrics() -> JSONResponse:
    for path in METRICS_CANDIDATES:
        if path.exists():
            return JSONResponse(json.loads(path.read_text(encoding="utf-8")))
    return JSONResponse(
        {"available": False, "message": "Run `python -m eval.run` to generate metrics."}
    )


@app.get("/api/config")
def config() -> dict:
    """Non-secret runtime config the dashboard surfaces on the Settings page."""
    settings = Settings()
    return {
        "model": settings.anthropic_model,
        "read_only": True,
        "rag_enabled": False,
        "public_repos_only": True,
        "rate_limit_per_min": REVIEW_RATE_LIMIT,
    }


@app.post("/api/review")
def review(req: ReviewRequest, request: Request) -> dict:
    client_ip = request.client.host if request.client else "anonymous"
    if not review_limiter.allow(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in a minute.")

    match = PR_URL_RE.match(req.pr_url.strip())
    if not match:
        raise HTTPException(
            status_code=400,
            detail="Expected a URL like https://github.com/owner/repo/pull/123",
        )
    owner, repo, number = match.group(1), match.group(2), int(match.group(3))
    repo_full = f"{owner}/{repo}"

    # Deferred imports: keep startup, health, and metrics light.
    from agent.github_client import GitHubClient
    from agent.reviewer import review_diff

    settings = Settings()
    client = GitHubClient(settings=settings)

    try:
        public = client.repo_is_public(repo_full)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Repository {repo_full} not found or inaccessible.")
    if not public:
        raise HTTPException(status_code=403, detail="Demo mode only supports public repositories.")

    try:
        diff_text = client.get_pr_diff(repo_full, number)
    except Exception as exc:  # noqa: BLE001 - surface a clean error to the client
        raise HTTPException(status_code=502, detail=f"Could not fetch the PR diff: {exc}")

    try:
        # retrieve=False: the repo isn't checked out in the demo, so review the
        # diff without RAG context (and without the heavy embedding deps).
        result = review_diff(diff_text, repo_full, settings=settings, retrieve=False)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Review failed: {exc}")

    # Enrich the response with the diff + PR metadata so the dashboard can render
    # a changed-files panel and a diff viewer. (Additive — the Review schema is
    # unchanged; this is just the wire payload.)
    payload = result.model_dump()
    payload.update(
        {
            "repo": repo_full,
            "pr_number": number,
            "pr_url": req.pr_url.strip(),
            "diff": diff_text,
        }
    )
    return payload


# Mount the dashboard LAST so it doesn't shadow /api/*.
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
else:  # pragma: no cover - only when the frontend isn't present

    @app.get("/")
    def _root() -> dict:
        return {"message": "Frontend not built. API is up — see /api/health."}
