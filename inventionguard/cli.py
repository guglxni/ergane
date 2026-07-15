"""InventionGuard CLI entry point."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from inventionguard import analyzer, detector, notifier, prior_art, synthesizer
from inventionguard.config import settings

app = typer.Typer(
    name="patentguard",
    help="InventionGuard — detect potential patentable inventions in code commits",
    no_args_is_help=True,
)
console = Console()


LEGAL_DISCLAIMER = (
    "[bold yellow]⚠️ DISCLAIMER:[/bold yellow] This tool identifies potential technical inventions. "
    "It does [bold]not[/bold] provide legal advice and does [bold]not[/bold] guarantee patentability. "
    "Always consult a qualified patent attorney before filing. AI cannot be a co-inventor."
)


@app.command()
def scan(
    since: Optional[str] = typer.Option("HEAD~1", "--since", help="Commit range start (git ref)"),
    to: Optional[str] = typer.Option("HEAD", "--to", help="Commit range end (git ref)"),
    repo_path: Optional[Path] = typer.Option(None, "--repo", help="Path to git repository (default: cwd)"),
    output_json: bool = typer.Option(False, "--json", help="Output raw JSON instead of rich UI"),
    skip_notify: bool = typer.Option(False, "--skip-notify", help="Skip OpenClaw/GBRAIN notifications"),
) -> None:
    """Scan git commits for potential patentable inventions."""
    console.print(Panel(LEGAL_DISCLAIMER, title="InventionGuard", border_style="red"))

    repo = repo_path or Path.cwd()
    diffs = analyzer.get_commit_diffs(str(repo), since, to)

    if not diffs:
        console.print("[yellow]No code changes detected in the specified range.[/yellow]")
        raise typer.Exit(0)

    results: list[dict] = []

    for diff_entry in diffs:
        commit_hash = diff_entry["commit_hash"]
        commit_message = diff_entry["commit_message"]
        files_changed = diff_entry["files_changed"]
        diff_text = diff_entry["diff_text"]

        console.print(f"\n[bold cyan]Analyzing commit {commit_hash[:8]}:[/bold cyan] {commit_message}")

        # Stage 1: Graphify subgraph
        subgraph = analyzer.get_graphify_subgraph(str(repo), files_changed)

        # Stage 2: Invention detection
        detection = detector.detect_invention(
            diff=diff_text,
            commit_message=commit_message,
            subgraph=subgraph,
            files_changed=files_changed,
        )

        if detection.get("skip") or detection.get("novelty_score", 0.0) < settings.novelty_threshold:
            console.print(f"  [dim]→ Novelty score {detection.get('novelty_score', 0):.2f} — skipping[/dim]")
            continue

        console.print(f"  [green]→ Detected invention (novelty {detection['novelty_score']:.2f})[/green]")

        # Stage 3: Prior art search
        prior = prior_art.search_prior_art(
            technical_problem=detection["technical_problem"],
            technical_solution=detection["technical_solution"],
            key_claim_elements=detection["key_claim_elements"],
        )

        # Stage 4: Synthesis
        synthesis = synthesizer.synthesize(
            detection=detection,
            prior_art_results=prior,
        )

        result = {
            "commit_hash": commit_hash,
            "commit_message": commit_message,
            "detection": detection,
            "prior_art": prior,
            "synthesis": synthesis,
        }
        results.append(result)

        if not output_json:
            _render_result(result)

        # Stage 5: Notify
        if not skip_notify:
            notifier.notify(result, repo_path=str(repo))
            notifier.store_in_gbrain(result)

    if output_json:
        console.print(json.dumps(results, indent=2, default=str))

    if results:
        console.print(f"\n[bold green]{len(results)} invention(s) detected.[/bold green]")
    else:
        console.print("\n[bold yellow]No patentable inventions detected in this range.[/bold yellow]")


@app.command()
def analyze(
    file: Path = typer.Option(..., "--file", help="Path to file to analyze"),
    repo_path: Optional[Path] = typer.Option(None, "--repo", help="Git repo path (default: cwd)"),
    output_json: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """Analyze a specific file for potential inventions."""
    console.print(Panel(LEGAL_DISCLAIMER, title="InventionGuard", border_style="red"))

    repo = repo_path or Path.cwd()
    diff_text = analyzer.get_file_diff(str(repo), str(file))
    files_changed = [str(file)]
    subgraph = analyzer.get_graphify_subgraph(str(repo), files_changed)

    detection = detector.detect_invention(
        diff=diff_text,
        commit_message=f"Manual analysis of {file}",
        subgraph=subgraph,
        files_changed=files_changed,
    )

    if output_json:
        console.print(json.dumps(detection, indent=2, default=str))
    else:
        table = Table(title="Invention Detection Result")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        table.add_row("Technical Problem", detection.get("technical_problem", "N/A"))
        table.add_row("Technical Solution", detection.get("technical_solution", "N/A"))
        table.add_row("Novelty Score", str(detection.get("novelty_score", 0)))
        table.add_row("Assessment", detection.get("novelty_assessment", "N/A"))
        table.add_row("Rationale", detection.get("rationale", "N/A"))
        console.print(table)


def _render_result(result: dict) -> None:
    detection = result["detection"]
    synthesis = result["synthesis"]

    table = Table(title=f"Invention: {detection.get('technical_problem', 'Unknown')[:60]}...")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Novelty Score", f"{detection['novelty_score']:.2f} ({detection['novelty_assessment']})")
    table.add_row("Risk Assessment", synthesis.get("risk_assessment", "N/A"))
    table.add_row("Similarity Score", f"{synthesis.get('overall_similarity_score', 0):.1f}%")
    table.add_row("Closest Patent", synthesis.get("closest_patent", {}).get("patent_number", "N/A"))
    table.add_row("Recommendation", synthesis.get("recommendation", "N/A"))
    console.print(table)

    if synthesis.get("draft_independent_claim"):
        console.print(Panel(synthesis["draft_independent_claim"], title="Draft Independent Claim", border_style="blue"))


if __name__ == "__main__":
    app()
