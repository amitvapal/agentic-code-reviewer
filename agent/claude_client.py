"""A thin wrapper over the Anthropic SDK.

Exposes two helpers used throughout the agent:

* ``complete`` — a plain system/user completion that returns the response text.
* ``complete_json`` — the same, but tolerant of fenced or prose-wrapped JSON,
  with a single automatic repair retry when the model returns malformed JSON.
"""

from __future__ import annotations

import json

import anthropic

from agent.config import Settings
from agent.jsonparse import loads_json


def _text_from(response: object) -> str:
    """Concatenate the text blocks of a Messages API response."""
    parts = [
        block.text
        for block in getattr(response, "content", [])
        if getattr(block, "type", None) == "text"
    ]
    return "".join(parts).strip()


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
            return loads_json(text)
        except json.JSONDecodeError:
            repair_user = (
                f"{user}\n\nYour previous output was not valid JSON. "
                "Return only the JSON object, with no prose or code fences.\n\n"
                f"Previous output:\n{text}"
            )
            # One repair attempt; a second failure is allowed to raise.
            text = self.complete(sys_prompt, repair_user, max_tokens=max_tokens)
            return loads_json(text)
