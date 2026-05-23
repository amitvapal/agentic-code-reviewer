"""Settings loads credentials and config from the environment."""

from agent.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-test-model")
    monkeypatch.setenv("CHROMA_DIR", "/tmp/chroma")
    monkeypatch.setenv("EMBED_MODEL", "test-embed")
    monkeypatch.setenv("TOP_K", "7")

    settings = Settings(_env_file=None)

    assert settings.anthropic_api_key == "test-key"
    assert settings.github_token == "test-token"
    assert settings.anthropic_model == "claude-test-model"
    assert settings.chroma_dir == "/tmp/chroma"
    assert settings.embed_model == "test-embed"
    assert settings.top_k == 7


def test_settings_defaults(monkeypatch):
    for var in ("ANTHROPIC_MODEL", "CHROMA_DIR", "EMBED_MODEL", "TOP_K"):
        monkeypatch.delenv(var, raising=False)

    settings = Settings(_env_file=None)

    assert settings.anthropic_model == "claude-sonnet-4-20250514"
    assert settings.embed_model == "all-MiniLM-L6-v2"
    assert settings.top_k == 5
