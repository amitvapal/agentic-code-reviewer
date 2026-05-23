"""GitHubClient: inline vs. body routing, and the idempotency marker."""

from unittest.mock import MagicMock, patch

from agent.github_client import MARKER, GitHubClient
from agent.schemas import Finding, Review

# math_utils.py RIGHT-side lines present in this diff: 4..9 (line 7 is added).
DIFF = '''\
--- a/math_utils.py
+++ b/math_utils.py
@@ -4,6 +4,6 @@ def fibonacci(n):
 def fibonacci(n):
     """Return the nth Fibonacci number, computed iteratively."""
     a, b = 0, 1
-    for _ in range(n):
+    for _ in range(n + 1):
         a, b = b, a + b
     return a
'''

REVIEW = Review(
    summary="Reviewed 1 hunk(s) across 1 file(s); found 3 finding(s).",
    findings=[
        Finding(
            kind="bug", file="math_utils.py", line=7, severity="high",
            summary="Off-by-one in fibonacci loop",
            detail="range(n + 1) runs one iteration too many.",
            suggested_fix="Use range(n).",
        ),
        Finding(
            kind="style", file="math_utils.py", line=999, severity="low",
            summary="comment about a line not in diff",
            detail="This line is outside the changed hunk.",
        ),
        Finding(
            kind="refactor", file="math_utils.py", line=None, severity="low",
            summary="file-level line-less suggestion",
            detail="Applies to the whole file.",
            suggested_fix="Extract a helper.",
        ),
    ],
)


def _mock_pr(head_sha="abc123", reviews=None):
    pr = MagicMock()
    pr.head.sha = head_sha
    pr.get_reviews.return_value = reviews or []
    return pr


def _client_with(mock_github, pr):
    mock_github.return_value.get_repo.return_value.get_pull.return_value = pr
    return GitHubClient(token="x")


def test_inline_vs_body_routing():
    pr = _mock_pr()
    with (
        patch("agent.github_client.Github") as mock_github,
        patch("agent.github_client.requests") as mock_requests,
    ):
        mock_requests.get.return_value = MagicMock(text=DIFF, status_code=200)
        mock_requests.post.return_value = MagicMock(status_code=200)
        client = _client_with(mock_github, pr)

        result = client.post_review("o/r", 1, REVIEW)

    payload = mock_requests.post.call_args.kwargs["json"]

    # The in-diff finding (line 7) becomes a single RIGHT-side inline comment.
    assert len(payload["comments"]) == 1
    comment = payload["comments"][0]
    assert comment["path"] == "math_utils.py"
    assert comment["line"] == 7
    assert comment["side"] == "RIGHT"
    assert "Off-by-one" in comment["body"]
    assert payload["commit_id"] == "abc123"

    # Line-less + out-of-diff findings fall back to body bullets (not inline).
    body = payload["body"]
    assert MARKER in body
    assert "comment about a line not in diff" in body
    assert "file-level line-less suggestion" in body
    assert "Off-by-one" not in body

    assert result["status"] == "posted"
    assert result["inline_comments"] == 1


def test_skips_when_already_reviewed_for_head():
    prior = MagicMock(body=f"{MARKER}\nold review", commit_id="abc123")
    pr = _mock_pr(head_sha="abc123", reviews=[prior])
    with (
        patch("agent.github_client.Github") as mock_github,
        patch("agent.github_client.requests") as mock_requests,
    ):
        client = _client_with(mock_github, pr)
        result = client.post_review("o/r", 1, REVIEW)

    assert result["status"] == "skipped"
    mock_requests.post.assert_not_called()
    mock_requests.get.assert_not_called()


def test_posts_again_when_prior_review_is_for_old_commit():
    stale = MagicMock(body=f"{MARKER}\nold review", commit_id="oldsha")
    pr = _mock_pr(head_sha="abc123", reviews=[stale])
    with (
        patch("agent.github_client.Github") as mock_github,
        patch("agent.github_client.requests") as mock_requests,
    ):
        mock_requests.get.return_value = MagicMock(text=DIFF, status_code=200)
        mock_requests.post.return_value = MagicMock(status_code=200)
        client = _client_with(mock_github, pr)
        result = client.post_review("o/r", 1, REVIEW)

    assert result["status"] == "posted"
    mock_requests.post.assert_called_once()
