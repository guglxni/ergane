"""Invention detection via LLM."""

from __future__ import annotations

import json
import os
from typing import Any

import requests

from inventionguard.config import settings

DETECTION_SYSTEM_PROMPT = """You are a patent technical examiner. Analyze the following code diff and its architectural context (provided as a knowledge graph subgraph) to identify any technical improvements to computer functionality.

Rules:
- Software/code itself is NOT patentable. Only the underlying technical improvement to computer functionality is patentable (USPTO Section 101/Alice).
- HIGH novelty: novel algorithm, architectural improvement, or technical optimization with no obvious prior art.
- MEDIUM novelty: improvement on known technique but with non-obvious twist.
- LOW novelty: routine implementation, standard library usage, UI change, business logic.
- Never output legal advice. Only technical analysis.
- If novelty_score < 0.4, set "skip": true and do not proceed to claim drafting.
"""

DETECTION_USER_TEMPLATE = """
Code diff:
{diff}

Commit message:
{commit_message}

Graphify subgraph:
{subgraph}

Files changed:
{files_changed}

Your task:
1. Identify the technical problem being solved.
2. Identify the technical solution implemented.
3. Assess whether this solution represents a novel improvement to computer functionality (not merely an abstract idea, business method, or routine implementation).
4. Output a structured JSON object exactly as specified.
"""


def detect_invention(
    diff: str,
    commit_message: str,
    subgraph: dict[str, Any],
    files_changed: list[str],
) -> dict[str, Any]:
    """Send diff + subgraph to LLM for invention detection."""
    api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Fallback: rule-based heuristic
        return _heuristic_detection(diff, commit_message)

    client = requests.Session()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    user_content = DETECTION_USER_TEMPLATE.format(
        diff=diff[:8000],
        commit_message=commit_message,
        subgraph=json.dumps(subgraph, indent=2)[:4000],
        files_changed=", ".join(files_changed),
    )

    payload = {
        "model": settings.model,
        "messages": [
            {"role": "system", "content": DETECTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.2,
        "max_tokens": 2048,
        "response_format": {"type": "json_object"},
    }

    try:
        resp = client.post(
            f"{settings.openai_base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return parsed
    except Exception as exc:  # pragma: no cover
        # Graceful degradation
        return {
            "technical_problem": f"Error during detection: {exc}",
            "technical_solution": "N/A",
            "novelty_score": 0.0,
            "novelty_assessment": "LOW",
            "key_claim_elements": [],
            "rationale": "LLM call failed; falling back.",
            "ipc_suggestion": "",
            "skip": True,
        }


def _heuristic_detection(diff: str, commit_message: str) -> dict[str, Any]:
    """Quick heuristic when LLM is unavailable."""
    novelty_indicators = [
        "algorithm", "protocol", "consensus", "replication", "synchronization",
        "vector clock", "distributed", "cache invalidation", "conflict resolution",
        "compression", "encryption", "scheduler", "optimiz", "heuristic",
    ]
    score = sum(1 for ind in novelty_indicators if ind.lower() in (diff + commit_message).lower()) / len(novelty_indicators)
    return {
        "technical_problem": commit_message,
        "technical_solution": "See diff",
        "novelty_score": round(min(score * 3, 0.95), 2),
        "novelty_assessment": "HIGH" if score > 0.5 else "MEDIUM" if score > 0.2 else "LOW",
        "key_claim_elements": ["method", "system"],
        "rationale": "Heuristic assessment based on keyword matches.",
        "ipc_suggestion": "G06F",
        "skip": score < 0.15,
    }
