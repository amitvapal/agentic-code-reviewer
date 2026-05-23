"""Three Chain-of-Thought review chains built on ``ChatAnthropic``.

Each chain takes a diff hunk plus retrieved RAG context, asks the model to
reason step-by-step *before* emitting findings, enforces JSON-only output, and
parses it with the ``complete_json`` repair pattern (one retry on malformed or
schema-invalid JSON).
"""

from __future__ import annotations

import json

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from agent.config import Settings
from agent.jsonparse import loads_json
from agent.schemas import ChainResult

# Shared output contract: enforces JSON-only output with reasoning-first CoT.
_CONTRACT = (
    "Respond with a SINGLE JSON object and nothing else — no prose before or "
    "after it, and no markdown code fences.\n"
    "The object must have exactly these two keys:\n"
    '  - "reasoning": a string containing your step-by-step analysis.\n'
    '  - "findings": an array of finding objects.\n'
    "Each finding object has exactly these keys:\n"
    '  - "kind": one of "bug", "style", "refactor"\n'
    '  - "file": the file path the finding applies to (string)\n'
    '  - "line": the affected line number (integer), or null\n'
    '  - "severity": one of "low", "medium", "high"\n'
    '  - "summary": a one-line description (string)\n'
    '  - "detail": a fuller explanation (string)\n'
    '  - "suggested_fix": a concrete fix (string), or null\n'
    'Reason step-by-step in "reasoning" FIRST, then list only the findings your '
    "reasoning supports. If there are no issues, return an empty findings array."
)

BUG_SYSTEM = (
    "You are a meticulous bug-finder reviewing a single code change (a unified "
    "diff hunk) together with surrounding repository context.\n"
    "Look only for correctness defects: logic errors, null/None handling, "
    "off-by-one errors, race conditions, resource leaks, and incorrect error "
    "handling.\n"
    "Bias strongly toward precision: only report an issue you are confident is a "
    "real defect. Do NOT invent issues, and do NOT report style or refactoring "
    'concerns. Set "kind" to "bug" for every finding.\n\n' + _CONTRACT
)

STYLE_SYSTEM = (
    "You are a code-style reviewer examining a single code change (a unified "
    "diff hunk) together with surrounding repository context.\n"
    "Look for naming problems, dead code, duplication, missing type annotations "
    "or docstrings, and inconsistency with the surrounding codebase. Use the "
    "provided repository context to judge consistency with existing "
    'conventions. Set "kind" to "style" for every finding.\n\n' + _CONTRACT
)

REFACTOR_SYSTEM = (
    "You are a refactoring advisor examining a single code change (a unified "
    "diff hunk) together with surrounding repository context.\n"
    "Suggest concrete simplifications, extractions, and clearer abstractions. "
    'Every finding MUST include a concrete "suggested_fix". Set "kind" to '
    '"refactor" for every finding.\n\n' + _CONTRACT
)


def build_llm(settings: Settings | None = None) -> ChatAnthropic:
    """Construct a ``ChatAnthropic`` client using the configured model."""
    settings = settings or Settings()
    return ChatAnthropic(
        model=settings.anthropic_model,
        api_key=settings.anthropic_api_key,
        max_tokens=8192,
    )


def _message_text(message: object) -> str:
    """Extract plain text from an LLM response (string or content-block list)."""
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content)


def _format_context(chunks: list[dict]) -> str:
    if not chunks:
        return "(no additional context retrieved)"
    parts = []
    for c in chunks:
        header = f"# {c.get('path')} (lines {c.get('start_line')}-{c.get('end_line')})"
        parts.append(f"{header}\n{c.get('text', '')}")
    return "\n\n".join(parts)


def _user_prompt(hunk: str, context: list[dict]) -> str:
    return (
        "## Changed hunk (unified diff)\n"
        f"```diff\n{hunk}\n```\n\n"
        "## Relevant repository context\n"
        f"{_format_context(context)}\n"
    )


def _messages(system: str, user: str) -> list:
    return [SystemMessage(content=system), HumanMessage(content=user)]


def _run_chain(
    system: str, hunk: str, context: list[dict], llm: ChatAnthropic
) -> ChainResult:
    """Invoke ``llm`` and parse a ``ChainResult``, repairing once if needed."""
    user = _user_prompt(hunk, context)
    raw = _message_text(llm.invoke(_messages(system, user)))
    try:
        return ChainResult.model_validate(loads_json(raw))
    except (json.JSONDecodeError, ValidationError):
        repair = (
            f"{user}\n\nYour previous output was not valid JSON. Return only the "
            "JSON object described above, with no prose or code fences.\n\n"
            f"Previous output:\n{raw}"
        )
        fixed = _message_text(llm.invoke(_messages(system, repair)))
        # A second failure is allowed to propagate.
        return ChainResult.model_validate(loads_json(fixed))


def bug_detection_chain(
    hunk: str,
    context: list[dict],
    llm: ChatAnthropic | None = None,
    settings: Settings | None = None,
) -> ChainResult:
    """Find correctness defects in the hunk (high precision)."""
    llm = llm or build_llm(settings)
    return _run_chain(BUG_SYSTEM, hunk, context, llm)


def style_chain(
    hunk: str,
    context: list[dict],
    llm: ChatAnthropic | None = None,
    settings: Settings | None = None,
) -> ChainResult:
    """Find style / consistency issues, judged against the codebase context."""
    llm = llm or build_llm(settings)
    return _run_chain(STYLE_SYSTEM, hunk, context, llm)


def refactor_chain(
    hunk: str,
    context: list[dict],
    llm: ChatAnthropic | None = None,
    settings: Settings | None = None,
) -> ChainResult:
    """Suggest concrete refactors, each with a suggested fix."""
    llm = llm or build_llm(settings)
    return _run_chain(REFACTOR_SYSTEM, hunk, context, llm)
