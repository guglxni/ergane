"""Patent database search wrappers — USPTO, EPO, PQAI."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable

import httpx


@dataclass(frozen=True)
class SearchOutcome:
    """Normalized result and observability metadata for a prior-art search."""

    records: list[dict]
    sources_queried: list[str]
    errors: list[dict]


def _safe_json(resp: httpx.Response) -> dict:
    try:
        return resp.json()
    except Exception:
        return {"_error": "Invalid JSON response"}


def _request_error(source: str, error: Exception) -> list[dict]:
    """Return an operationally useful error without recording request secrets."""
    if isinstance(error, httpx.HTTPStatusError):
        return [{"source": source, "_error": f"HTTP {error.response.status_code}"}]
    return [{"source": source, "_error": f"{type(error).__name__}: request failed"}]


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
            resp.raise_for_status()
            data = _safe_json(resp)
            if "_error" in data:
                return [{"source": "USPTO", "_error": str(data["_error"])}]
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
    except Exception as exc:
        return _request_error("USPTO", exc)


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
            token_resp.raise_for_status()
            token_data = _safe_json(token_resp)
            token = token_data.get("access_token", "")
            if not token:
                return [{"source": "EPO", "_error": "OAuth failed"}]

            search_resp = client.get(
                "https://ops.epo.org/3.2/rest-services/published-data/search",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                params={"q": query, "Range": f"1-{limit}"},
            )
            search_resp.raise_for_status()
            data = _safe_json(search_resp)
            if "_error" in data:
                return [{"source": "EPO", "_error": str(data["_error"])}]
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
    except Exception as exc:
        return _request_error("EPO", exc)


def search_pqai(query: str, token: str = "", limit: int = 10) -> list[dict]:
    """Search PQAI semantic patent search. Free tier: 1,500/mo."""
    url = "https://api.projectpq.ai/search/102"
    params: dict[str, str | int] = {"q": query, "n": limit, "type": "patent"}
    if token:
        params["token"] = token

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = _safe_json(resp)
            if "_error" in data:
                return [{"source": "PQAI", "_error": str(data["_error"])}]
            return [{
                "source": "PQAI",
                "patent_number": r.get("publication_number", "N/A"),
                "title": r.get("title", "Untitled"),
                "abstract": r.get("abstract", "")[:500],
                "assignee": "",
                "filing_year": 2026,
                "ipc": "",
            } for r in data.get("results", [])]
    except Exception as exc:
        return _request_error("PQAI", exc)


def search_all_with_metadata(query: str, cfg: Any) -> SearchOutcome:
    """Search available databases concurrently and deduplicate records.

    USPTO and PQAI are attempted without credentials because both offer a usable
    public/free tier. EPO is only attempted when OAuth credentials are present.
    Individual source failures are retained as metadata rather than silently
    converted into a false claim that no prior art exists.
    """
    limit = int(getattr(cfg, "max_prior_art", 20))
    requests: list[tuple[str, Callable[..., list[dict]], dict[str, Any]]] = [
        ("USPTO", search_uspto, {"query": query, "api_key": getattr(cfg, "uspto_api_key", ""), "limit": limit}),
        ("PQAI", search_pqai, {"query": query, "token": getattr(cfg, "pqai_api_key", ""), "limit": limit}),
    ]
    if getattr(cfg, "epo_consumer_key", "") and getattr(cfg, "epo_consumer_secret", ""):
        requests.append(("EPO", search_epo, {
            "query": query,
            "consumer_key": cfg.epo_consumer_key,
            "consumer_secret": cfg.epo_consumer_secret,
            "limit": limit,
        }))

    source_results: list[tuple[str, list[dict]]] = []
    with ThreadPoolExecutor(max_workers=len(requests)) as executor:
        futures = [(source, executor.submit(search, **kwargs)) for source, search, kwargs in requests]
        for source, future in futures:
            try:
                source_results.append((source, future.result()))
            except Exception as exc:  # Defensive: wrappers normally return an error record.
                source_results.append((source, [{"source": source, "_error": str(exc)}]))

    results: list[dict] = []
    seen: set[str] = set()
    errors: list[dict] = []
    for source, records in source_results:
        for r in records:
            if "_error" in r:
                errors.append({"source": source, "error": r["_error"]})
                continue
            pn = r.get("patent_number", "")
            if pn and pn not in seen:
                seen.add(pn)
                results.append(r)
    return SearchOutcome(records=results[:limit], sources_queried=[source for source, _, _ in requests], errors=errors)


def search_all(query: str, cfg: Any) -> list[dict]:
    """Backward-compatible list-only prior-art search."""
    return search_all_with_metadata(query, cfg).records
