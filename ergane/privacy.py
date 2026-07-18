"""Repository consent checks before Ergane sends code-derived text externally."""
from __future__ import annotations

import re
from pathlib import Path

import git
import httpx


def github_repo_slug(repo_path: Path) -> str | None:
    """Return an owner/repository slug for an origin hosted on GitHub."""
    try:
        repo = git.Repo(repo_path)
        origin = repo.remotes.origin
        urls = list(origin.urls)
    except (AttributeError, git.GitError, ValueError):
        return None

    for url in urls:
        match = re.search(r"github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?$", url)
        if match:
            return f"{match.group(1)}/{match.group(2)}"
    return None


def external_processing_allowed(repo_path: Path, github_token: str, allow_private_repos: bool) -> tuple[bool, str]:
    """Fail closed for GitHub repositories whose visibility cannot be verified.

    A repository with no GitHub origin is assumed to be directly in the caller's
    local scope. GitHub-hosted repositories require either verified public
    visibility or an explicit `allow_private_repos` opt-in.
    """
    if allow_private_repos:
        return True, "Private-repository processing explicitly enabled."

    slug = github_repo_slug(repo_path)
    if not slug:
        return True, "No GitHub origin detected; processing caller-provided local scope."

    headers = {"Accept": "application/vnd.github+json"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"https://api.github.com/repos/{slug}", headers=headers)
            if response.status_code == 200 and response.json().get("private") is False:
                return True, "Verified public GitHub repository."
    except httpx.HTTPError:
        pass
    return False, "Could not verify that the GitHub repository is public; set ERGANE_ALLOW_PRIVATE_REPOS=true to opt in."
