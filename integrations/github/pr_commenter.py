"""Post a summary comment on a GitHub pull request after an audit run.

Reads the JSON report from $REPORT_PATH and posts / updates a comment
on the PR identified by $PR_NUMBER / $REPO.  Requires $GH_TOKEN.

Usage (from CI):
    python integrations/github/pr_commenter.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

_API = "https://api.github.com"
_MARKER = "<!-- code-auditor -->"


def _load_report(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _build_comment(report: dict) -> str:
    s = report.get("summary", {})
    total = s.get("total", 0)
    critical = s.get("critical", 0)
    high = s.get("high", 0)
    medium = s.get("medium", 0)
    low = s.get("low", 0)
    info = s.get("info", 0)
    duration = s.get("duration_seconds", 0)

    emoji = "🔴" if (critical + high) > 0 else ("🟡" if medium > 0 else "✅")

    lines = [
        _MARKER,
        f"## {emoji} Code Audit Results",
        "",
        f"| Severity | Count |",
        f"|----------|-------|",
        f"| 🔴 Critical | {critical} |",
        f"| 🟠 High     | {high} |",
        f"| 🟡 Medium   | {medium} |",
        f"| 🔵 Low      | {low} |",
        f"| ⚪ Info     | {info} |",
        f"| **Total**  | **{total}** |",
        "",
        f"_Scanned in {duration}s — scan `{report.get('scan_id', '')}` "
        f"• project: {', '.join(report.get('project_types', []))}_ ",
    ]

    # Top 5 high/critical issues
    top = [
        i for i in report.get("issues", [])
        if i.get("severity") in ("critical", "high")
    ][:5]
    if top:
        lines += ["", "### Top findings", ""]
        for issue in top:
            file = issue.get("file", "")
            line = f":{issue['line']}" if issue.get("line") else ""
            lines.append(
                f"- **{issue['severity'].upper()}** `{issue['rule_id']}` "
                f"— `{file}{line}` — {issue['message']}"
            )

    return "\n".join(lines)


def main() -> None:
    token = os.environ.get("GH_TOKEN")
    repo = os.environ.get("REPO")
    pr_number = os.environ.get("PR_NUMBER")
    report_path = os.environ.get("REPORT_PATH", "audit-report.json")

    if not all([token, repo, pr_number]):
        print("Missing GH_TOKEN, REPO, or PR_NUMBER — skipping comment.", file=sys.stderr)
        sys.exit(0)

    try:
        report = _load_report(report_path)
    except FileNotFoundError:
        print(f"Report not found at {report_path}", file=sys.stderr)
        sys.exit(1)

    body = _build_comment(report)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    with httpx.Client(timeout=30) as client:
        # Find existing comment to update
        comments_url = f"{_API}/repos/{repo}/issues/{pr_number}/comments"
        existing_id = None
        page = 1
        while True:
            resp = client.get(comments_url, headers=headers, params={"per_page": 100, "page": page})
            resp.raise_for_status()
            comments = resp.json()
            if not comments:
                break
            for c in comments:
                if _MARKER in c.get("body", ""):
                    existing_id = c["id"]
                    break
            if existing_id or len(comments) < 100:
                break
            page += 1

        if existing_id:
            resp = client.patch(
                f"{_API}/repos/{repo}/issues/comments/{existing_id}",
                headers=headers,
                json={"body": body},
            )
        else:
            resp = client.post(comments_url, headers=headers, json={"body": body})

        resp.raise_for_status()
        print(f"Comment {'updated' if existing_id else 'posted'} on PR #{pr_number}")


if __name__ == "__main__":
    main()
