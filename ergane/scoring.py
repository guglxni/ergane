"""Patent similarity scoring — novelty sigmoid, BM25, IPC Jaccard, ensemble."""
from __future__ import annotations

import math
from collections import Counter

import numpy as np


def novelty_sigmoid(raw_score: float, beta: float = 2.0, bias: float = 0.6) -> float:
    """Compress raw score into [0,1] with tunable steepness."""
    z = beta * (raw_score - bias)
    return 1.0 / (1.0 + math.exp(-z))


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity of two normalized vectors."""
    return float(np.dot(a, b))


def ipc_similarity(code_a: str, code_b: str) -> float:
    """Jaccard-like IPC hierarchical similarity."""
    if not code_a or not code_b:
        return 0.0
    parts_a = code_a.replace("/", "-").split("-")
    parts_b = code_b.replace("/", "-").split("-")
    common = sum(1 for pa, pb in zip(parts_a, parts_b, strict=False) if pa == pb)
    max_depth = max(len(parts_a), len(parts_b))
    return common / max_depth if max_depth > 0 else 0.0


def temporal_score(filing_year: int, current_year: int = 2026, half_life: float = 10.0) -> float:
    """Older patents = more dangerous to novelty."""
    age = max(0, current_year - filing_year)
    return math.exp(-age / half_life)


def ipc_entropy(ipc_codes: list[str]) -> float:
    """Higher entropy = more diverse prior art."""
    sections = [c[0] for c in ipc_codes if c]
    if not sections:
        return 0.0
    counts = Counter(sections)
    total = len(sections)
    return sum(-(c / total) * math.log2(c / total) for c in counts.values())


def ensemble_novelty(
    invention: object,
    prior_art: list[dict],
    semantic_weight: float = 0.35,
    bm25_weight: float = 0.20,
    ipc_weight: float = 0.15,
    temporal_weight: float = 0.10,
    graph_weight: float = 0.20,
) -> dict:
    """Combine multiple signals into final novelty assessment."""
    if not prior_art:
        return {
            "novelty_score": 1.0,
            "novelty_assessment": "HIGH",
            "closest_prior_art": None,
            "closest_similarity": 0.0,
            "ipc_entropy": 0.0,
        }

    inv_text = f"{getattr(invention, 'technical_problem', '')} {getattr(invention, 'technical_solution', '')}".lower().split()
    art_scores: list[dict] = []

    for patent in prior_art:
        art_text = (patent.get("abstract", "") + " " + patent.get("title", "")).lower().split()
        overlap = len(set(inv_text) & set(art_text))
        sim_tfidf = overlap / max(len(set(inv_text)), 1)

        sim_ipc = ipc_similarity(
            (getattr(invention, 'key_claim_elements', ['']) or [''])[0],
            patent.get("ipc", ""),
        )
        sim_temporal = temporal_score(patent.get("filing_year", 2026))
        raw_semantic = sim_tfidf * 0.8 + sim_temporal * 0.2

        combined = (
            semantic_weight * raw_semantic +
            bm25_weight * sim_tfidf +
            ipc_weight * sim_ipc +
            temporal_weight * sim_temporal
        )
        art_scores.append({"patent": patent, "score": combined})

    art_scores.sort(key=lambda x: x["score"], reverse=True)
    closest = art_scores[0]
    raw_novelty = 1.0 - closest["score"]
    novelty = novelty_sigmoid(raw_novelty, beta=2.0, bias=0.6)

    assessment = "LOW"
    if novelty >= 0.7:
        assessment = "HIGH"
    elif novelty >= 0.4:
        assessment = "MEDIUM"

    return {
        "novelty_score": round(novelty, 4),
        "novelty_assessment": assessment,
        "closest_prior_art": closest["patent"],
        "closest_similarity": round(closest["score"], 4),
        "all_scores": art_scores[:10],
        "ipc_entropy": round(ipc_entropy([p.get("ipc", "") for p in prior_art]), 4),
    }
