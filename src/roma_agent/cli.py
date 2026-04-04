from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .config import Settings
from .pipeline import RomaPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RomaAgent: idea to multi-platform article")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--idea", help="Your blog idea")
    group.add_argument("--idea-file", help="Path to UTF-8 text file containing large idea input")
    return parser.parse_args()


def main() -> None:
    _configure_io_encoding()
    args = parse_args()
    idea_text = _resolve_idea_text(args)
    settings = Settings.load()
    runtime = os.getenv("ROMA_AGENT_RUNTIME", "auto")
    pipeline = RomaPipeline(settings)
    result = pipeline.run(idea_text)

    console = Console()
    console.print(f"[cyan]Provider:[/cyan] {settings.provider} | [cyan]Runtime:[/cyan] {runtime} | [cyan]Model:[/cyan] {settings.model}")
    if settings.provider == "mock":
        console.print("[yellow]Warning:[/yellow] mock mode is active, output is placeholder content.")
    console.print(f"[green]Run completed:[/green] {result.run_id}")
    console.print(f"[cyan]Senate quality score:[/cyan] {result.senate_quality_score}")
    console.print(f"[cyan]Senate rework triggered:[/cyan] {result.senate_rework_triggered} | [cyan]Rounds:[/cyan] {result.senate_rework_rounds}")
    console.print(f"[cyan]Tribune issues:[/cyan] {len(result.tribune_issues)}")
    for issue in result.tribune_issues:
        console.print(f"  - {issue}")

    table = Table(title="Generated Platform Articles")
    table.add_column("Platform")
    table.add_column("Title")
    table.add_column("Deployment")
    deployment_map = {item.platform: item.output_path for item in result.deployment_records}
    for article in result.platform_articles:
        table.add_row(article.platform, article.title, deployment_map.get(article.platform, "n/a"))
    console.print(table)


def _configure_io_encoding() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
            except Exception:
                continue


def _resolve_idea_text(args: argparse.Namespace) -> str:
    if getattr(args, "idea", None):
        return args.idea
    idea_file = getattr(args, "idea_file", None)
    if not idea_file:
        raise ValueError("Either --idea or --idea-file is required.")
    path = Path(idea_file)
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    main()

