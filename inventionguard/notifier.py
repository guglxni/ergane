"""Notification: OpenClaw webhook + GBrain memory storage."""

from __future__ import annotations

import os
import subprocess
from typing import Any

import requests

from inventionguard.config import settings


def notify(result: dict[str, Any], repo_path: str) -> None:
    """Send OpenClaw webhook notification."""
    webhook_url = settings.openclaw_webhook_url or os.getenv("OPENCLAW_WEBHOOK_URL")
    if not webhook_url:
        return

    detection = result["detection"]
    synthesis = result["synthesis"]
    commit_hash = result["commit_hash"]

    payload = {
        "invention_title": detection.get("technical_problem", "Untitled Invention")[:80],
        "novelty_score": detection.get("novelty_score", 0.0),
        "risk_assessment": synthesis.get("risk_assessment", "UNKNOWN"),
        "inventor": _get_commit_author(repo_path, commit_hash),
        "commit_hash_short": commit_hash[:7],
        "commit_url": f"https://github.com/{settings.github_repo}/commit/{commit_hash}" if settings.github_repo else "",
        "technical_problem": detection.get("technical_problem", ""),
        "closest_patent_title": synthesis.get("closest_patent", {}).get("title", "N/A"),
        "closest_patent_number": synthesis.get("closest_patent", {}).get("patent_number", "N/A"),
        "overall_similarity_score": synthesis.get("overall_similarity_score", 0.0),
        "github_pr_url": f"https://github.com/{settings.github_repo}/pulls" if settings.github_repo else "",
        "dismiss_url": "https://inventionguard.local/dismiss/0",
    }

    try:
        requests.post(webhook_url, json=payload, timeout=30)
    except Exception:
        pass


def store_in_gbrain(result: dict[str, Any]) -> None:
    """Store invention note in GBrain via MCP or CLI if available."""
    gbrain_url = settings.gbrain_mcp_url or os.getenv("GBRAIN_MCP_URL")
    detection = result["detection"]
    synthesis = result["synthesis"]
    commit_hash = result["commit_hash"]

    title = f"Invention: {detection.get('technical_problem', 'Unknown')[:60]}"
    content = f"""## Technical Problem
{detection.get('technical_problem', 'N/A')}

## Technical Solution
{detection.get('technical_solution', 'N/A')}

## Novelty Score
{detection.get('novelty_score', 0)} ({detection.get('novelty_assessment', 'N/A')})

## Draft Claim
{synthesis.get('draft_independent_claim', 'N/A')}

## Related Code
- {', '.join(result.get('files_changed', []))}

## Commit
{commit_hash}
"""

    if gbrain_url:
        try:
            requests.post(
                f"{gbrain_url.rstrip('/')}/notes",
                json={"title": title, "content": content, "tags": ["invention"]},
                timeout=30,
            )
        except Exception:
            pass
    else:
        # Attempt CLI fallback
        try:
            subprocess.run(
                ["gbrain", "create-note", "--title", title, "--content", content],
                capture_output=True,
                timeout=30,
                check=False,
            )
        except Exception:
            pass


def _get_commit_author(repo_path: str, commit_hash: str) -> str:
    """Get commit author email."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "show", "-s", "--format=%ae", commit_hash],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.stdout.strip() or "unknown@developer"
    except Exception:
        return "unknown@developer"
