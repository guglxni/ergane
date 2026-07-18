"""Notification — GitHub PR comments + OpenClaw webhook."""
from __future__ import annotations

from typing import Any

import httpx


def _request_error(error: Exception) -> dict:
    """Avoid persisting URLs, tokens, or service response bodies in state/audit logs."""
    if isinstance(error, httpx.HTTPStatusError):
        return {"_error": f"HTTP {error.response.status_code}"}
    return {"_error": f"{type(error).__name__}: request failed"}


def comment_marker(commit_hash: str) -> str:
    """Return a stable hidden marker used to update rather than duplicate comments."""
    return f"<!-- ergane:commit:{commit_hash} -->"


def format_pr_comment(result: dict, invention: Any) -> str:
    """Format detection results as markdown for GitHub PR comment."""
    ns = result.get("novelty_score", 0.0)
    assessment = result.get("novelty_assessment", "UNKNOWN")
    emoji = "🟢" if assessment == "HIGH" else "🟡" if assessment == "MEDIUM" else "🔴"

    lines = [
        f"## {emoji} Ergane Patent Detection — {invention.commit_hash}",
        "",
        f"**Novelty Score:** `{ns}` | **Assessment:** {assessment}",
        f"**Risk Assessment:** {result.get('risk_assessment', 'PENDING_PRIOR_ART_REVIEW')}",
    ]

    if getattr(invention, 'technical_problem', ''):
        lines.append(f"**Technical Problem:** {invention.technical_problem[:300]}")
    if getattr(invention, 'technical_solution', ''):
        lines.extend(["", f"**Technical Solution:**\n```\n{invention.technical_solution[:400]}\n```"])

    elements = getattr(invention, "key_claim_elements", [])
    if elements:
        lines.extend(["", "**Key Claim Elements:**", *(f"- {element}" for element in elements[:10])])

    lines.extend(["", "**Closest Prior Art:**"])
    closest = result.get("closest_prior_art") or result.get("closest_patent")
    if closest:
        lines.append(f"- {closest.get('patent_number', 'N/A')}: {closest.get('title', 'Untitled')} ({closest.get('source', 'unknown')})")
    else:
        lines.append("- None found")

    if result.get("overall_similarity_score") is not None:
        lines.append(f"**Similarity:** {result['overall_similarity_score']}%")

    claim = result.get("draft_independent_claim", "")
    if claim:
        lines.extend(["", "**Draft Independent Claim:**", "```", claim[:1200], "```"])

    lines.extend([
        "",
        f"**Recommendation:** {result.get('recommendation', 'UNKNOWN')}",
        "",
        "*⚠️ Preliminary draft for attorney review only. Not legal advice.*",
        comment_marker(invention.commit_hash),
    ])
    return "\n".join(lines)


def build_openclaw_payload(result: dict, invention: Any, repo_slug: str = "", pr_number: int = 0) -> dict:
    """Build the documented OpenClaw agent-hook payload without leaking secrets."""
    closest = result.get("closest_prior_art") or result.get("closest_patent") or {}
    pr_url = f"https://github.com/{repo_slug}/pull/{pr_number}" if repo_slug and pr_number else ""
    commit_url = f"https://github.com/{repo_slug}/commit/{invention.commit_hash}" if repo_slug else ""
    return {
        "invention_title": invention.commit_message[:120],
        "novelty_score": result.get("novelty_score", 0.0),
        "risk_assessment": result.get("risk_assessment", "UNKNOWN"),
        "commit_hash_short": invention.commit_hash,
        "commit_url": commit_url,
        "technical_problem": getattr(invention, "technical_problem", ""),
        "technical_solution": getattr(invention, "technical_solution", ""),
        "key_claim_elements": getattr(invention, "key_claim_elements", []),
        "closest_patent_title": closest.get("title", ""),
        "closest_patent_number": closest.get("patent_number", ""),
        "overall_similarity_score": result.get("overall_similarity_score", 0.0),
        "github_pr_url": pr_url,
    }


def find_existing_ergane_comment(comments: list[dict], body: str) -> dict | None:
    """Find the earlier comment carrying the same Ergane commit marker."""
    marker = next((line for line in body.splitlines() if line.startswith("<!-- ergane:commit:")), "")
    return next((comment for comment in comments if marker and marker in str(comment.get("body", ""))), None)


def upsert_pr_comment(repo: str, pr_number: int, body: str, github_token: str) -> dict:
    """Create or replace Ergane's per-commit PR comment idempotently."""
    if not github_token:
        return {"_error": "No GitHub token"}
    base_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {"Authorization": f"Bearer {github_token}", "Accept": "application/vnd.github+json"}
    try:
        with httpx.Client(timeout=30.0) as client:
            comments_response = client.get(base_url, headers=headers, params={"per_page": 100})
            comments_response.raise_for_status()
            existing = find_existing_ergane_comment(comments_response.json(), body)
            if existing:
                response = client.patch(
                    f"https://api.github.com/repos/{repo}/issues/comments/{existing['id']}",
                    headers=headers,
                    json={"body": body},
                )
            else:
                response = client.post(base_url, headers=headers, json={"body": body})
            response.raise_for_status()
            return response.json()
    except Exception as exc:
        return _request_error(exc)


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
            resp.raise_for_status()
            return {"status": resp.status_code}
    except Exception as exc:
        return _request_error(exc)
