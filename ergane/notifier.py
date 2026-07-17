"""Notification — GitHub PR comments + OpenClaw webhook."""
from __future__ import annotations

from typing import Any

import httpx


def format_pr_comment(result: dict, invention: Any) -> str:
    """Format detection results as markdown for GitHub PR comment."""
    ns = result.get("novelty_score", 0.0)
    assessment = result.get("novelty_assessment", "UNKNOWN")
    emoji = "🟢" if assessment == "HIGH" else "🟡" if assessment == "MEDIUM" else "🔴"

    lines = [
        f"## {emoji} Ergane Patent Detection — {invention.commit_hash}",
        "",
        f"**Novelty Score:** `{ns}` | **Assessment:** {assessment}",
    ]

    if getattr(invention, 'technical_problem', ''):
        lines.append(f"**Technical Problem:** {invention.technical_problem[:300]}")
    if getattr(invention, 'technical_solution', ''):
        lines.extend(["", f"**Technical Solution:**\n```\n{invention.technical_solution[:400]}\n```"])

    lines.extend(["", "**Closest Prior Art:**"])
    closest = result.get("closest_prior_art")
    if closest:
        lines.append(f"- {closest.get('patent_number', 'N/A')}: {closest.get('title', 'Untitled')} ({closest.get('source', 'unknown')})")
    else:
        lines.append("- None found")

    lines.extend([
        "",
        f"**Recommendation:** {result.get('recommendation', 'UNKNOWN')}",
        "",
        "*⚠️ Preliminary draft for attorney review only. Not legal advice.*",
    ])
    return "\n".join(lines)


def post_pr_comment(repo: str, pr_number: int, body: str, github_token: str) -> dict:
    """Post comment to GitHub PR."""
    if not github_token:
        return {"_error": "No GitHub token"}
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, headers=headers, json={"body": body})
            return resp.json()
    except Exception as e:
        return {"_error": str(e)}


def send_openclaw_webhook(payload: dict, webhook_url: str, hooks_token: str) -> dict:
    """POST notification to OpenClaw gateway."""
    if not webhook_url:
        return {"_error": "No webhook URL"}
    headers = {"Content-Type": "application/json"}
    if hooks_token:
        headers["X-Hooks-Token"] = hooks_token
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(webhook_url, headers=headers, json=payload)
            return {"status": resp.status_code, "body": resp.text[:200]}
    except Exception as e:
        return {"_error": str(e)}
