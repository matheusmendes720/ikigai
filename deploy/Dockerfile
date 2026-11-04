# syntax=docker/dockerfile:1
#
# The canonical service, as a container (ADR-037 D3/D6, renewed scope 2026-11-02).
#
# ONE image, THREE roles. The role is chosen by the command, not by three
# images: the api (MCP over HTTP) and the bot (Telegram) share the same
# contracts, the same store client and the same service layer, so they must
# not be allowed to drift apart in the build.
#
#   api → python -m src.transport.mcp_server
#   bot → python -m src.bot.main
#   db  → postgres:16 + pgvector (see compose.yml)
#
# The repository root is the workdir and is on PYTHONPATH: the canonical
# import style is the dotted prefix (`from src.contracts.dom import ...`),
# and the published `strategics` package lives at src/ikigai/src/strategics.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app:/app/src/ikigai/src

WORKDIR /app

# libpq for psycopg; curl for the healthcheck.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libpq5 curl \
 && rm -rf /var/lib/apt/lists/*

# Dependencies first, so a source change does not reinstall the world.
#
# `psycopg` and `psycopg-pool` are NOT yet declared in src/ikigai/pyproject.toml
# (the lock could not be regenerated in the environment where ADR-037 was
# written). They are installed here so the container works today; declaring
# them in the pyproject and running `poetry lock` is the follow-up, in the
# same change that adds them.
#
# `httpx` is installed explicitly because `src/bot/main.py` imports it
# directly — the Telegram client talks to api.telegram.org with it. It also
# arrives transitively through the MCP SDK, but a direct import deserves a
# direct dependency.
COPY src/ikigai/pyproject.toml src/ikigai/poetry.lock /tmp/ikigai/
RUN pip install --no-cache-dir poetry \
 && poetry config virtualenvs.create false \
 && poetry -C /tmp/ikigai install --only main --no-root \
 && pip install --no-cache-dir "psycopg[binary]>=3.2" "psycopg-pool>=3.2" "httpx>=0.27"

# The published surface. `vault/` is the prose input; the structured state
# lives in the store, not in these trees.
#
# `strategics/` is the other prose input — the PT-BR strategic documents the
# vault excerpt (`vault/_strategics_excerpt.md`) names as the full grounding.
# It is published, and the loader that reads `<root>/strategics/*.md` ships
# with the service. The vendored third-party fork beside it is NOT published
# and the .dockerignore keeps it out of the build context, so the image is
# the same on the owner's machine and on a fresh clone.
#
# A COPY of a path the branch does not publish fails the BUILD — the VPS, CI —
# with a message that says nothing about the cause. The drift net holds both
# ends: everything the image copies must be tracked, and the branch must
# publish the prose the image copies.
COPY src/ /app/src/
COPY vault/ /app/vault/
COPY strategics/ /app/strategics/
COPY specs/ /app/specs/
COPY code-docs/ /app/code-docs/
COPY pytest.ini /app/pytest.ini

# The container must not report healthy while the store is unreachable: the
# store IS the service (ADR-037 D4). The check measures the DATA PLANE — the
# store answers a query and the transport is listening — not the surface
# (contract C-2).
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD python -m src.transport.healthcheck || exit 1

CMD ["python", "-m", "src.transport.mcp_server"]
