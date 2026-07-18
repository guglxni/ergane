from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import httpx
from typer.testing import CliRunner

from ergane.analyzer import Invention, assess_invention
from ergane.cli import app
from ergane.config import get_config
from ergane.notifier import build_openclaw_payload, find_existing_ergane_comment, format_pr_comment
from ergane.patent_search import _safe_json, search_all_with_metadata
from ergane.privacy import external_processing_allowed
from ergane.state import append_audit_event, append_invention, read_state
from ergane.synthesizer import SynthesisResult, synthesize


def _candidate_invention() -> Invention:
    return Invention(
        commit_hash="abcd1234",
        commit_message="feat: reconcile distributed cache\n\nProblem: stale cache records after a network partition",
        files_changed=["ergane/cache.py"],
        technical_problem="stale cache records after a network partition",
        technical_solution="class VectorClock: synchronize distributed cache state",
        key_claim_elements=["data structure: VectorClock", "method: synchronize", "vector clock consensus"],
    )


def test_triage_skips_documentation_change() -> None:
    invention = Invention(
        commit_hash="docs1234",
        commit_message="docs: clarify setup",
        files_changed=["README.md"],
        technical_solution="documentation update",
    )

    result = assess_invention(invention)

    assert result["skip"] is True
    assert result["novelty_assessment"] == "LOW"
    assert result["ipc_suggestion"] == ""


def test_triage_requires_problem_claims_and_ipc_hint() -> None:
    result = assess_invention(_candidate_invention())

    assert result["skip"] is False
    assert result["candidate_score"] >= 0.4
    assert result["ipc_suggestion"] == "G06F 12/08"


def test_search_outcome_deduplicates_and_preserves_source_errors(monkeypatch) -> None:
    from ergane import patent_search

    monkeypatch.setattr(
        patent_search,
        "search_uspto",
        lambda **_: [{"source": "USPTO", "patent_number": "US-1", "title": "One"}],
    )
    monkeypatch.setattr(
        patent_search,
        "search_pqai",
        lambda **_: [
            {"source": "PQAI", "patent_number": "US-1", "title": "Duplicate"},
            {"source": "PQAI", "_error": "rate limited"},
        ],
    )
    config = SimpleNamespace(max_prior_art=20, uspto_api_key="", pqai_api_key="", epo_consumer_key="", epo_consumer_secret="")

    outcome = search_all_with_metadata("vector clock", config)

    assert outcome.sources_queried == ["USPTO", "PQAI"]
    assert [record["patent_number"] for record in outcome.records] == ["US-1"]
    assert outcome.errors == [{"source": "PQAI", "error": "rate limited"}]


def test_state_is_idempotent_for_rescans(tmp_path: Path) -> None:
    invention = _candidate_invention()
    result = {"novelty_score": 0.81, "novelty_assessment": "HIGH"}

    first_id = append_invention(tmp_path, invention, result)
    second_id = append_invention(tmp_path, invention, result)

    assert first_id == second_id == "INV-001"
    assert len(read_state(tmp_path)["inventions"]) == 1


def test_repo_toml_supplies_defaults_but_environment_wins(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / ".ergane.toml").write_text("novelty_threshold = 0.55\nmax_prior_art = 12\n")
    assert get_config(tmp_path).novelty_threshold == 0.55
    assert get_config(tmp_path).max_prior_art == 12

    monkeypatch.setenv("ERGANE_NOVELTY_THRESHOLD", "0.7")
    assert get_config(tmp_path).novelty_threshold == 0.7


def test_config_accepts_standard_openai_environment_name(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    assert get_config(Path.cwd()).openai_api_key == "test-key"


def test_repo_config_cannot_override_external_endpoint_or_private_opt_in(tmp_path: Path) -> None:
    (tmp_path / ".ergane.toml").write_text(
        'openai_base_url = "https://attacker.invalid/v1"\nallow_private_repos = true\nnovelty_threshold = 0.55\n'
    )

    config = get_config(tmp_path)

    assert config.openai_base_url == "https://api.openai.com/v1"
    assert config.allow_private_repos is False
    assert config.novelty_threshold == 0.55


def test_invalid_upstream_json_never_returns_response_body() -> None:
    response = httpx.Response(502, content=b"token=should-not-be-exposed")

    assert _safe_json(response) == {"_error": "Invalid JSON response"}


def test_notification_contract_contains_review_context() -> None:
    invention = _candidate_invention()
    result = {
        "novelty_score": 0.81,
        "novelty_assessment": "HIGH",
        "risk_assessment": "NOVEL",
        "overall_similarity_score": 19.0,
        "closest_prior_art": {"patent_number": "US-1", "title": "Cache synchronization", "source": "USPTO"},
        "draft_independent_claim": "1. A method comprising: reconciling vector clocks.",
        "recommendation": "PROCEED_WITH_FILING",
    }

    comment = format_pr_comment(result, invention)
    payload = build_openclaw_payload(result, invention, "example/ergane", 42)

    assert "Key Claim Elements" in comment
    assert "Draft Independent Claim" in comment
    assert payload["github_pr_url"].endswith("/pull/42")
    assert payload["closest_patent_number"] == "US-1"


def test_comment_marker_finds_existing_pr_comment() -> None:
    comment = format_pr_comment({"novelty_score": 0.5, "novelty_assessment": "MEDIUM"}, _candidate_invention())
    existing = find_existing_ergane_comment([{"id": 7, "body": comment}], comment)

    assert existing == {"id": 7, "body": comment}


def test_private_repo_opt_in_skips_remote_visibility_lookup(tmp_path: Path) -> None:
    allowed, reason = external_processing_allowed(tmp_path, github_token="", allow_private_repos=True)

    assert allowed is True
    assert "explicitly enabled" in reason


def test_audit_event_is_append_only_json_lines(tmp_path: Path) -> None:
    append_audit_event(tmp_path, {"event": "scan_completed", "commit": "abcd1234"})
    append_audit_event(tmp_path, {"event": "scan_completed", "commit": "dcba4321"})

    rows = (tmp_path / ".github" / "ergane-audit.ndjson").read_text().splitlines()
    assert len(rows) == 2
    assert '"commit": "abcd1234"' in rows[0]


def test_synthesis_uses_validated_responses_output(monkeypatch) -> None:
    import ergane.synthesizer as synthesizer

    captured: dict[str, object] = {}

    class FakeResponses:
        def parse(self, **kwargs: object) -> object:
            captured.update(kwargs)
            return SimpleNamespace(
                output_parsed=SynthesisResult(
                    overall_similarity_score=21.0,
                    closest_patent={"patent_number": "US-1", "title": "Cache", "source": "USPTO", "similarity_score": 21.0},
                    risk_assessment="NOVEL",
                    analysis="Technical comparison.",
                    draft_independent_claim="1. A method comprising: reconciling cache state.",
                    recommendation="PROCEED_WITH_FILING",
                    novelty_score=0.79,
                    disclaimer="Preliminary draft for attorney review only.",
                )
            )

    class FakeClient:
        responses = FakeResponses()

    monkeypatch.setattr(synthesizer, "OpenAI", lambda **_: FakeClient())
    result = synthesize(_candidate_invention(), [], api_key="test-key", reasoning_effort="high")

    assert result["novelty_score"] == 0.79
    assert captured["text_format"] is SynthesisResult
    assert captured["store"] is False


def test_dry_run_writes_no_state_file(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "cache.py").write_text("class VectorClock:\n    def synchronize(self):\n        return None\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "feat: reconcile cache\n\nProblem: stale cache after network partition"],
        cwd=tmp_path,
        check=True,
    )
    (tmp_path / "cache.py").write_text("class VectorClock:\n    def synchronize(self):\n        return 'reconciled'\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "feat: improve cache reconciliation\n\nProblem: stale cache after network partition"],
        cwd=tmp_path,
        check=True,
    )

    result = CliRunner().invoke(app, ["scan", "--repo", str(tmp_path), "--dry-run", "--json"])

    assert result.exit_code == 0, result.output
    assert '"risk_assessment": "DRY_RUN"' in result.output
    assert not (tmp_path / ".github" / "ergane-state.md").exists()
