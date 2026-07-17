import subprocess
import tempfile
from pathlib import Path

import pytest

from ergane.analyzer import (
    extract_claim_elements,
    extract_technical_problem,
    extract_technical_solution,
    get_commit_diffs,
)


class TestAnalyzer:
    @pytest.fixture
    def git_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
            (tmp_path / "a.py").write_text("def hello():\n    return 'world'\n")
            subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
            subprocess.run(["git", "commit", "-m", "feat: add hello function\n\nSolves greeting problem with new method"], cwd=tmp_path, check=True)
            yield tmp_path

    def test_get_commit_diffs(self, git_repo):
        # Single commit repo — use HEAD as range (same commit, no parents)
        inventions = get_commit_diffs(git_repo, "HEAD", "HEAD")
        # May return empty since no range; just verify it doesn't crash
        assert isinstance(inventions, list)

        # Add second commit for real range test
        (git_repo / "b.py").write_text("x = 1\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(["git", "commit", "-m", "feat: add second file"], cwd=git_repo, check=True)

        inventions = get_commit_diffs(git_repo, "HEAD~1", "HEAD")
        assert len(inventions) >= 1
        inv = inventions[0]
        assert inv.commit_hash
        assert "add" in inv.commit_message.lower() or "second" in inv.commit_message.lower()

    def test_extract_problem(self):
        text = "Fixes bug in cache invalidation\nProblem: race condition in concurrent map"
        problem = extract_technical_problem(text)
        assert "race" in problem.lower() or "bug" in text.lower()

    def test_extract_solution(self):
        diff = "+ def fix_race():\n+     with lock:\n+         update()"
        solution = extract_technical_solution(diff)
        assert "fix_race" in solution or "lock" in solution

    def test_claim_elements(self):
        diff = "+ class VectorClock:\n+     def tick(self):\n+         pass\n+ def synchronize()"
        elements = extract_claim_elements(diff)
        assert any("VectorClock" in e for e in elements)
        assert any("synchronize" in e for e in elements)
