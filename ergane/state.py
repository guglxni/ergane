"""State persistence — .github/ergane-state.md tracking."""
from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _state_path(repo_path: Path) -> Path:
    return repo_path / ".github" / "ergane-state.md"


def _audit_path(repo_path: Path) -> Path:
    return repo_path / ".github" / "ergane-audit.ndjson"


def append_audit_event(repo_path: Path, event: dict[str, Any]) -> None:
    """Append a compact, machine-readable audit record for one pipeline event."""
    import json

    path = _audit_path(repo_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": datetime.now(UTC).isoformat(), **event}
    with path.open("a", encoding="utf-8") as audit_file:
        audit_file.write(json.dumps(payload, sort_keys=True, default=str) + "\n")


def read_state(repo_path: Path = Path(".")) -> dict:
    """Parse ergane-state.md into structured data."""
    path = _state_path(repo_path)
    if not path.exists():
        return {"inventions": [], "false_positives": [], "version": "0.1.0", "text": ""}

    text = path.read_text()
    inventions = []
    in_table = False
    for line in text.splitlines():
        if "| ID |" in line:
            in_table = True
            continue
        if in_table and line.startswith("|") and "INV-" in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 5:
                inventions.append({
                    "id": parts[0],
                    "date": parts[1],
                    "commit": parts[2],
                    "novelty": parts[3],
                    "status": parts[4],
                    "pr": parts[5] if len(parts) > 5 else "",
                })
    return {"inventions": inventions, "text": text}


def append_invention(repo_path: Path, invention: Any, result: dict, pr_url: str = "") -> str:
    """Append one invention row, returning an existing ID when re-scanned."""
    path = _state_path(repo_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    state = read_state(repo_path)
    for existing in state["inventions"]:
        if existing.get("commit") == invention.commit_hash:
            return str(existing["id"])
    inv_id = f"INV-{len(state['inventions']) + 1:03d}"
    novelty = result.get("novelty_score", 0.0)
    assessment = result.get("novelty_assessment", "UNKNOWN")

    if not path.exists():
        _init_state(path)

    date = datetime.now(UTC).date().isoformat()
    row = f"| {inv_id} | {date} | {invention.commit_hash} | {novelty} {assessment} | pending-review | {pr_url} |"
    text = path.read_text()
    lines = text.rstrip().splitlines()
    # Remove legacy empty table row (|---|---|---|---|---|---|)
    lines = [ln for ln in lines if ln.strip().replace("|", "").replace("-", "").replace(" ", "") != ""]
    lines.append(row)
    path.write_text("\n".join(lines) + "\n")
    return inv_id


def _init_state(path: Path) -> None:
    path.write_text(
        """# Ergane State\n\n## Detected Inventions
| ID | Date | Commit | Novelty | Status | PR |
|---|---|---|---|---|---|\n\n## False Positive Patterns
- UI layout changes — add exclusion filter
- README updates — add documentation exclusion\n\n## Version
- v0.1.0
"""
    )


def update_status(repo_path: Path, inv_id: str, status: str) -> bool:
    """Update status of an invention in state file."""
    path = _state_path(repo_path)
    if not path.exists():
        return False
    text = path.read_text()
    new_text = re.sub(
        rf"(\| {re.escape(inv_id)} \| [^|]+ \| [^|]+ \| [^|]+ \| )[^|]+",
        rf"\1{status}",
        text,
    )
    if new_text != text:
        path.write_text(new_text)
        return True
    return False
