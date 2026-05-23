"""Entrypoint: review the current PR and post the result.

Resolves the repo + PR number from the GitHub Actions environment (or argv when
run locally), indexes the checked-out repo, runs the review, and posts it.

Usage:
    python -m agent.run_on_pr                 # inside GitHub Actions
    python -m agent.run_on_pr <pr_number>     # local, repo from $GITHUB_REPOSITORY
    python -m agent.run_on_pr <owner/repo> <pr_number>
"""

from __future__ import annotations

import json
import os
import sys

from agent.config import Settings
from agent.github_client import GitHubClient
from agent.indexer import index_repo
from agent.reviewer import review_diff


def _pr_number_from_event() -> int | None:
    """Read the PR number from the Actions event payload, if present."""
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not os.path.exists(event_path):
        return None
    with open(event_path, encoding="utf-8") as fh:
        event = json.load(fh)
    if "number" in event:
        return int(event["number"])
    if "pull_request" in event:
        return int(event["pull_request"]["number"])
    return None


def _resolve_target(argv: list[str]) -> tuple[str, int]:
    """Return ``(repo_full_name, pr_number)`` from argv + environment."""
    if len(argv) >= 2:
        return argv[0], int(argv[1])

    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        raise SystemExit("GITHUB_REPOSITORY is not set; pass <owner/repo> <pr_number>.")

    if len(argv) == 1:
        return repo, int(argv[0])

    pr_number = _pr_number_from_event()
    if pr_number is None:
        raise SystemExit("Could not determine the PR number from the event or argv.")
    return repo, pr_number


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    repo_full_name, pr_number = _resolve_target(argv)

    settings = Settings()
    client = GitHubClient(settings=settings)
    repo_path = os.environ.get("GITHUB_WORKSPACE", ".")

    print(f"Indexing {repo_path} ...")
    index_repo(repo_path, settings=settings)

    print(f"Fetching diff for {repo_full_name}#{pr_number} ...")
    diff_text = client.get_pr_diff(repo_full_name, pr_number)

    print("Reviewing diff ...")
    review = review_diff(diff_text, repo_path, settings=settings)

    print(f"Posting review ({len(review.findings)} finding(s)) ...")
    result = client.post_review(repo_full_name, pr_number, review)
    print(f"Done: {result}")


if __name__ == "__main__":
    main()
