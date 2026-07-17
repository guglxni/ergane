"""Typer CLI — ergane scan, ergane analyze, ergane config."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel

from ergane.analyzer import (
    extract_claim_elements,
    extract_technical_problem,
    extract_technical_solution,
    get_commit_diffs,
)
from ergane.config import get_config
from ergane.notifier import format_pr_comment, post_pr_comment, send_openclaw_webhook
from ergane.patent_search import search_all
from ergane.scoring import ensemble_novelty
from ergane.state import append_invention, read_state
from ergane.synthesizer import synthesize

app = typer.Typer(help="Ergane — Patent intelligence for code commits")
console = Console()


def _print_result(result: dict, invention: Any) -> None:
    """Pretty-print detection results."""
    ns = result.get("novelty_score", 0.0)
    assessment = result.get("novelty_assessment", "UNKNOWN")
    color = "green" if assessment == "HIGH" else "yellow" if assessment == "MEDIUM" else "red"

    title = f"🧠 Ergane — {invention.commit_hash}"
    body = (
        f"[bold]Novelty Score:[/] [{color}]{ns}[/{color}]\n"
        f"[bold]Assessment:[/] [{color}]{assessment}[/{color}]\n"
        f"[bold]Recommendation:[/] {result.get('recommendation', 'UNKNOWN')}"
    )
    console.print(Panel(body, title=title, border_style=color))

    if result.get("closest_prior_art"):
        art = result["closest_prior_art"]
        console.print(
            f"[dim]Closest prior art:[/] {art.get('patent_number')} — {art.get('title')} ({art.get('source')})"
        )

    claim = result.get("draft_independent_claim", "")
    if claim and "DRY RUN" not in claim and "Error" not in claim:
        console.print(Panel(claim[:600], title="Draft Claim", border_style="blue"))


@app.command()
def scan(
    since: str = typer.Option("HEAD~1", help="Git ref to scan from"),
    to: str = typer.Option("HEAD", help="Git ref to scan to"),
    repo: Path = typer.Option(".", help="Path to git repository"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Skip LLM and API calls"),
    json_out: bool = typer.Option(False, "--json", help="Output raw JSON"),
    notify: bool = typer.Option(False, "--notify", help="Send notifications"),
    pr_number: int = typer.Option(0, "--pr", help="GitHub PR number for comment"),
    repo_slug: str = typer.Option("", "--repo-slug", help="GitHub repo slug (owner/repo)"),
) -> None:
    """Scan git commits for patentable technical inventions."""
    cfg = get_config()
    if dry_run:
        cfg.dry_run = True

    if not (repo / ".git").exists():
        console.print("[red]Error:[/] Not a git repository.")
        raise typer.Exit(1)

    console.print(f"[dim]Scanning {since}..{to} in {repo}...[/]")

    inventions = get_commit_diffs(repo, since, to)
    if not inventions:
        console.print("[yellow]No commits found in range.[/]")
        raise typer.Exit(0)

    results: list[dict] = []

    for inv in inventions:
        inv.technical_problem = extract_technical_problem(inv.commit_message + "\n" + inv.diff_text)
        inv.technical_solution = extract_technical_solution(inv.diff_text)
        inv.key_claim_elements = extract_claim_elements(inv.diff_text)

        console.print(f"\n[bold]Commit {inv.commit_hash}[/]: {inv.commit_message[:60]}")
        console.print(f"[dim]Files:[/] {', '.join(inv.files_changed[:5])}")

        query = f"{inv.technical_problem} {inv.technical_solution}"[:200]
        prior_art = search_all(query, cfg) if not cfg.dry_run else []

        if prior_art:
            console.print(f"[dim]Found {len(prior_art)} prior art records[/]")

        if not cfg.dry_run and cfg.has_openai and prior_art:
            scored = ensemble_novelty(inv, prior_art)
            synthesis = synthesize(
                inv, prior_art, api_key=cfg.openai_api_key,
                model=cfg.model, reasoning_effort=cfg.reasoning_effort,
                reasoning_mode=cfg.reasoning_mode, dry_run=cfg.dry_run,
            )
            result = {**scored, **synthesis}
        else:
            result = ensemble_novelty(inv, prior_art)

        results.append(result)
        _print_result(result, inv)

        if notify and not cfg.dry_run:
            comment = format_pr_comment(result, inv)
            if pr_number and repo_slug and cfg.github_token:
                r = post_pr_comment(repo_slug, pr_number, comment, cfg.github_token)
                status = r.get("html_url", "posted") if "_error" not in r else f"error: {r['_error']}"
                console.print(f"[dim]PR comment:[/] {status}")

            if cfg.openclaw_webhook_url:
                payload = {
                    "invention_title": inv.commit_message[:80],
                    "novelty_score": result.get("novelty_score", 0.0),
                    "risk_assessment": result.get("risk_assessment", "UNKNOWN"),
                    "commit_hash_short": inv.commit_hash,
                }
                r = send_openclaw_webhook(payload, cfg.openclaw_webhook_url, cfg.openclaw_hooks_token)
                status = f"{r}" if "_error" not in r else f"error: {r['_error']}"
                console.print(f"[dim]Webhook:[/] {status}")

        append_invention(repo, inv, result)

    if json_out:
        console.print(json.dumps(results, indent=2, default=str))

    console.print(
        f"\n[green]Scan complete.[/] {len(inventions)} commit(s) analyzed. "
        f"State written to .github/ergane-state.md"
    )


@app.command()
def analyze(
    repo: Path = typer.Option(".", help="Path to git repository"),
) -> None:
    """Show current ergane state and statistics."""
    state = read_state(repo)
    inventions = state.get("inventions", [])

    if not inventions:
        console.print("[yellow]No inventions recorded yet. Run `ergane scan` first.[/]")
        return

    from rich.table import Table
    table = Table(title="Ergane Invention Dashboard")
    table.add_column("ID", style="cyan")
    table.add_column("Date", style="dim")
    table.add_column("Commit", style="magenta")
    table.add_column("Novelty", style="green")
    table.add_column("Status", style="yellow")

    for inv in inventions:
        table.add_row(
            inv.get("id", "?"),
            inv.get("date", "?"),
            inv.get("commit", "?"),
            inv.get("novelty", "?"),
            inv.get("status", "?"),
        )

    console.print(table)
    console.print(f"\n[dim]Total inventions: {len(inventions)}[/]")


@app.command()
def config_show() -> None:
    """Display current Ergane configuration."""
    cfg = get_config()
    data = {
        "model": cfg.model,
        "fast_model": cfg.fast_model,
        "balanced_model": cfg.balanced_model,
        "novelty_threshold": cfg.novelty_threshold,
        "max_prior_art": cfg.max_prior_art,
        "has_openai": cfg.has_openai,
        "has_uspto": cfg.has_uspto,
        "has_epo": cfg.has_epo,
        "has_pqai": cfg.has_pqai,
        "dry_run": cfg.dry_run,
    }
    console.print(json.dumps(data, indent=2))


def main() -> None:
    app()
