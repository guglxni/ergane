# Ergane — Patent Intelligence for Code Commits

[**Developer Tools Track**](#) | OpenAI Build Week 2026 | July 18, 2026

> **Ergane** (Ἐργάνη) — the Greek goddess of diligence and industry — a CLI tool + GitHub Action that detects patentable technical inventions in your code commits before they become public prior art.

## 🎯 Problem

Engineers invent patentable technology every single commit — novel caching strategies, consensus algorithms, data structures, synchronization mechanisms. By the time legal reviews, the invention is already public. Patentability destroyed. Prior art searches cost $5-15,000 each. Early detection is everything.

## 💡 Solution

Ergane runs on every `git push`:

```
Stage 1: Extract invention  →  Stage 2: Search patents  →  Stage 3: Synthesize  →  Stage 4: Notify
```

It extracts the technical problem and solution from your diff, searches USPTO + EPO + PQAI in parallel, generates a novelty score, synthesizes a preliminary claim, and posts results to your GitHub PR + team Slack via OpenClaw webhook.

## 🚀 Quick Start

```bash
# Install
pip install ergane

# Scan last commit
export OPENAI_API_KEY="sk-..."
ergane scan --since HEAD~1

# Dry run (no API calls)
ergane scan --since HEAD~1 --dry-run

# Check analysis dashboard
ergane analyze
```

## 🏗️ Architecture

| Module | Purpose | File |
|--------|---------|------|
| **config** | Env vars + .ergane.toml | `ergane/config.py` |
| **analyzer** | PyGit2 diff parsing, invention extraction | `ergane/analyzer.py` |
| **scoring** | BM25 + IPC Jaccard + temporal decay + ensemble | `ergane/scoring.py` |
| **patent_search** | USPTO ODP + EPO OPS + PQAI parallel search | `ergane/patent_search.py` |
| **synthesizer** | GPT-5.6-sol claim drafting, risk assessment | `ergane/synthesizer.py` |
| **notifier** | GitHub PR comment + OpenClaw webhook | `ergane/notifier.py` |
| **state** | .github/ergane-state.md persistent tracking | `ergane/state.py` |
| **cli** | Typer + Rich terminal UI | `ergane/cli.py` |

## 🤖 Codex + GPT-5.6 Usage

Built with **Codex CLI v0.144.5** and **GPT-5.6-sol/terra/luna** (July 2026).

| Stage | Model | Reasoning | Task |
|-------|-------|-----------|------|
| 1 | gpt-5.6-luna | low | Diff parsing, technical extraction |
| 2 | gpt-5.6-terra | medium | Coral SQL/Direct API patent search |
| 3 | gpt-5.6-sol | high | Claim drafting, legal synthesis |
| 4 | gpt-5.6-luna | low | PR comment + notification formatting |

Codex was used as the developer agent for feature implementation and lint fixes:

```bash
# Example: ask Codex to implement a scoring algorithm
codex exec -m gpt-5.6-terra "Implement novelty sigmoid scoring in scoring.py"
```

> **Note:** Codex CLI Free/Go tier usage limit was reached on July 18, 2026 during final build. The last Codex session ID was `019f71f3-ce2f-79e3-a2bc-de8d7997cdb9` (exec mode, lint fixes). For Build Week submissions requiring `/feedback`, this may serve as evidence of Codex usage. If an active session is needed, upgrade to ChatGPT Plus or use the existing session archive.


## 🔧 Configuration

```bash
# Environment variables
export OPENAI_API_KEY="sk-..."          # Required for synthesis
export ERGANE_MODEL="gpt-5.6-sol"       # Default: gpt-5.6-sol
export ERGANE_NOVELTY_THRESHOLD=0.4     # Min score to flag

# Or create .ergane.toml in repo root
[ergane]
novelty_threshold = 0.5
excluded_paths = ["*.md", "tests/**"]
```

## 🧪 Tests

```bash
pytest tests/ -v --cov=ergane
```

## 🎬 Demo

[TODO: Link to <3 min YouTube video showing Ergane scan → novelty score → PR comment]

## 📄 License

MIT — See [LICENSE](LICENSE)

## 🙏 Acknowledgments

- Built for **OpenAI Build Week 2026** — Developer Tools Track
- Uses **Codex CLI** with GPT-5.6-sol/terra/luna models
- Patent data from **USPTO**, **EPO OPS**, **PQAI**
- Loop Engineering principles from **Addy Osmani**

## 📝 Submission Notes

- **`/feedback` Session ID:** [TBD — run inside Codex and type `/feedback`]
- **Track:** Developer Tools
- **GitHub Repo:** [TBD]
- **Devpost Project:** [TBD]
