"""Typer CLI — entry point for the `audit` command."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..__init__ import __version__
from ..core.pipeline import Pipeline
from ..core.schema import Severity, SEVERITY_ORDER
from ..reporters import cli_reporter, json_reporter, html_reporter

app = typer.Typer(
    name="audit",
    help="Multi-engine code audit platform for Python / Django / React.",
    add_completion=False,
)

console = Console()
err_console = Console(stderr=True)


# ── scan ──────────────────────────────────────────────────────────────────────


@app.command()
def scan(
    path: Path = typer.Argument(Path("."), help="Directory to scan."),
    python_only: bool = typer.Option(False, "--python", help="Run Python/Django engines only."),
    frontend_only: bool = typer.Option(False, "--frontend", help="Run React/JS engines only."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write report to file."),
    fmt: str = typer.Option("cli", "--format", "-f", help="Output format: cli | json | html."),
    fail_on: Optional[str] = typer.Option(
        None, "--fail-on",
        help="Exit 1 if any issue at this severity or higher (critical|high|medium|low|info).",
    ),
    since_commit: Optional[str] = typer.Option(
        None, "--since-commit", help="Only report issues in files changed since this commit."
    ),
    no_cache: bool = typer.Option(False, "--no-cache", help="Skip the file-hash cache."),
    compact: bool = typer.Option(False, "--compact", help="Condensed CLI table (no snippets)."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """Run all applicable engines on PATH and report findings."""
    if verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)

    if not path.exists():
        err_console.print(f"[red]Error:[/red] Path not found: {path}")
        raise typer.Exit(2)

    pipeline = Pipeline(
        use_cache=not no_cache,
        since_commit=since_commit,
        python_only=python_only,
        frontend_only=frontend_only,
    )

    result = asyncio.run(pipeline.run(path))

    # Render
    fmt_lower = fmt.lower()
    if fmt_lower == "json":
        payload = json_reporter.render(result, path=output)
        if not output:
            print(payload)
    elif fmt_lower == "html":
        html = html_reporter.render(result, path=output)
        if not output:
            print(html)
        else:
            console.print(f"[green]Report written to[/green] {output}")
    else:
        cli_reporter.render(result, console=console, compact=compact)
        if output:
            # Also write JSON sidecar
            json_reporter.render(result, path=output)
            console.print(f"[dim]JSON written to {output}[/dim]")

    if result.errors:
        for err in result.errors:
            err_console.print(f"[yellow]Warning:[/yellow] {err}")

    # Exit code
    if fail_on:
        try:
            threshold = Severity(fail_on.lower())
        except ValueError:
            err_console.print(f"[red]Invalid --fail-on value:[/red] {fail_on}")
            raise typer.Exit(2)

        matching = [
            i for i in result.issues
            if SEVERITY_ORDER[i.severity] >= SEVERITY_ORDER[threshold]
            and i.duplicate_of is None
        ]
        if matching:
            raise typer.Exit(1)


# ── serve ─────────────────────────────────────────────────────────────────────


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", help="Bind host."),
    port: int = typer.Option(8888, "--port", "-p", help="Bind port."),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on file changes."),
) -> None:
    """Start the FastAPI scan server."""
    try:
        import uvicorn
        from ..api.main import create_app
        uvicorn.run(
            "auditor.api.main:app",
            host=host,
            port=port,
            reload=reload,
        )
    except ImportError:
        err_console.print("[red]uvicorn not installed.[/red] Run: pip install uvicorn")
        raise typer.Exit(1)


# ── version ───────────────────────────────────────────────────────────────────


@app.command()
def version() -> None:
    """Print the version and exit."""
    console.print(f"code-auditor {__version__}")


# ── entry point ───────────────────────────────────────────────────────────────


if __name__ == "__main__":
    app()
