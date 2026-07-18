# OWASP-Aligned Security Review

**Date:** 2026-07-18
**Scope:** Ergane CLI, outbound integrations, GitHub Actions, dependencies, GitHub repository settings, and project-local skills.
**Method:** OWASP Top 10:2025 alignment, STRIDE data-flow review, Bandit, `pip-audit`, secret-pattern scan, workflow review, and GitHub settings verification.
**Confidence gate:** Comprehensive review; findings below are verified from code or repository configuration.

## Summary

| Severity | Open | Resolved in this review |
|---|---:|---:|
| Critical | 0 | 0 |
| High | 0 | 4 |
| Medium | 1 | 0 |
| Low | 1 | 0 |

## Resolved findings

### [HIGH] SR-001 — Checked-in config could redirect credential-bearing requests

- **Category:** OWASP A05 Security Misconfiguration / A10 Exceptional Conditions
- **Location:** `ergane/config.py`
- **Confidence:** 9/10

`.ergane.toml` was read from the repository and could override `openai_base_url`,
webhook settings, or private-repository consent when an internal pull request was
scanned with secrets. An attacker with pull-request write access could redirect
OpenAI or webhook traffic.

**Remediation:** repository config is now allowlisted to non-sensitive tuning
fields. Endpoints, credentials, and private-repository consent must come from
environment/operator configuration.

### [HIGH] SR-002 — CI could report success after a MyPy failure

- **Category:** OWASP A08 Software and Data Integrity Failures
- **Location:** `.github/workflows/ci.yml`
- **Confidence:** 10/10

The previous workflow used `mypy ... || true`, suppressing a failed type check.

**Remediation:** CI now fails closed on lint, type, test, and smoke-check errors.

### [HIGH] SR-003 — CI/CD used mutable GitHub Action tags

- **Category:** OWASP A03 Software Supply Chain Failures
- **Location:** `.github/workflows/*.yml`
- **Confidence:** 10/10

Workflow dependencies referenced mutable tags such as `@v4` and `@v5`.

**Remediation:** every third-party action is pinned to its immutable full commit
SHA. The repository also has locked Python dependencies, Dependabot configuration,
dependency review, CodeQL, and scheduled `pip-audit` checks.

### [HIGH] SR-004 — PR-controlled code could receive release credentials

- **Category:** OWASP A05 Security Misconfiguration / A08 Software and Data Integrity Failures
- **Location:** `.github/workflows/ergane.yml`
- **Confidence:** 10/10

The original pull-request job checked out and executed the pull-request version
of the CLI while exposing the OpenAI key and a pull-request-write token. A
malicious branch could modify executable code to exfiltrate those values.

**Remediation:** untrusted `pull_request` jobs now receive no application
secrets, use `persist-credentials: false`, and perform only a dry scan. A
separate `pull_request_target` job checks out the trusted base SHA, fetches the
PR head only as Git data, and runs the trusted CLI when privileged commenting
is required.

## Open findings

### [MEDIUM] SR-005 — Workflow artifacts can contain proprietary invention analysis

- **Category:** OWASP A02 Security Misconfiguration / STRIDE Information Disclosure
- **Location:** `.github/workflows/ergane.yml`
- **Confidence:** 8/10

`ergane-state.md` and the audit stream can contain commit identifiers, novelty
assessments, and claim drafts. They are uploaded as GitHub Actions artifacts.

**Impact:** anyone with artifact access can read the analysis.

**Mitigation in place:** artifacts have a 7-day retention period; private-repo
external processing is opt-in; secret values and response bodies are redacted from
state and audit records.

**Recommendation:** keep the workflow disabled for repositories whose IP policy
forbids GitHub Actions artifacts, or replace artifact persistence with an approved
encrypted system of record.

### [LOW] SR-006 — Direct API credentials remain operator-managed secrets

- **Category:** OWASP A04 Cryptographic Failures / A09 Logging and Alerting
- **Location:** GitHub Actions and local environment configuration
- **Confidence:** 8/10

Patent API, OpenAI, GitHub, and OpenClaw credentials are intentionally supplied
through environment variables. The code avoids committing or logging them, but
rotation, least privilege, and billing alerts are deployment responsibilities.

**Recommendation:** use GitHub environment-scoped secrets for production, rotate
keys periodically, and alert on unexpected OpenAI/API usage.

## Passed checks

- No committed credential pattern was found in tracked source or history-facing
  scan scope.
- No `eval`, `exec`, dynamic shell, unsafe YAML, pickle deserialization, raw SQL,
  or TLS-verification bypass was found in production code.
- Bandit reported only two false positives for empty credential defaults; no
  actionable Bandit finding remains.
- `pip-audit` found zero known vulnerabilities in the locked dependency set.
- All outbound HTTP clients have explicit timeouts. Failure paths now redact
  response bodies, URLs, and exception details before persistence.
- OpenAI synthesis uses schema-validated Structured Outputs with `store=False`.
- No `pull_request_target` trigger or interpolated pull-request body is used.
- GitHub repository secret scanning and push protection are enabled.

## STRIDE summary

| Component | Principal threat | Current control |
|---|---|---|
| CLI and local repository | Tampering | Git history is read-only; dry-run prevents external calls/state writes. |
| Patent/OpenAI APIs | Information disclosure | Explicit opt-in for private GitHub repos; fixed trusted endpoints; redacted failures. |
| GitHub PR comments | Tampering/replay | Per-commit hidden marker produces idempotent upserts. |
| OpenClaw webhook | Information disclosure | Token header, timeout, no response-body logging; endpoint remains operator-trusted. |
| State and audit records | Repudiation/disclosure | Append-only audit stream, idempotent state entries, short artifact retention. |
| CI/CD | Supply-chain compromise | SHA-pinned actions, `uv.lock`, CodeQL, dependency review, Dependabot, required checks. |

## Verification

`uv sync --locked --all-extras`, `pytest`, Ruff, and MyPy all pass locally. GitHub
will execute the protected CI and Security workflows when the hardening branch is
pushed and a pull request is opened.
