"""Ergane configuration — env vars + repo-local .ergane.toml."""
from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
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
    openai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("ERGANE_OPENAI_API_KEY", "OPENAI_API_KEY"),
        description="OpenAI API key",
    )
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias=AliasChoices("ERGANE_OPENAI_BASE_URL", "OPENAI_BASE_URL"),
    )
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] = Field(
        default="medium"
    )
    reasoning_mode: Literal["standard", "pro"] = Field(default="standard")
    openai_timeout_seconds: float = Field(default=45.0, gt=0.0, le=300.0)
    openai_max_retries: int = Field(default=2, ge=0, le=5)

    # Patent APIs
    uspto_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("ERGANE_USPTO_API_KEY", "USPTO_API_KEY"),
        description="USPTO API key (optional)",
    )
    epo_consumer_key: str = Field(
        default="", validation_alias=AliasChoices("ERGANE_EPO_CONSUMER_KEY", "EPO_CONSUMER_KEY")
    )
    epo_consumer_secret: str = Field(
        default="", validation_alias=AliasChoices("ERGANE_EPO_CONSUMER_SECRET", "EPO_CONSUMER_SECRET")
    )
    pqai_api_key: str = Field(
        default="", validation_alias=AliasChoices("ERGANE_PQAI_API_KEY", "PQAI_API_KEY")
    )

    # Notification
    github_token: str = Field(
        default="", validation_alias=AliasChoices("ERGANE_GITHUB_TOKEN", "GITHUB_TOKEN"), description="GitHub token for PR comments"
    )
    openclaw_webhook_url: str = Field(
        default="", validation_alias=AliasChoices("ERGANE_OPENCLAW_WEBHOOK_URL", "OPENCLAW_WEBHOOK_URL")
    )
    openclaw_hooks_token: str = Field(
        default="", validation_alias=AliasChoices("ERGANE_OPENCLAW_HOOKS_TOKEN", "OPENCLAW_HOOKS_TOKEN")
    )

    # Behavior
    novelty_threshold: float = Field(default=0.4, ge=0.0, le=1.0)
    max_prior_art: int = Field(default=20, ge=1, le=100)
    notification_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    allow_private_repos: bool = Field(default=False)
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

# A checked-in configuration file is part of a pull request and must never be
# able to redirect credential-bearing traffic or enable privileged behavior.
_REPO_CONFIG_ALLOWED_FIELDS = frozenset(
    {
        "model",
        "fast_model",
        "balanced_model",
        "reasoning_effort",
        "reasoning_mode",
        "openai_timeout_seconds",
        "openai_max_retries",
        "novelty_threshold",
        "max_prior_art",
        "notification_threshold",
        "dry_run",
        "verbose",
    }
)


def _read_repo_config(repo_path: Path) -> dict[str, object]:
    """Read an optional repo-local .ergane.toml file."""
    config_path = find_repo_config(repo_path)
    if not config_path:
        return {}
    with config_path.open("rb") as config_file:
        raw = tomllib.load(config_file)
    values = raw.get("ergane", raw)
    return values if isinstance(values, dict) else {}


def get_config(repo_path: Path | None = None) -> Config:
    """Load settings from environment and, when supplied, .ergane.toml.

    Environment and .env values win over repository configuration.  This lets a
    checked-in config define safe defaults without ever overriding CI secrets.
    """
    global _config
    if repo_path is None:
        if _config is None:
            _config = Config()
        return _config

    environment_config = Config()
    repo_values = _read_repo_config(repo_path)
    if not repo_values:
        return environment_config

    values = environment_config.model_dump()
    for name, value in repo_values.items():
        if name not in _REPO_CONFIG_ALLOWED_FIELDS:
            continue
        field = Config.model_fields.get(name)
        if field is None:
            continue
        aliases = [f"ERGANE_{name.upper()}"]
        alias = field.validation_alias
        if isinstance(alias, AliasChoices):
            aliases.extend(str(choice) for choice in alias.choices)
        if not any(os.environ.get(env_name) for env_name in aliases):
            values[name] = value
    return Config.model_validate(values)


def find_repo_config(repo_path: Path = Path(".")) -> Path | None:
    """Find .ergane.toml in repo root (walk up from cwd)."""
    path = repo_path.resolve()
    for parent in [path, *path.parents]:
        candidate = parent / ".ergane.toml"
        if candidate.exists():
            return candidate
    return None
