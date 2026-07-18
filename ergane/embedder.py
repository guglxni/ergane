"""Sentence-transformer embeddings for invention similarity."""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Mapping

import numpy as np


@lru_cache(maxsize=1)
def _load_model() -> Any:
    """Load the embedding model only when semantic search is requested."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise ImportError(
            "sentence-transformers is required for embeddings. "
            "Install it with: pip install sentence-transformers"
        ) from exc
    return SentenceTransformer("all-MiniLM-L6-v2")


def encode_text(text: str) -> np.ndarray:
    """Encode text as a normalized all-MiniLM-L6-v2 embedding."""
    embedding = _load_model().encode(text, normalize_embeddings=True)
    return np.asarray(embedding, dtype=np.float32)


def encode_invention(invention_dict: Mapping[str, object]) -> np.ndarray:
    """Encode an invention's problem, solution, and claim elements."""
    problem = invention_dict.get("problem", invention_dict.get("technical_problem", ""))
    solution = invention_dict.get("solution", invention_dict.get("technical_solution", ""))
    elements = invention_dict.get("claim_elements", invention_dict.get("key_claim_elements", []))
    claim_text = " ".join(str(element) for element in elements) if isinstance(elements, (list, tuple, set)) else str(elements or "")
    return encode_text("\n".join(str(part or "") for part in (problem, solution, claim_text)))


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Return cosine similarity, or zero when either vector is empty."""
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denominator) if denominator else 0.0
