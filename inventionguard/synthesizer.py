"""Synthesis: compare invention against prior art and draft claims."""

from __future__ import annotations

import json
import os
from typing import Any

import requests

from inventionguard.config import settings

SYNTHESIS_SYSTEM_PROMPT = """You are a patent claim analyst. Compare the following invention against the provided prior art patents.

Rules:
- Use proper patent claim language: "A method comprising...", "A system comprising..."
- The independent claim must include all essential elements of the invention.
- Dependent claims add optional but valuable limitations.
- Do not claim software per se; claim the method/system that implements the technical improvement.
- Include disclaimer: "This is a preliminary draft for attorney review only."
- Never claim an invention is legally patentable. Only provide technical analysis.
"""

SYNTHESIS_USER_TEMPLATE = """
Invention:
- Technical problem: {technical_problem}
- Technical solution: {technical_solution}
- Key claim elements: {key_claim_elements}

Prior Art (from Coral search results):
{prior_art_table}

Your task:
1. For each prior art patent, assess similarity to the invention (0-100%).
2. Identify which claim elements are covered by which prior art.
3. Determine if the invention is anticipated by a single reference or rendered obvious by combination.
4. Output structured JSON exactly as specified.
"""


def synthesize(
    detection: dict[str, Any],
    prior_art_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Synthesize invention against prior art and draft claims."""
    api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _heuristic_synthesis(detection, prior_art_results)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    prior_art_table = json.dumps(prior_art_results[:10], indent=2, default=str)
    user_content = SYNTHESIS_USER_TEMPLATE.format(
        technical_problem=detection.get("technical_problem", ""),
        technical_solution=detection.get("technical_solution", ""),
        key_claim_elements=", ".join(detection.get("key_claim_elements", [])),
        prior_art_table=prior_art_table,
    )

    payload = {
        "model": settings.model,
        "messages": [
            {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.2,
        "max_tokens": 2048,
        "response_format": {"type": "json_object"},
    }

    try:
        resp = requests.post(
            f"{settings.openai_base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        parsed.setdefault("overall_similarity_score", 50.0)
        parsed.setdefault("risk_assessment", "POSSIBLY_NOVEL")
        parsed.setdefault("draft_independent_claim", "1. A method comprising... [DRAFT PLACEHOLDER]")
        parsed.setdefault("recommendation", "PROCEED_WITH_FILING")
        return parsed
    except Exception as exc:
        return {
            "overall_similarity_score": 50.0,
            "closest_patent": {"patent_number": "N/A", "title": "N/A", "source": "N/A", "similarity_score": 0.0, "overlapping_claim_elements": []},
            "risk_assessment": "POSSIBLY_NOVEL",
            "analysis": f"Synthesis failed: {exc}. Fallback heuristic applied.",
            "draft_independent_claim": "1. A method comprising... [DRAFT PLACEHOLDER — attorney review required]\n\nDisclaimer: This is a preliminary draft for attorney review only.",
            "recommendation": "PROCEED_WITH_FILING",
        }


def _heuristic_synthesis(detection: dict[str, Any], prior_art_results: list[dict[str, Any]]) -> dict[str, Any]:
    avg_score = sum(p.get("score", 50) for p in prior_art_results) / max(len(prior_art_results), 1)
    return {
        "overall_similarity_score": round(avg_score, 1),
        "closest_patent": {
            "patent_number": prior_art_results[0].get("patent_number", "N/A") if prior_art_results else "N/A",
            "title": prior_art_results[0].get("title", "N/A") if prior_art_results else "N/A",
            "source": prior_art_results[0].get("source", "N/A") if prior_art_results else "N/A",
            "similarity_score": round(avg_score, 1),
            "overlapping_claim_elements": [],
        },
        "risk_assessment": "NOVEL" if avg_score < 30 else "POSSIBLY_NOVEL" if avg_score < 60 else "LIKELY_PRIOR_ART",
        "analysis": "Heuristic synthesis based on keyword overlap scores.",
        "draft_independent_claim": (
            f"1. A method for {detection.get('technical_problem', 'the disclosed problem')} comprising: "
            f"{', '.join(detection.get('key_claim_elements', ['the steps']))}.\n\n"
            "Disclaimer: This is a preliminary draft for attorney review only."
        ),
        "recommendation": "PROCEED_WITH_FILING",
    }
