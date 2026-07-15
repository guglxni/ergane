# Graph Report - inventionguard  (2026-07-16)

## Corpus Check
- 20 files · ~5,177 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 111 nodes · 147 edges · 14 communities (10 shown, 4 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 5 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4e0ffdfa`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- VectorClock
- scan
- detect_invention
- notifier.py
- InventionGuard
- prior_art.py
- synthesizer.py
- MEMORY.md — InventionGuard
- config.py
- SOUL.md — InventionGuard
- __init__.py
- RULES.md
- inventionguard

## God Nodes (most connected - your core abstractions)
1. `scan()` - 11 edges
2. `detect_invention()` - 9 edges
3. `VectorClock` - 8 edges
4. `search_prior_art()` - 7 edges
5. `DistributedCache` - 6 edges
6. `get_graphify_subgraph()` - 6 edges
7. `analyze()` - 6 edges
8. `notify()` - 6 edges
9. `synthesize()` - 6 edges
10. `InventionGuard` - 6 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `get_commit_diffs()`  [EXTRACTED]
  skills/scan_repo.py → inventionguard/analyzer.py
- `main()` --calls--> `detect_invention()`  [EXTRACTED]
  skills/draft_claim.py → inventionguard/detector.py
- `main()` --calls--> `search_prior_art()`  [EXTRACTED]
  skills/draft_claim.py → inventionguard/prior_art.py
- `main()` --calls--> `search_prior_art()`  [EXTRACTED]
  skills/search_prior_art.py → inventionguard/prior_art.py
- `main()` --calls--> `detect_invention()`  [EXTRACTED]
  skills/detect_invention.py → inventionguard/detector.py

## Import Cycles
- None detected.

## Communities (14 total, 4 thin omitted)

### Community 0 - "VectorClock"
Cohesion: 0.14
Nodes (9): DistributedCache, Any, Distributed cache invalidation using vector clocks.  This module implements a no, A vector clock for tracking event ordering across nodes., Return -1 if self < other, 1 if self > other, 0 if concurrent., Cache with vector-clock-based invalidation protocol., Invalidate if remote_vc is newer than local., Reconcile cache state with another node after partition heals. (+1 more)

### Community 1 - "scan"
Cohesion: 0.18
Nodes (15): get_commit_diffs(), get_file_diff(), get_graphify_subgraph(), Any, Code analysis: diff extraction and Graphify subgraph retrieval., Retrieve code diffs for a commit range., Get the latest diff for a single file., Run Graphify query on modified files and return JSON subgraph. (+7 more)

### Community 2 - "detect_invention"
Cohesion: 0.21
Nodes (10): detect_invention(), _heuristic_detection(), Any, Invention detection via LLM., Quick heuristic when LLM is unavailable., Send diff + subgraph to LLM for invention detection., main(), GitAgent skill: detect_invention.py Detects inventions in a single diff. (+2 more)

### Community 3 - "notifier.py"
Cohesion: 0.21
Nodes (10): _get_commit_author(), notify(), Any, Notification: OpenClaw webhook + GBrain memory storage., Send OpenClaw webhook notification., Store invention note in GBrain via MCP or CLI if available., Get commit author email., store_in_gbrain() (+2 more)

### Community 4 - "InventionGuard"
Cohesion: 0.18
Nodes (10): 🏗️ Architecture, Configuration, 🔧 Coral Integration, Installation, InventionGuard, 📄 License, 🎯 Positioning, Prerequisites (+2 more)

### Community 5 - "prior_art.py"
Cohesion: 0.24
Nodes (8): build_coral_sql(), Any, Prior art search via Coral SQL and direct PQAI API., Generate the multi-source Coral SQL query., Search USPTO, EPO, local patents via Coral; PQAI via direct API., search_prior_art(), main(), GitAgent skill: search_prior_art.py Generates Coral SQL and executes prior art s

### Community 6 - "synthesizer.py"
Cohesion: 0.31
Nodes (7): _heuristic_synthesis(), Any, Synthesis: compare invention against prior art and draft claims., Synthesize invention against prior art and draft claims., synthesize(), main(), GitAgent skill: draft_claim.py Drafts preliminary patent claims from detection r

### Community 7 - "MEMORY.md — InventionGuard"
Cohesion: 0.33
Nodes (5): Company-Specific Technical Domains, False Positive Patterns to Avoid, MEMORY.md — InventionGuard, Past Inventions Detected, Preferred Claim Drafting Style

### Community 9 - "SOUL.md — InventionGuard"
Cohesion: 0.50
Nodes (3): Constraints, Purpose, SOUL.md — InventionGuard

## Knowledge Gaps
- **16 isolated node(s):** `inventionguard`, `Past Inventions Detected`, `False Positive Patterns to Avoid`, `Company-Specific Technical Domains`, `Preferred Claim Drafting Style` (+11 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `scan()` connect `scan` to `detect_invention`, `notifier.py`, `prior_art.py`, `synthesizer.py`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **Why does `detect_invention()` connect `detect_invention` to `scan`, `synthesizer.py`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `search_prior_art()` connect `prior_art.py` to `scan`, `synthesizer.py`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `Path` (e.g. with `get_file_diff()` and `get_graphify_subgraph()`) actually correct?**
  _`Path` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `inventionguard`, `Past Inventions Detected`, `False Positive Patterns to Avoid` to the rest of the system?**
  _16 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `VectorClock` be split into smaller, more focused modules?**
  _Cohesion score 0.1437908496732026 - nodes in this community are weakly interconnected._