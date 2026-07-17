import pytest

from ergane.analyzer import Invention
from ergane.scoring import ensemble_novelty, ipc_similarity, novelty_sigmoid, temporal_score


class TestNoveltySigmoid:
    def test_basic_compression(self):
        assert 0.0 < novelty_sigmoid(0.6) < 1.0
        assert novelty_sigmoid(0.6) == pytest.approx(0.5, abs=0.01)

    def test_high_score(self):
        assert novelty_sigmoid(0.9) > 0.6  # z=0.6 → sigmoid ≈ 0.65

    def test_low_score(self):
        assert novelty_sigmoid(0.3) < 0.4  # z=-0.6 → sigmoid ≈ 0.35


class TestIPCSimilarity:
    def test_exact_match(self):
        assert ipc_similarity("G06F-17/30", "G06F-17/30") == 1.0

    def test_partial_match(self):
        # "G06F-17/30" vs "G06F-17/40": G06F and 17 match (2 of 3 parts)
        assert ipc_similarity("G06F-17/30", "G06F-17/40") == pytest.approx(2/3, abs=0.01)

    def test_no_match(self):
        assert ipc_similarity("G06F", "H04L") == 0.0

    def test_empty(self):
        assert ipc_similarity("", "G06F") == 0.0


class TestTemporalScore:
    def test_fresh_patent(self):
        assert temporal_score(2026, current_year=2026) == pytest.approx(1.0, abs=0.01)

    def test_old_patent(self):
        assert temporal_score(2000, current_year=2026) < 0.1


class TestEnsembleNovelty:
    def test_high_novelty_empty_prior_art(self):
        inv = Invention("abc123", "feat: new algo", ["a.py"])
        result = ensemble_novelty(inv, [])
        assert result["novelty_score"] == 1.0
        assert result["novelty_assessment"] == "HIGH"

    def test_low_novelty_with_prior_art(self):
        inv = Invention("abc123", "feat: new algo", ["a.py"])
        prior = [{
            "source": "USPTO",
            "patent_number": "US10,000,000",
            "title": "Similar Algorithm",
            "abstract": "new algo for caching and synchronization with vector clock consensus",
            "ipc": "G06F-17/30",
            "filing_year": 2024,
        }]
        result = ensemble_novelty(inv, prior)
        assert result["novelty_score"] < 1.0

    def test_medium_novelty(self):
        inv = Invention("abc123", "feat: something", ["b.py"])
        prior = [{
            "source": "USPTO",
            "patent_number": "US9,000,000",
            "title": "Somewhat Related",
            "abstract": "different domain entirely blockchain consensus",
            "ipc": "H04L",
            "filing_year": 2020,
        }]
        result = ensemble_novelty(inv, prior)
        assert 0.0 < result["novelty_score"] < 1.0
