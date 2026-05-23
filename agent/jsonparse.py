"""Lenient JSON parsing shared by the Claude client and the review chains.

Handles model output that is fenced (```json ... ```), raw, or preceded by
prose, by extracting the first balanced JSON value. This is the parsing half of
the ``complete_json`` repair pattern.
"""

from __future__ import annotations

import json
import re

# Matches a ```json ... ``` (or bare ``` ... ```) fenced block.
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


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


def loads_json(text: str) -> object:
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
