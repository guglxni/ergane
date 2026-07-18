"""LLM synthesis — schema-validated novelty assessment and claim drafting."""
from __future__ import annotations

import json
from typing import Any, Literal, cast

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field


class ClosestPatent(BaseModel):
    """A schema-validated summary of one prior-art reference."""

    model_config = ConfigDict(extra="forbid")

    patent_number: str = ""
    title: str = ""
    source: str = ""
    similarity_score: float = Field(ge=0.0, le=100.0)
    overlapping_claim_elements: list[str] = Field(default_factory=list)


class SynthesisResult(BaseModel):
    """The only model output shape accepted by Ergane's production pipeline."""

    model_config = ConfigDict(extra="forbid")

    overall_similarity_score: float = Field(ge=0.0, le=100.0)
    closest_patent: ClosestPatent
    risk_assessment: Literal["NOVEL", "POSSIBLY_NOVEL", "LIKELY_PRIOR_ART"]
    analysis: str
    draft_independent_claim: str
    recommendation: Literal["PROCEED_WITH_FILING", "REFINE_INVENTION", "ABANDON"]
    novelty_score: float = Field(ge=0.0, le=1.0)
    disclaimer: str


def synthesize(
    invention: Any,
    prior_art: list[dict],
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-5.6-sol",
    reasoning_effort: str = "high",
    reasoning_mode: str = "standard",
    dry_run: bool = False,
    timeout_seconds: float = 45.0,
    max_retries: int = 2,
) -> dict:
    """Compare an invention with prior art through the Responses API.

    `reasoning_mode` remains in the signature for configuration compatibility.
    It is intentionally not sent because it is a Codex-harness concern, not a
    documented Responses API parameter.
    """
    if dry_run or not api_key:
        return SynthesisResult(
            overall_similarity_score=23.0,
            closest_patent=ClosestPatent(
                patent_number="US10,123,456",
                title="Mock Patent",
                source="USPTO",
                similarity_score=23.0,
            ),
            risk_assessment="NOVEL",
            analysis="Dry-run placeholder; no external model call was made.",
            draft_independent_claim="1. A method comprising: receiving... [DRY RUN]",
            recommendation="PROCEED_WITH_FILING",
            novelty_score=0.87,
            disclaimer="Preliminary draft for attorney review only.",
        ).model_dump()

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout_seconds,
        max_retries=max_retries,
    )
    system_prompt = """You are a patent claim analyst. Compare inventions against prior art.
Rules:
- Use proper claim language: "A method comprising..."
- NEVER claim software per se (Alice Corp §101)
- Include the disclaimer "Preliminary draft for attorney review only."
- AI cannot be an inventor.
- Do not give legal advice; produce technical analysis for human attorney review."""
    user_prompt = f"""INVENTION:
- Technical problem: {getattr(invention, 'technical_problem', '')[:500]}
- Technical solution: {getattr(invention, 'technical_solution', '')[:800]}
- Key claim elements: {', '.join(getattr(invention, 'key_claim_elements', [])[:10])}

PRIOR ART ({len(prior_art)} results):
{json.dumps(prior_art[:10], indent=2)[:4000]}

Return a complete comparison, an independent claim draft, and a preliminary-review disclaimer."""

    try:
        # Responses is the recommended API for new projects. Structured Outputs
        # reject malformed or incomplete model output before it reaches a PR or
        # a notification, and store=False keeps this legal-adjacent request out
        # of retained response state.
        response = client.responses.parse(
            model=model,
            instructions=system_prompt,
            input=user_prompt,
            text_format=SynthesisResult,
            reasoning=cast(Any, {"effort": reasoning_effort}),
            store=False,
        )
        result = response.output_parsed
        if result is None:
            raise ValueError("Model returned no parseable synthesis output")
        return result.model_dump()
    except Exception:
        return {
            "overall_similarity_score": 0.0,
            "closest_patent": None,
            "risk_assessment": "ERROR",
            "draft_independent_claim": "Synthesis unavailable; no claim was generated.",
            "recommendation": "ABANDON",
            "novelty_score": 0.0,
            "disclaimer": "Synthesis failed; attorney review is required.",
            "_error": "OpenAI synthesis request failed",
        }
