"""LLM synthesis — novelty assessment, claim drafting, risk analysis."""
from __future__ import annotations

import json
from typing import Any

from openai import OpenAI


def synthesize(
    invention: Any,
    prior_art: list[dict],
    api_key: str,
    model: str = "gpt-5.6-sol",
    reasoning_effort: str = "high",
    reasoning_mode: str = "standard",
    dry_run: bool = False,
) -> dict:
    """Call OpenAI API to synthesize invention against prior art."""
    if dry_run or not api_key:
        return {
            "overall_similarity_score": 23.0,
            "closest_patent": {"patent_number": "US10,123,456", "title": "Mock Patent", "source": "USPTO", "similarity_score": 0.23},
            "risk_assessment": "NOVEL",
            "draft_independent_claim": "1. A method comprising: receiving... [DRY RUN]",
            "recommendation": "PROCEED_WITH_FILING",
            "novelty_score": 0.87,
        }

    client = OpenAI(api_key=api_key)

    system_prompt = """You are a patent claim analyst. Compare inventions against prior art.
Rules:
- Use proper claim language: "A method comprising..."
- NEVER claim software per se (Alice Corp §101)
- Include disclaimer: "Preliminary draft for attorney review only."
- AI cannot be co-inventor (USPTO Nov 2025)
- Output strict JSON only."""

    user_prompt = f"""INVENTION:
- Technical problem: {getattr(invention, 'technical_problem', '')[:500]}
- Technical solution: {getattr(invention, 'technical_solution', '')[:800]}
- Key claim elements: {', '.join(getattr(invention, 'key_claim_elements', [])[:10])}

PRIOR ART ({len(prior_art)} results):
{json.dumps(prior_art[:10], indent=2)[:4000]}

Output JSON:
{{
  "overall_similarity_score": float (0-100),
  "closest_patent": {{"patent_number": "", "title": "", "source": "", "similarity_score": float}},
  "risk_assessment": "NOVEL | POSSIBLY_NOVEL | LIKELY_PRIOR_ART",
  "draft_independent_claim": "string in USPTO format (Claim 1)",
  "recommendation": "PROCEED_WITH_FILING | REFINE_INVENTION | ABANDON",
  "novelty_score": float (0-1)
}}"""

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = resp.choices[0].message.content or "{}"
        result = json.loads(content)
        result.setdefault("novelty_score", result.get("overall_similarity_score", 50) / 100)
        return result
    except Exception as e:
        return {
            "overall_similarity_score": 0.0,
            "closest_patent": None,
            "risk_assessment": f"ERROR: {e}",
            "draft_independent_claim": "Error parsing LLM response",
            "recommendation": "ABANDON",
            "novelty_score": 0.0,
        }
