"""Rich CLI reporter — coloured tables and summary panel."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text

from ..core.schema import Issue, ScanResult, Severity, SEVERITY_COLORS


_SEVERITY_EMOJI = {
    Severity.CRITICAL: "🔴",
    Severity.HIGH: "🟠",
    Severity.MEDIUM: "🟡",
    Severity.LOW: "🔵",
    Severity.INFO: "⚪",
}


def render(result: ScanResult, console: Console | None = None, compact: bool = False) -> None:
    """Print a full scan report to the console."""
    c = console or Console()

    if not result.issues:
        c.print(Panel("[green]✔ No issues found[/green]", title="Audit complete"))
        _print_summary(c, result)
        return

    # Group issues by file
    by_file: dict[str, list[Issue]] = {}
    for issue in result.issues:
        by_file.setdefault(issue.file, []).append(issue)

    for file, issues in by_file.items():
        table = _build_table(file, issues, compact=compact)
        c.print(table)

    _print_summary(c, result)


# ── Internal helpers ──────────────────────────────────────────────────────────


def _build_table(file: str, issues: list[Issue], compact: bool) -> Table:
    title = f"[bold]{file}[/bold]  ({len(issues)} issue{'s' if len(issues) != 1 else ''})"
    table = Table(
        title=title,
        box=box.ROUNDED,
        show_lines=not compact,
        expand=False,
        title_justify="left",
    )

    table.add_column("Sev", width=8, no_wrap=True)
    table.add_column("Rule", width=14, no_wrap=True)
    table.add_column("Line", width=6, justify="right")
    table.add_column("Tool", width=10, no_wrap=True)
    table.add_column("Message")
    if not compact:
        table.add_column("Risk", width=6, justify="right")

    for issue in issues:
        color = SEVERITY_COLORS.get(issue.severity, "white")
        sev_text = Text(f"{_SEVERITY_EMOJI.get(issue.severity, '')} {issue.severity.value}", style=color)
        line_str = str(issue.line) if issue.line else "—"

        row = [sev_text, issue.rule_id, line_str, issue.tool, issue.message]
        if not compact:
            row.append(str(issue.risk_score))
        table.add_row(*row)

    return table


def _print_summary(c: Console, result: ScanResult) -> None:
    s = result.summary
    duration = f"{s.duration_seconds:.1f}s"

    lines = [
        f"[bold]Total[/bold]: {s.total}  "
        f"[bright_red]Critical: {s.critical}[/bright_red]  "
        f"[red]High: {s.high}[/red]  "
        f"[yellow]Medium: {s.medium}[/yellow]  "
        f"[cyan]Low: {s.low}[/cyan]  "
        f"[dim]Info: {s.info}[/dim]",
        f"[dim]Files: {s.files_scanned}  "
        f"Deduped: {s.duplicates_removed}  "
        f"Duration: {duration}  "
        f"Project: {', '.join(result.project_types) or 'unknown'}[/dim]",
    ]

    if result.errors:
        lines.append(f"[yellow]Errors: {len(result.errors)}[/yellow]")

    c.print(Panel("\n".join(lines), title=f"Scan {result.scan_id}"))
