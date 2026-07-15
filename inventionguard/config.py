"""InventionGuard configuration and settings."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # LLM
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"
    novelty_threshold: float = 0.4

    # Coral
    coral_sources: list[str] | None = None

    # PQAI
    pqai_api_key: str | None = None

    # OpenClaw
    openclaw_webhook_url: str | None = None

    # GBrain
    gbrain_mcp_url: str | None = None

    # GitHub
    github_token: str | None = None
    github_repo: str | None = None

    # Legal
    disclaimer: str = (
        "This tool identifies potential technical inventions. "
        "It does not provide legal advice. Consult a patent attorney."
    )

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=os.getenv("INVENTIONGUARD_MODEL", "gpt-4o"),
            novelty_threshold=float(os.getenv("INVENTIONGUARD_NOVELTY_THRESHOLD", "0.4")),
            coral_sources=(os.getenv("CORAL_SOURCES", "uspto,epo,local_patents")).split(","),
            pqai_api_key=os.getenv("PQAI_API_KEY"),
            openclaw_webhook_url=os.getenv("OPENCLAW_WEBHOOK_URL"),
            gbrain_mcp_url=os.getenv("GBRAIN_MCP_URL"),
            github_token=os.getenv("GITHUB_TOKEN"),
            github_repo=os.getenv("GITHUB_REPOSITORY"),
        )


settings = Settings.from_env()
