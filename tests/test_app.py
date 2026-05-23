"""FastAPI service: health, metrics, review routing, validation, rate limiting."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import REVIEW_RATE_LIMIT, app, review_limiter
from agent.schemas import Finding, Review

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_limiter():
    review_limiter._hits.clear()
    yield
    review_limiter._hits.clear()


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_metrics_serves_sample():
    resp = client.get("/api/metrics")
    assert resp.status_code == 200
    body = resp.json()
    # The committed sample is present until a real run overwrites results.json.
    assert "summary" in body
    assert body["summary"]["overall"]["precision"] >= 0


def test_config_endpoint():
    resp = client.get("/api/config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["read_only"] is True
    assert body["public_repos_only"] is True
    assert "model" in body
    assert body["rate_limit_per_min"] == REVIEW_RATE_LIMIT


def test_review_rejects_bad_url():
    resp = client.post("/api/review", json={"pr_url": "not-a-pr"})
    assert resp.status_code == 400


def test_dashboard_served_at_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Agentic Review" in resp.text  # title in the static shell
    assert "/app.js" in resp.text  # SPA bootstraps from here


def test_static_assets_served():
    for path in ("/app.js", "/styles.css"):
        assert client.get(path).status_code == 200


def test_review_happy_path_mocked():
    review = Review(
        summary="1 finding",
        findings=[
            Finding(
                kind="bug", file="m.py", line=7, severity="high",
                summary="Off-by-one", detail="loop bound", suggested_fix="use range(n)",
            )
        ],
    )
    fake_client = MagicMock()
    fake_client.repo_is_public.return_value = True
    fake_client.get_pr_diff.return_value = "diff --git a/m.py b/m.py\n"

    with (
        patch("agent.github_client.GitHubClient", return_value=fake_client),
        patch("agent.reviewer.review_diff", return_value=review) as mock_review,
    ):
        resp = client.post(
            "/api/review", json={"pr_url": "https://github.com/owner/repo/pull/12"}
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"] == "1 finding"
    assert body["findings"][0]["kind"] == "bug"
    # Response is enriched with diff + PR metadata for the dashboard.
    assert body["repo"] == "owner/repo"
    assert body["pr_number"] == 12
    assert "diff" in body
    # Demo is read-only and RAG-free.
    assert mock_review.call_args.kwargs["retrieve"] is False
    fake_client.repo_is_public.assert_called_once_with("owner/repo")


def test_review_blocks_private_repo():
    fake_client = MagicMock()
    fake_client.repo_is_public.return_value = False
    with patch("agent.github_client.GitHubClient", return_value=fake_client):
        resp = client.post(
            "/api/review", json={"pr_url": "https://github.com/owner/private/pull/1"}
        )
    assert resp.status_code == 403


def test_review_rate_limited():
    # Exhaust the limiter for the test client's IP, then expect 429.
    for _ in range(REVIEW_RATE_LIMIT):
        review_limiter.allow("testclient")
    resp = client.post("/api/review", json={"pr_url": "https://github.com/o/r/pull/1"})
    assert resp.status_code == 429
