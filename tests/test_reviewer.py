"""review_diff aggregates and de-dupes findings, with the LLM fully mocked."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from agent.config import Settings
from agent.reviewer import review_diff
from agent.schemas import Review

FIXTURE_REPO = Path(__file__).parent / "fixtures" / "sample_repo"

# An off-by-one bug introduced into the fixture's fibonacci loop.
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

# Canned, per-chain responses. The bug chain returns the *same* finding twice
# (different severities) so we can assert de-dup keeps the higher severity.
_BUG_PAYLOAD = {
    "reasoning": "range(n + 1) iterates one extra time, so it returns fib(n+1).",
    "findings": [
        {
            "kind": "bug",
            "file": "math_utils.py",
            "line": 7,
            "severity": "high",
            "summary": "Off-by-one in fibonacci loop",
            "detail": "range(n + 1) runs one iteration too many.",
            "suggested_fix": "Use range(n).",
        },
        {
            "kind": "bug",
            "file": "math_utils.py",
            "line": 7,
            "severity": "low",
            "summary": "Loop bound looks suspicious",
            "detail": "The loop count may be wrong.",
            "suggested_fix": None,
        },
    ],
}
_STYLE_PAYLOAD = {
    "reasoning": "Naming and docstring look consistent with the codebase.",
    "findings": [
        {
            "kind": "style",
            "file": "math_utils.py",
            "line": 5,
            "severity": "low",
            "summary": "Docstring could mention the off-by-one semantics",
            "detail": "Minor wording nit.",
            "suggested_fix": None,
        }
    ],
}
_REFACTOR_PAYLOAD = {
    "reasoning": "The loop is fine but could be expressed more clearly.",
    "findings": [
        {
            "kind": "refactor",
            "file": "math_utils.py",
            "line": None,
            "severity": "low",
            "summary": "Extract the iterative step",
            "detail": "Readability improvement.",
            "suggested_fix": "Add a helper or comment clarifying the recurrence.",
        }
    ],
}


def _system_text(messages) -> str:
    content = messages[0].content
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content if isinstance(b, dict))
    return content


def _fake_invoke(messages):
    """Return the canned payload matching the chain's system prompt."""
    system = _system_text(messages)
    if "bug-finder" in system:
        payload = _BUG_PAYLOAD
    elif "code-style" in system:
        payload = _STYLE_PAYLOAD
    else:
        payload = _REFACTOR_PAYLOAD
    return SimpleNamespace(content=json.dumps(payload))


def test_review_diff_aggregates_and_dedupes():
    settings = Settings(_env_file=None, anthropic_api_key="test")
    context = [
        {
            "path": "math_utils.py",
            "start_line": 1,
            "end_line": 9,
            "text": "def fibonacci(n): ...",
            "score": 0.9,
            "same_file": True,
        }
    ]

    with (
        patch("agent.chains.ChatAnthropic") as mock_chat,
        patch("agent.reviewer.retrieve_for_hunk", return_value=context) as mock_retrieve,
    ):
        mock_chat.return_value.invoke.side_effect = _fake_invoke
        review = review_diff(DIFF, str(FIXTURE_REPO), settings=settings)

    assert isinstance(review, Review)

    # 4 raw findings (2 bug + 1 style + 1 refactor) collapse to 3 after de-dup.
    assert len(review.findings) == 3
    assert sorted(f.kind for f in review.findings) == ["bug", "refactor", "style"]

    # De-dup keeps the higher-severity duplicate.
    bug = next(f for f in review.findings if f.kind == "bug")
    assert bug.severity == "high"
    assert bug.summary == "Off-by-one in fibonacci loop"

    # Summary reflects the de-duplicated counts.
    assert "3 finding(s)" in review.summary
    assert "1 bug" in review.summary

    # Retrieval was invoked for the hunk, scoped to the changed file.
    mock_retrieve.assert_called_once()
    assert mock_retrieve.call_args.args[1] == "math_utils.py"
