"""Patent database search wrappers — USPTO, EPO, PQAI."""
from __future__ import annotations

from typing import Any

import httpx


def _safe_json(resp: httpx.Response) -> dict:
    try:
        return resp.json()
    except Exception:
        return {"_error": resp.text[:500]}


def search_uspto(query: str, api_key: str = "", limit: int = 10) -> list[dict]:
    """Search USPTO patent applications. Free, no key required."""
    url = "https://api.uspto.gov/api/v1/patent/applications/search"
    payload = {"q": query, "limit": limit, "offset": 0}
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-KEY"] = api_key

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, json=payload, headers=headers)
            data = _safe_json(resp)
            results = data.get("patentFileWrapperDataBag", data.get("results", []))
            out = []
            for r in results:
                out.append({
                    "source": "USPTO",
                    "patent_number": r.get("applicationNumberText", r.get("patentNumber", "N/A")),
                    "title": r.get("inventionTitle", "Untitled"),
                    "abstract": r.get("abstractText", "")[:500],
                    "assignee": r.get("firstApplicantName", ""),
                    "filing_year": _extract_year(r.get("filingDate")),
                    "ipc": _join_ipc(r.get("ipcCodes")),
                })
            return out
    except Exception as e:
        return [{"source": "USPTO", "_error": str(e)}]


def _extract_year(date_str: Any) -> int:
    try:
        return int(str(date_str)[:4]) if date_str else 2026
    except (ValueError, TypeError):
        return 2026


def _join_ipc(codes: Any) -> str:
    if isinstance(codes, list):
        return ",".join(codes)
    return str(codes) if codes else ""


def search_epo(query: str, consumer_key: str = "", consumer_secret: str = "", limit: int = 10) -> list[dict]:
    """Search EPO OPS. Requires OAuth2. Falls back if no credentials."""
    if not consumer_key or not consumer_secret:
        return [{"source": "EPO", "_error": "No EPO credentials"}]

    try:
        with httpx.Client(timeout=30) as client:
            token_resp = client.post(
                "https://ops.epo.org/3.2/auth/accesstoken",
                auth=(consumer_key, consumer_secret),
                data={"grant_type": "client_credentials"},
            )
            token_data = _safe_json(token_resp)
            token = token_data.get("access_token", "")
            if not token:
                return [{"source": "EPO", "_error": "OAuth failed"}]

            search_resp = client.get(
                "https://ops.epo.org/3.2/rest-services/published-data/search",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                params={"q": query, "Range": f"1-{limit}"},
            )
            data = _safe_json(search_resp)
            refs = (
        data.get("ops:world-patent-data", {})
        .get("ops:biblio-search", {})
        .get("ops:search-result", {})
        .get("ops:publication-reference", [])
    )
            if not isinstance(refs, list):
                refs = [refs] if refs else []

            return [{
                "source": "EPO",
                "patent_number": r.get("document-id", {}).get("doc-number", "N/A"),
                "title": "EPO Result",
                "abstract": "",
                "assignee": "",
                "filing_year": 2026,
                "ipc": "",
            } for r in refs]
    except Exception as e:
        return [{"source": "EPO", "_error": str(e)}]


def search_pqai(query: str, token: str = "", limit: int = 10) -> list[dict]:
    """Search PQAI semantic patent search. Free tier: 1,500/mo."""
    url = "https://api.projectpq.ai/search/102"
    params = {"q": query, "n": limit, "type": "patent"}
    if token:
        params["token"] = token

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, params=params)
            data = _safe_json(resp)
            return [{
                "source": "PQAI",
                "patent_number": r.get("publication_number", "N/A"),
                "title": r.get("title", "Untitled"),
                "abstract": r.get("abstract", "")[:500],
                "assignee": "",
                "filing_year": 2026,
                "ipc": "",
            } for r in data.get("results", [])]
    except Exception as e:
        return [{"source": "PQAI", "_error": str(e)}]


def search_all(query: str, cfg: Any) -> list[dict]:
    """Search all configured databases, deduplicate by patent_number."""
    results: list[dict] = []
    seen: set[str] = set()

    for fn, key in [(search_uspto, "uspto_api_key"), (search_pqai, "pqai_api_key"), (search_epo, "epo_consumer_key")]:
        kwargs: dict[str, Any] = {"query": query}
        if fn is search_epo and getattr(cfg, "epo_consumer_key", "") and getattr(cfg, "epo_consumer_secret", ""):
            kwargs.update({"consumer_key": cfg.epo_consumer_key, "consumer_secret": cfg.epo_consumer_secret})
        elif fn is not search_epo and getattr(cfg, key, ""):
            kwargs["token"] = getattr(cfg, key) if fn is search_pqai else getattr(cfg, key)

        for r in fn(**kwargs):
            pn = r.get("patent_number", "")
            if pn and pn not in seen and "_error" not in r:
                seen.add(pn)
                results.append(r)

    return results
