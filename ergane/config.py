"""Ergane configuration — env vars + repo-local .ergane.toml."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Settings loaded from environment and .env files."""

    model_config = SettingsConfigDict(
        env_prefix="ERGANE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenAI
    model: str = Field(default="gpt-5.6-sol", description="Default LLM for synthesis")
    fast_model: str = Field(default="gpt-5.6-luna", description="Model for fast tasks")
    balanced_model: str = Field(default="gpt-5.6-terra", description="Model for balanced tasks")
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_base_url: str = Field(default="https://api.openai.com/v1")
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] = Field(
        default="medium"
    )
    reasoning_mode: Literal["standard", "pro"] = Field(default="standard")

    # Patent APIs
    uspto_api_key: str = Field(default="", description="USPTO API key (optional)")
    epo_consumer_key: str = Field(default="", description="EPO OPS consumer key")
    epo_consumer_secret: str = Field(default="", description="EPO OPS consumer secret")
    pqai_api_key: str = Field(default="", description="PQAI token (optional)")

    # Notification
    github_token: str = Field(default="", description="GitHub token for PR comments")
    openclaw_webhook_url: str = Field(default="", description="OpenClaw webhook URL")
    openclaw_hooks_token: str = Field(default="", description="OpenClaw hooks token")

    # Behavior
    novelty_threshold: float = Field(default=0.4, ge=0.0, le=1.0)
    max_prior_art: int = Field(default=20, ge=1, le=100)
    dry_run: bool = Field(default=False, description="Skip LLM and API calls")
    verbose: bool = Field(default=False)

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_uspto(self) -> bool:
        return bool(self.uspto_api_key)

    @property
    def has_epo(self) -> bool:
        return bool(self.epo_consumer_key and self.epo_consumer_secret)

    @property
    def has_pqai(self) -> bool:
        return bool(self.pqai_api_key)


_config: Config | None = None


def get_config() -> Config:
    """Load and return Ergane configuration (cached)."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def find_repo_config(repo_path: Path = Path(".")) -> Path | None:
    """Find .ergane.toml in repo root (walk up from cwd)."""
    path = repo_path.resolve()
    for parent in [path, *path.parents]:
        candidate = parent / ".ergane.toml"
        if candidate.exists():
            return candidate
    return None
