# InventionGuard

> **⚠️ DISCLAIMER:** This tool identifies potential technical inventions in code. It does **not** provide legal advice and does **not** guarantee patentability. Always consult a qualified patent attorney before filing. AI cannot be a co-inventor.

InventionGuard is a CLI tool and GitHub Action that detects potential patentable technical improvements to computer functionality in your code commits, searches multiple patent databases in parallel via SQL (using [Coral](https://withcoral.com)), synthesizes prior art similarity scores, drafts preliminary patent claims for attorney review, and notifies your team via [OpenClaw](https://openclaw.dev).

## 🎯 Positioning

InventionGuard is an **invention detection assistant**, not an auto-patenting tool. It flags technical novelty and prepares ~90% of the technical groundwork for human (attorney) finalization.

## 🏗️ Architecture

```
git push / CLI scan
    ↓
Stage 1: Code Analysis (PyGit2 + Graphify)
    ↓
Stage 2: Invention Detection (LLM-powered)
    ↓
Stage 3: Prior Art Search (Coral SQL — USPTO, EPO, PQAI, Local)
    ↓
Stage 4: Synthesis + Claim Drafting (LLM-powered)
    ↓
Stage 5: Memory & Notification (GBrain + OpenClaw + GitHub Issue)
    ↓
Stage 6: Human Review (Attorney reviews GitHub PR)
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- [Coral](https://withcoral.com) installed: `brew install withcoral/tap/coral`
- OpenAI API key (or compatible LLM endpoint)

### Installation

```bash
pip install inventionguard
```

### Configuration

Create a `.env` file:

```env
OPENAI_API_KEY=sk-...
USPTO_API_KEY=your_uspto_key  # optional
EPO_CONSUMER_KEY=your_epo_key
EPO_CONSUMER_SECRET=your_epo_secret
PQAI_API_KEY=optional
OPENCLAW_WEBHOOK_URL=https://openclaw.gateway/webhook/invention
GBRAIN_DB_PATH=./gbrain.db
CORAL_CONFIG_DIR=./coral_sources
```

### Usage

```bash
# Scan the latest commit in the current repo
patentguard scan

# Scan a specific commit range
patentguard scan --since HEAD~5 --to HEAD

# Analyze a specific file for inventions
patentguard analyze --file src/cache/invalidator.py
```

## 🔧 Coral Integration

Coral is the architectural moat: a local-first SQL runtime that translates SQL into API calls across patent databases. See `coral_sources/` for source specs.

## 📄 License

MIT
