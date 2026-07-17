# AGENTS.md
# Project context for Codex — OpenAI Build Week 2026 submission

## Project
Ergane — CLI tool + GitHub Action to detect patentable technical inventions in code diffs.
Track: Developer Tools
Deadline: July 21, 2026 5:00 PM PT

## Stack
- Python 3.11 / Typer / Rich / GitPython / httpx / pydantic
- OpenAI API (GPT-5.6-sol/terra/luna)
- Patent APIs: USPTO ODP, EPO OPS, PQAI
- pytest for tests

## Commands
- `pytest tests/ -v` — run test suite
- `ergane scan --since HEAD~1 --dry-run` — scan last commit without API calls
- `ergane analyze` — show detected inventions dashboard
- `ergane config-show` — display configuration
- `pip install -e .` — install in development mode

## Architecture
- `ergane/config.py` — Pydantic-based configuration (env vars + .ergane.toml)
- `ergane/analyzer.py` — Git diff parsing, invention extraction heuristics
- `ergane/scoring.py` — Novelty sigmoid, IPC Jaccard, temporal decay, ensemble scoring
- `ergane/patent_search.py` — USPTO + EPO + PQAI search with parallel dedup
- `ergane/synthesizer.py` — OpenAI API call for claim drafting + risk assessment
- `ergane/notifier.py` — GitHub PR comment + OpenClaw webhook formatting
- `ergane/state.py` — .github/ergane-state.md persistence
- `ergane/cli.py` — Typer CLI with scan/analyze/config-show commands

## Conventions
- Use `from __future__ import annotations`
- Type hints everywhere
- Raise typer.Exit(1) for CLI errors, not sys.exit
- Rich panels for formatted output
- JSON output mode supported via --json flag
- Dry-run mode skips all API calls and LLM synthesis

## Testing
- Tests in `tests/` directory
- Use pytest fixtures for git repos (create temp repos with subprocess git commands)
- Single-commit repos: HEAD~1 fails, use HEAD..HEAD or add second commit first
