# code-auditor

A lightweight, professional-grade code audit platform for Python / Django / React projects.
Runs **Ruff**, **Bandit**, **Semgrep**, **ESLint**, and **npm audit** in parallel,
normalises all output into a unified schema, deduplicates cross-tool findings, and
enriches them with risk scores and actionable suggestions.

---

## Quick start (Docker)

```bash
# Scan a local project
docker run --rm -v /path/to/your/project:/target ghcr.io/your-org/code-auditor:latest \
    scan /target --format html --output /target/audit-report.html

# or via docker-compose
TARGET_PATH=/path/to/your/project docker-compose run --rm auditor
```

## CLI usage

```bash
# Scan current directory (CLI table output)
audit scan .

# Scan and write JSON report, fail on high/critical
audit scan /path/to/project --format json --output report.json --fail-on high

# HTML report
audit scan . --format html --output report.html

# Only Python engines
audit scan . --python

# Only React/JS engines
audit scan . --frontend

# Incremental: only report issues in files changed since a commit
audit scan . --since-commit main

# Start the FastAPI server
audit serve --port 8000
```

## Output formats

| Format | Description |
|--------|-------------|
| `cli`  | Rich colour tables in the terminal (default) |
| `json` | Structured `ScanResult` JSON |
| `html` | Self-contained, sortable, filterable HTML page |

## Engines

| Engine  | Tool      | Language     | Notes                          |
|---------|-----------|--------------|--------------------------------|
| python  | Ruff      | Python       | Style, correctness, security   |
| python  | Bandit    | Python       | Security (SAST)                |
| django  | Semgrep   | Python       | Custom Django security rules   |
| react   | ESLint    | JS / JSX     | React + security rules         |
| dep     | npm audit | JS packages  | Known CVEs in dependencies     |

## Severity → risk score

| Severity | Base score | Security boost | Auth-file boost | Test-file penalty |
|----------|-----------|----------------|-----------------|-------------------|
| CRITICAL | 90        | +15            | +10             | −10               |
| HIGH     | 70        | +15            | +10             | −10               |
| MEDIUM   | 40        | +15            | +10             | −10               |
| LOW      | 15        | +15            | +10             | −10               |
| INFO     | 5         | +15            | +10             | −10               |

## Project structure

```
src/auditor/
  cli/main.py          # Typer CLI
  core/
    schema.py          # Issue, ScanResult, ScanSummary
    raw.py             # RawFinding (internal)
    detector.py        # Project type detection
    runner.py          # Async subprocess runner
    normalizer.py      # RawFinding → Issue
    deduplicator.py    # Exact + semantic dedup
    enricher.py        # Risk score + tags + suggestions
    cache.py           # File hash cache
    pipeline.py        # Orchestration
  engines/             # One module per tool
  parsers/             # JSON output parsers
  reporters/           # cli | json | html
  api/                 # FastAPI (audit serve)
config/
  semgrep/             # Custom Django Semgrep rules
  eslint/              # ESLint config
  ruff.toml
integrations/
  github/              # GitHub Actions + PR commenter
  gitlab/
tests/
  fixtures/            # Sample projects with seeded issues
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## CI integration

### GitHub Actions
See [integrations/github/action.yml](integrations/github/action.yml).

### GitLab CI
See [integrations/gitlab/.gitlab-ci.yml](integrations/gitlab/.gitlab-ci.yml).
