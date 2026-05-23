"""GitHub integration: fetch a PR diff and post a structured review.

Uses PyGithub for the object model (pull request, existing reviews) and
``requests`` for the two REST endpoints where raw control is cleaner: fetching
the unified diff and creating a review with ``line``/``side`` inline comments.
"""

from __future__ import annotations

from collections import Counter

import requests
from github import Auth, Github
from unidiff import PatchSet

from agent.config import Settings
from agent.schemas import Finding, Review

API_ROOT = "https://api.github.com"
# Hidden marker stamped into the review body for idempotency.
MARKER = "<!-- agentic-code-review -->"
_TIMEOUT = 30


def _commentable_lines(diff_text: str) -> dict[str, set[int]]:
    """Map each file to the set of RIGHT-side line numbers present in the diff.

    These are the only lines GitHub will accept an inline review comment on
    (added + context lines; removed lines exist only on the LEFT side).
    """
    out: dict[str, set[int]] = {}
    for patched_file in PatchSet(diff_text):
        lines: set[int] = set()
        for hunk in patched_file:
            for line in hunk:
                if line.target_line_no is not None:  # added or context => on RIGHT
                    lines.add(line.target_line_no)
        out[patched_file.path] = lines
    return out


def _format_inline(finding: Finding) -> str:
    parts = [f"**[{finding.kind} / {finding.severity}] {finding.summary}**", "", finding.detail]
    if finding.suggested_fix:
        parts += ["", f"_Suggested fix:_ {finding.suggested_fix}"]
    return "\n".join(parts)


def _format_bullet(finding: Finding) -> str:
    loc = f"`{finding.file}:{finding.line}`" if finding.line is not None else f"`{finding.file}`"
    bullet = f"- **[{finding.kind} / {finding.severity}]** {finding.summary} ({loc})"
    if finding.suggested_fix:
        bullet += f" — _fix:_ {finding.suggested_fix}"
    return bullet


def _counts(findings: list[Finding]) -> str:
    if not findings:
        return "_No findings._"
    by_kind = Counter(f.kind for f in findings)
    by_sev = Counter(f.severity for f in findings)
    kinds = ", ".join(f"{by_kind[k]} {k}" for k in ("bug", "style", "refactor") if by_kind[k])
    sev = ", ".join(f"{by_sev[s]} {s}" for s in ("high", "medium", "low") if by_sev[s])
    return f"**By kind:** {kinds}  \n**By severity:** {sev}"


def _build_body(review: Review, listed: list[Finding], heading: str) -> str:
    """Assemble the review body: marker, counts, overall summary, listed findings."""
    lines = [MARKER, "## 🤖 Agentic Code Review", ""]
    if review.summary:
        lines += [review.summary, ""]
    lines += [_counts(review.findings), ""]
    if listed:
        lines += [f"### {heading}", ""]
        lines += [_format_bullet(f) for f in listed]
    return "\n".join(lines).rstrip() + "\n"


class GitHubClient:
    """Thin GitHub client for fetching diffs and posting reviews."""

    def __init__(self, token: str | None = None, settings: Settings | None = None) -> None:
        if token is None:
            settings = settings or Settings()
            token = settings.github_token
        self.token = token
        self.gh = Github(auth=Auth.Token(token))

    def _headers(self, accept: str = "application/vnd.github+json") -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def get_pr_diff(self, repo_full_name: str, pr_number: int) -> str:
        """Return the unified diff for a PR."""
        url = f"{API_ROOT}/repos/{repo_full_name}/pulls/{pr_number}"
        resp = requests.get(
            url, headers=self._headers("application/vnd.github.diff"), timeout=_TIMEOUT
        )
        resp.raise_for_status()
        return resp.text

    def _already_reviewed(self, pr, head_sha: str) -> bool:
        """True if a prior bot review (matching marker) exists for ``head_sha``."""
        for review in pr.get_reviews():
            if MARKER in (review.body or "") and review.commit_id == head_sha:
                return True
        return False

    def _split_findings(
        self, findings: list[Finding], commentable: dict[str, set[int]]
    ) -> tuple[list[dict], list[Finding]]:
        """Partition findings into inline comments and body-only leftovers."""
        comments: list[dict] = []
        leftover: list[Finding] = []
        for finding in findings:
            if finding.line is not None and finding.line in commentable.get(finding.file, set()):
                comments.append(
                    {
                        "path": finding.file,
                        "line": finding.line,
                        "side": "RIGHT",
                        "body": _format_inline(finding),
                    }
                )
            else:
                leftover.append(finding)
        return comments, leftover

    def post_review(self, repo_full_name: str, pr_number: int, review: Review) -> dict:
        """Create a single PR review with inline comments + a summary body.

        Idempotent: if a prior bot review already exists for the PR's head
        commit, this is a no-op. Findings whose line isn't present in the diff
        (and line-less findings) are collected into the review body rather than
        causing the inline comment to fail.
        """
        pr = self.gh.get_repo(repo_full_name).get_pull(pr_number)
        head_sha = pr.head.sha

        if self._already_reviewed(pr, head_sha):
            return {"status": "skipped", "reason": f"already reviewed {head_sha}"}

        diff_text = self.get_pr_diff(repo_full_name, pr_number)
        commentable = _commentable_lines(diff_text)
        comments, leftover = self._split_findings(review.findings, commentable)

        body = _build_body(review, leftover, "Findings not attached to a diff line")
        url = f"{API_ROOT}/repos/{repo_full_name}/pulls/{pr_number}/reviews"
        payload = {
            "commit_id": head_sha,
            "body": body,
            "event": "COMMENT",
            "comments": comments,
        }
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=_TIMEOUT)

        # Safety net: if GitHub rejects an inline comment (422), retry with
        # every finding in the body instead of failing the whole review.
        if resp.status_code == 422 and comments:
            fallback = _build_body(review, review.findings, "All findings")
            resp = requests.post(
                url,
                headers=self._headers(),
                json={"commit_id": head_sha, "body": fallback, "event": "COMMENT", "comments": []},
                timeout=_TIMEOUT,
            )
            comments = []

        resp.raise_for_status()
        return {
            "status": "posted",
            "commit": head_sha,
            "inline_comments": len(comments),
            "body_findings": len(leftover) if comments else len(review.findings),
        }
