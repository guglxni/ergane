"""Code analysis: diff extraction and Graphify subgraph retrieval."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

try:
    import pygit2
except Exception:  # pragma: no cover
    pygit2 = None  # type: ignore


def get_commit_diffs(repo_path: str, since: str, to: str) -> list[dict[str, Any]]:
    """Retrieve code diffs for a commit range."""
    if pygit2 is None:
        raise RuntimeError("pygit2 is not installed")

    repo = pygit2.Repository(repo_path)
    since_commit = repo.resolve_refish(since)[0]
    to_commit = repo.resolve_refish(to)[0]

    diffs: list[dict[str, Any]] = []
    for commit in repo.walk(to_commit.id, pygit2.GIT_SORT_TIME):  # type: ignore[arg-type]
        if commit.id == since_commit.id:
            break

        parent = commit.parents[0] if commit.parents else None
        if parent is None:
            continue

        diff = repo.diff(parent, commit)
        diff_text_parts: list[str] = []
        for patch in diff:
            if patch is None:
                continue
            patch_text = patch.text
            if patch_text:
                diff_text_parts.append(patch_text)
        diff_text = "\n".join(diff_text_parts)
        if not diff_text.strip():
            continue

        files_changed: list[str] = []
        for patch in diff:
            if patch is None:
                continue
            delta = patch.delta
            if delta is None:
                continue
            new_path = delta.new_file.path
            old_path = delta.old_file.path
            if new_path:
                files_changed.append(new_path)
            elif old_path:
                files_changed.append(old_path)

        diffs.append({
            "commit_hash": str(commit.id),
            "commit_message": commit.message.strip(),
            "files_changed": files_changed,
            "diff_text": diff_text,
        })

    return diffs


def get_file_diff(repo_path: str, file_path: str) -> str:
    """Get the latest diff for a single file."""
    if pygit2 is None:
        raise RuntimeError("pygit2 is not installed")

    repo = pygit2.Repository(repo_path)
    head = repo.head.peel(pygit2.Commit)
    parent = head.parents[0] if head.parents else None
    if parent is None:
        return ""

    diff = repo.diff(parent, head)
    out_lines: list[str] = []
    for patch in diff:
        if patch is None:
            continue
        delta = patch.delta
        if delta is None:
            continue
        new_path = delta.new_file.path
        old_path = delta.old_file.path
        path = new_path or old_path
        if path and (path == file_path or Path(path).name == Path(file_path).name):
            pt = patch.text
            if pt:
                out_lines.append(pt)

    return "\n".join(out_lines)


def get_graphify_subgraph(repo_path: str, files_changed: list[str]) -> dict[str, Any]:
    """Run Graphify query on modified files and return JSON subgraph."""
    try:
        # Ensure graph exists
        graph_path = Path(repo_path) / "graphify-out" / "graph.json"
        if not graph_path.exists():
            # Build graph first
            subprocess.run(
                ["graphify", "update", str(repo_path)],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )

        if not graph_path.exists():
            return {"error": "Graphify graph not available", "nodes": [], "edges": []}

        query = f"Identify data processing and synchronization methods in files: {', '.join(files_changed)}"
        result = subprocess.run(
            ["graphify", "query", query, "--graph", str(graph_path), "--json"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        if result.returncode == 0 and result.stdout.strip():
            try:
                data: dict[str, Any] = json.loads(result.stdout)
                return data
            except json.JSONDecodeError:
                return {"raw": result.stdout, "nodes": [], "edges": []}
        else:
            return {"error": result.stderr or "graphify query failed", "nodes": [], "edges": []}
    except Exception as exc:  # pragma: no cover
        return {"error": str(exc), "nodes": [], "edges": []}
