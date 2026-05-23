"""Application settings, loaded from the environment / `.env`."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the agent.

    Values are read (case-insensitively) from environment variables, falling
    back to a local `.env` file, then to the defaults below.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Credentials
    anthropic_api_key: str = ""
    github_token: str = ""

    # Model / inference
    anthropic_model: str = "claude-sonnet-4-20250514"

    # Vector store + embeddings
    chroma_dir: str = "./chroma_db"
    embed_model: str = "all-MiniLM-L6-v2"
    top_k: int = 5
