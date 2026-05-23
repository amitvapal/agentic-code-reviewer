"""ClaudeClient.complete_json strips fences, extracts JSON, and repairs once."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from agent.claude_client import ClaudeClient
from agent.config import Settings


def _resp(text: str) -> SimpleNamespace:
    """Build a fake Messages API response with a single text block."""
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


def _client(mock_messages_client: MagicMock) -> ClaudeClient:
    return ClaudeClient(
        settings=Settings(_env_file=None, anthropic_api_key="x"),
        client=mock_messages_client,
    )


def test_strips_json_fences():
    mock = MagicMock()
    mock.messages.create.return_value = _resp('```json\n{"ok": true}\n```')

    result = _client(mock).complete_json("sys", "user")

    assert result == {"ok": True}
    assert mock.messages.create.call_count == 1


def test_extracts_json_from_leading_prose():
    mock = MagicMock()
    mock.messages.create.return_value = _resp(
        'Sure, here you go:\n{"verdict": "approve"}'
    )

    result = _client(mock).complete_json("sys", "user")

    assert result == {"verdict": "approve"}
    assert mock.messages.create.call_count == 1


def test_repairs_malformed_json_once():
    mock = MagicMock()
    mock.messages.create.side_effect = [
        _resp("I cannot produce JSON, sorry."),  # unparseable -> triggers repair
        _resp('{"ok": true}'),  # repaired
    ]

    result = _client(mock).complete_json("sys", "user")

    assert result == {"ok": True}
    assert mock.messages.create.call_count == 2
