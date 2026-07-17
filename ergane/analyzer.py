"""Git diff analysis — extract technical invention from commits."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import git


@dataclass
class Invention:
    """Extracted invention from a code commit."""

    commit_hash: str
    commit_message: str
    files_changed: list[str]
    diff_text: str = ""
    technical_problem: str = ""
    technical_solution: str = ""
    key_claim_elements: list[str] = field(default_factory=list)


def get_commit_diffs(repo_path: Path, since_ref: str, to_ref: str = "HEAD") -> list[Invention]:
    """Extract diff + metadata for commits between since_ref and to_ref."""
    repo = git.Repo(repo_path)
    since = repo.commit(since_ref)
    to = repo.commit(to_ref)

    inventions: list[Invention] = []
    for commit in repo.iter_commits(f"{since.hexsha}..{to.hexsha}"):
        diff = commit.parents[0].diff(commit) if commit.parents else []
        files = [d.b_path or d.a_path for d in diff if d.b_path or d.a_path]

        patch_parts = []
        for d in diff:
            if d.diff:
                if isinstance(d.diff, bytes):
                    patch_parts.append(d.diff.decode("utf-8", errors="replace"))
                else:
                    patch_parts.append(str(d.diff))
        patch = "\n".join(patch_parts)

        msg = commit.message
        if isinstance(msg, bytes):
            msg = msg.decode("utf-8", errors="replace")

        inventions.append(
            Invention(
                commit_hash=commit.hexsha[:8],
                commit_message=msg.strip(),
                files_changed=[f for f in files if f],
                diff_text=patch[:8000],
            )
        )
    return inventions


def extract_technical_problem(text: str) -> str:
    """Heuristic: find problem statement in commit message or diff comments."""
    for pat in [
        r"(?:Problem|Issue|Bug|Fixes)\s*[:#]\s*(.+?)(?:\n|$)",
        r"(?:fix|solve|address|resolve)[sd]?\s+(?:the\s+)?(.+?)(?:\n|$)",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:500]
    return ""


def extract_technical_solution(diff_text: str) -> str:
    """Heuristic: find solution — new function signatures, algorithm changes."""
    added = [ln[1:] for ln in diff_text.splitlines() if ln.startswith("+") and not ln.startswith("+++")]
    funcs = [fn_ln for fn_ln in added if re.match(r"^\s*(def|class|function)\s+", fn_ln)]
    if funcs:
        return "\n".join(funcs[:5])[:800]
    return "\n".join(added[:20])[:800]


def extract_claim_elements(diff_text: str) -> list[str]:
    """Heuristic: extract key technical elements from diff."""
    elements: list[str] = []
    added = [ln[1:] for ln in diff_text.splitlines() if ln.startswith("+") and not ln.startswith("+++")]

    for line in added:
        if "class " in line:
            m = re.search(r"class\s+(\w+)", line)
            if m:
                elements.append(f"data structure: {m.group(1)}")
        if "def " in line and "(" in line:
            m = re.search(r"def\s+(\w+)", line)
            if m:
                elements.append(f"method: {m.group(1)}")

    lowered = diff_text.lower()
    if "lock" in lowered:
        elements.append("synchronization mechanism")
    if "cache" in lowered:
        elements.append("caching strategy")
    if "queue" in lowered:
        elements.append("queue-based processing")
    if "vector" in lowered and "clock" in lowered:
        elements.append("vector clock consensus")

    return list(dict.fromkeys(elements))[:10]
