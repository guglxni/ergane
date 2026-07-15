"""Prior art search via Coral SQL and direct PQAI API."""

from __future__ import annotations

import subprocess
from typing import Any

import requests



def build_coral_sql(query_text: str, top_k: int = 10) -> str:
    """Generate the multi-source Coral SQL query."""
    return f"""
WITH uspto_results AS (
    SELECT patent_number, title, abstract, assignee, 0.8 AS source_weight
    FROM uspto.patents
    WHERE q = '{query_text}'
    LIMIT {top_k}
),
epo_results AS (
    SELECT doc_number AS patent_number, title, abstract, applicant AS assignee, 0.8 AS source_weight
    FROM epo.patents
    WHERE q = '{query_text}'
    LIMIT {top_k}
),
local_results AS (
    SELECT patent_number, title, abstract, assignee, 0.6 AS source_weight
    FROM local_patents.grants
    WHERE abstract LIKE '%{query_text.split()[0]}%'
    LIMIT {top_k}
)
SELECT * FROM uspto_results
UNION ALL SELECT * FROM epo_results
UNION ALL SELECT * FROM local_results
ORDER BY source_weight DESC
LIMIT {top_k * 3};
"""


def search_prior_art(
    technical_problem: str,
    technical_solution: str,
    key_claim_elements: list[str],
) -> list[dict[str, Any]]:
    """Search USPTO, EPO, local patents via Coral; PQAI via direct API."""
    results: list[dict[str, Any]] = []

    query_text = f"{technical_problem} {technical_solution}"
    # Clean query for SQL
    query_text_sql = query_text.replace("'", "''")[:200]

    # Coral multi-source search
    sql = build_coral_sql(query_text_sql)
    try:
        coral_output = subprocess.run(
            ["coral", "sql", sql],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if coral_output.returncode == 0 and coral_output.stdout.strip():
            # Simple parsing of Coral tabular output
            # In production, use coral sql --format json when available
            lines = coral_output.stdout.strip().splitlines()
            for line in lines[2:]:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 3:
                    results.append({
                        "patent_number": parts[0] if len(parts) > 0 else "N/A",
                        "title": parts[1] if len(parts) > 1 else "N/A",
                        "abstract": parts[2] if len(parts) > 2 else "N/A",
                        "assignee": parts[3] if len(parts) > 3 else "N/A",
                        "source": "CORAL",
                    })
    except Exception as exc:
        results.append({"error": f"Coral search failed: {exc}", "source": "CORAL"})

    # PQAI semantic search (direct API — Coral DSL v3 does not support table_functions)
    try:
        pqai_resp = requests.post(
            "https://search.projectpq.ai/api/search",
            json={"query": query_text, "top_n": 10},
            timeout=60,
        )
        pqai_data = pqai_resp.json()
        for item in pqai_data.get("results", []):
            results.append({
                "patent_number": item.get("publication_number", item.get("id", "N/A")),
                "title": item.get("title", "N/A"),
                "abstract": item.get("abstract", "N/A"),
                "score": item.get("score", 0.0),
                "source": "PQAI",
            })
    except Exception as exc:
        results.append({"error": f"PQAI search failed: {exc}", "source": "PQAI"})

    return results
