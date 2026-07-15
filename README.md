# InventionGuard

> **OpenAI Build Week 2026 — Developer Tools Track**  
> **Deadline: Jul 22, 2026 @ 5:30am GMT+5:30**

> **⚠️ LEGAL DISCLAIMER:** This tool identifies potential technical inventions in code. It does **not** provide legal advice and does **not** guarantee patentability. Always consult a qualified patent attorney before filing. AI cannot be a co-inventor under USPTO guidance (Nov 2025).

InventionGuard is a CLI tool and GitHub Action that detects potential patentable technical improvements to computer functionality in your code commits, searches multiple patent databases in parallel via SQL (using [Coral](https://withcoral.com)), synthesizes prior art similarity scores, drafts preliminary patent claims for attorney review, and notifies your team via [OpenClaw](https://openclaw.dev).

## 🎯 Positioning

**Invention detection assistant** — NOT an auto-patenting tool. It flags technical novelty and prepares ~90% of the technical groundwork for human (attorney) finalization. It never claims to replace lawyers or guarantee patentability.

## 🏗️ Architecture

```
git push / CLI scan
    ↓
Stage 1: Code Analysis (PyGit2 + Graphify)
    ↓
Stage 2: Invention Detection (LLM-powered via OpenAI-compatible API)
    ↓
Stage 3: Prior Art Search (Coral SQL — USPTO, EPO, LOCAL + direct PQAI API)
    ↓
Stage 4: Synthesis + Claim Drafting (LLM-powered)
    ↓
Stage 5: Memory & Notification (GBrain + OpenClaw + GitHub Issue)
    ↓
Stage 6: Human Review (Attorney reviews GitHub PR / Issue)
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- [Coral](https://withcoral.com) installed: `brew install withcoral/tap/coral`
- OpenAI API key (or any OpenAI-compatible endpoint) — optional; heuristic fallback works without it

### Installation

```bash
# Clone the repository
git clone https://github.com/<your-org>/inventionguard.git
cd inventionguard

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode
pip install -e ".[dev]"

# Add Coral sources
coral source add --file coral_sources/uspto.yaml
coral source add --file coral_sources/epo.yaml
coral source add --file coral_sources/local_patents.yaml
```

### Configuration

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

Required environment variables:

```env
OPENAI_API_KEY=sk-...          # Optional — enables GPT-4o detection & synthesis
OPENAI_BASE_URL=https://api.openai.com/v1
EPO_CONSUMER_KEY=your_epo_key  # Required for EPO patent search
EPO_CONSUMER_SECRET=your_epo_secret
USPTO_API_KEY=your_uspto_key   # Optional for USPTO
OPENCLAW_WEBHOOK_URL=https://openclaw.gateway/webhook/invention
GITHUB_TOKEN=ghp_...
GITHUB_REPOSITORY=owner/repo
```

### CLI Usage

```bash
# Scan the latest commit in the current repo
patentguard scan

# Scan a specific commit range
patentguard scan --since HEAD~5 --to HEAD

# Analyze a specific file for inventions
patentguard analyze --file src/cache/invalidator.py

# Output JSON for CI pipelines
patentguard scan --since HEAD~1 --to HEAD --json
```

### GitHub Action

Add the workflow to `.github/workflows/inventionguard.yml` (included in this repo):

```yaml
name: InventionGuard Scan
on:
  push:
    branches: [main, master]
jobs:
  inventionguard:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      issues: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install inventionguard
      - run: |
          curl -fsSL https://withcoral.com/install.sh | sh
          coral source add --file coral_sources/uspto.yaml || true
          coral source add --file coral_sources/epo.yaml || true
          coral source add --file coral_sources/local_patents.yaml || true
      - run: patentguard scan --since ${{ github.event.before }} --to ${{ github.sha }}
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_REPOSITORY: ${{ github.repository }}
```

## 🔧 Coral Integration (The Architectural Moat)

[Coral](https://withcoral.com) is an open-source (Apache 2.0) local-first SQL runtime that translates SQL into API calls. It handles auth, pagination, rate limits, and cross-source JOINs locally via the DataFusion engine.

InventionGuard uses Coral to search **four patent sources in parallel** through a single SQL query:

1. **USPTO** — US Patent Open Data Portal
2. **EPO** — European Patent Office Open Patent Services (OPS)
3. **Local Patents** — Local Parquet/Arrow corpus of USPTO bulk data
4. **PQAI** — Semantic prior-art search (direct REST API, since Coral DSL v3 does not support table functions)

Example Coral SQL executed by the agent:

```sql
WITH uspto_results AS (
    SELECT patent_number, title, abstract, assignee, 0.8 AS source_weight
    FROM uspto.patents
    WHERE q = 'distributed cache invalidation vector clock'
    LIMIT 10
),
epo_results AS (
    SELECT doc_number AS patent_number, title, abstract, applicant AS assignee, 0.8 AS source_weight
    FROM epo.patents
    WHERE q = 'ti=distributed cache AND ab=vector clock'
    LIMIT 10
),
local_results AS (
    SELECT patent_number, title, abstract, assignee, 0.6 AS source_weight
    FROM local_patents.grants
    WHERE abstract LIKE '%vector clock%' AND abstract LIKE '%cache%'
    LIMIT 10
)
SELECT * FROM uspto_results
UNION ALL SELECT * FROM epo_results
UNION ALL SELECT * FROM local_results
ORDER BY source_weight DESC
LIMIT 20;
```

## 🧰 Codex / LLM Acceleration Points

1. **Invention Detection Prompt** — Codex accelerated the design of the structured JSON extraction prompt and fallback heuristic.
2. **Coral Source Specs** — Codex helped translate raw API documentation into valid Coral DSL v3 YAML manifests.
3. **Prior Art Synthesis Prompt** — Codex iterated the synthesis prompt to ensure proper USPTO claim language and legal-safe output.
4. **OpenClaw Skill** — Codex generated the OpenClaw webhook handler YAML from the notification payload spec.
5. **GitHub Action** — Codex scaffolded the CI workflow with artifact upload, issue creation, and secret injection.

## 🔒 Legal & Safety

- **Software/code itself is NOT patentable.** Only the underlying technical improvement to computer functionality is patentable (USPTO Section 101/Alice).
- **GitHub code is NOT legally recognized as patent prior art by USPTO.** Use it only for product validation, not legal prior art claims.
- **AI cannot be a co-inventor** (USPTO Nov 2025 guidance). The tool prepares technical groundwork for human finalization.
- Every output includes: *"This tool identifies potential technical inventions. It does not provide legal advice. Consult a patent attorney."*
- Local-first architecture: sensitive invention data stays on your machine. No generic OpenAI API training on user data.

## 📦 Project Structure

```
inventionguard/
├── inventionguard/
│   ├── cli.py            # Typer CLI entry point
│   ├── analyzer.py       # PyGit2 diff + Graphify subgraph
│   ├── detector.py       # LLM invention detection prompts
│   ├── prior_art.py      # Coral SQL + PQAI API search
│   ├── synthesizer.py    # Prior art synthesis + claim drafting
│   ├── notifier.py       # OpenClaw + GBrain integration
│   └── config.py         # Settings & env var management
├── skills/
│   ├── scan_repo.py
│   ├── detect_invention.py
│   ├── search_prior_art.py
│   ├── draft_claim.py
│   └── notify_team.py
├── coral_sources/
│   ├── uspto.yaml
│   ├── epo.yaml
│   └── local_patents.yaml
├── .github/workflows/inventionguard.yml
├── SOUL.md
├── RULES.md
├── MEMORY.md
├── pyproject.toml
└── README.md
```

## 🧪 Testing

```bash
# Run linters
ruff check inventionguard/ skills/
mypy inventionguard/ skills/

# Run unit tests
pytest tests/

# Test CLI end-to-end
patentguard scan --since HEAD~1 --to HEAD --skip-notify
```

## 📄 License

MIT — See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [Coral](https://withcoral.com) — SQL-over-API runtime
- [OpenClaw](https://openclaw.dev) — Notification gateway (judge advantage: Peter "Clawfather" Steinberger)
- [Graphify](https://github.com/safishamsi/graphify) — Code knowledge graphs
- [GBrain](https://github.com/garrytan/gbrain) — Agent memory layer
- [PQAI](https://search.projectpq.ai) — Semantic prior art search
