"""A thin wrapper over the Anthropic SDK.

Exposes two helpers used throughout the agent:

* ``complete`` — a plain system/user completion that returns the response text.
* ``complete_json`` — the same, but tolerant of fenced or prose-wrapped JSON,
  with a single automatic repair retry when the model returns malformed JSON.
"""

from __future__ import annotations

import json
import re

import anthropic

from agent.config import Settings

# Matches a ```json ... ``` (or bare ``` ... ```) fenced block.
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def _text_from(response: object) -> str:
    """Concatenate the text blocks of a Messages API response."""
    parts = [
        block.text
        for block in getattr(response, "content", [])
        if getattr(block, "type", None) == "text"
    ]
    return "".join(parts).strip()


def _extract_json_span(text: str) -> str | None:
    """Return the first balanced ``{...}`` / ``[...]`` span in ``text``.

    Scans for the first opening brace/bracket and walks to its matching close,
    respecting string literals and escapes so braces inside strings don't throw
    off the depth count. Returns ``None`` if no balanced span is found.
    """
    start = next((i for i, ch in enumerate(text) if ch in "{["), None)
    if start is None:
        return None

    open_ch = text[start]
    close_ch = "}" if open_ch == "{" else "]"
    depth = 0
    in_str = False
    escaped = False

    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _loads(text: str) -> object:
    """Parse JSON that may be fenced, raw, or preceded by prose.

    Raises ``json.JSONDecodeError`` if nothing parseable is found.
    """
    candidate = text.strip()
    fence = _FENCE_RE.search(candidate)
    if fence:
        candidate = fence.group(1).strip()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        span = _extract_json_span(candidate)
        if span is None:
            raise
        return json.loads(span)


class ClaudeClient:
    """Minimal Anthropic Messages API wrapper."""

    def __init__(
        self,
        settings: Settings | None = None,
        client: anthropic.Anthropic | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.client = client or anthropic.Anthropic(
            api_key=self.settings.anthropic_api_key
        )
        self.model = self.settings.anthropic_model

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> str:
        """Run a single system/user completion and return its text."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            # Cache the (stable) system prompt so repeated calls reuse the prefix.
            system=[
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user}],
        )
        return _text_from(response)

    def complete_json(
        self,
        system: str,
        user: str,
        schema_hint: str | None = None,
        max_tokens: int = 4096,
    ) -> object:
        """Like :meth:`complete`, but parse the result as JSON.

        Accepts fenced (```json ... ```), raw, or prose-prefixed JSON. On a
        parse failure, sends one repair message asking for JSON only and tries
        again before letting the error propagate.
        """
        sys_prompt = system
        if schema_hint:
            sys_prompt = (
                f"{system}\n\nReturn ONLY a JSON object matching this schema:\n"
                f"{schema_hint}"
            )

        text = self.complete(sys_prompt, user, max_tokens=max_tokens)
        try:
            return _loads(text)
        except json.JSONDecodeError:
            repair_user = (
                f"{user}\n\nYour previous output was not valid JSON. "
                "Return only the JSON object, with no prose or code fences.\n\n"
                f"Previous output:\n{text}"
            )
            # One repair attempt; a second failure is allowed to raise.
            text = self.complete(sys_prompt, repair_user, max_tokens=max_tokens)
            return _loads(text)
