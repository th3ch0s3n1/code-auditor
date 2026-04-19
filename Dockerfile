FROM python:3.12-slim

# ── System dependencies ───────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        git \
        ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Node.js global tools ──────────────────────────────────────────────────────
RUN npm install -g \
        eslint@8 \
        eslint-plugin-react \
        eslint-plugin-security \
    && npm cache clean --force

# ── Python audit tools ────────────────────────────────────────────────────────
RUN pip install --no-cache-dir ruff bandit semgrep

# ── Application ───────────────────────────────────────────────────────────────
WORKDIR /app
COPY pyproject.toml ./
# README.md is optional (referenced by pyproject.toml) — copy only if present
COPY README.m[d] ./
COPY src/ ./src/
COPY config/ ./config/

RUN pip install --no-cache-dir -e ".[dev]"

# Smoke test
RUN audit version

# ── Runtime ───────────────────────────────────────────────────────────────────
# Mount the target project at /target when running:
#   docker run --rm -v /path/to/project:/target auditor audit scan /target

ENTRYPOINT ["audit"]
CMD ["--help"]
