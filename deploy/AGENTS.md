# deploy — the deployment artefact

Score 15 — distinct domain: the container contract. Everything here is a
deploy artefact; `src/` never imports it and the drift net does not see it.

## OVERVIEW
One Python image (many roles), a second Node image for the external agent,
the compose that wires them, and the host-side scripts that back up, publish
and probe.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| The stack | `compose.yml` | 7 services: db, api, ws, sync, write, bot, harness · 2 file secrets · 5 volumes |
| Canonical image | `Dockerfile` | `python:3.11-slim`; role = command, not build; `--only main` deps |
| Agent image | `harness/Dockerfile` | `node:24-bookworm-slim`; a SECOND image on purpose (ADR-037 D7) |
| The contract in prose | `README.md` | env vars, RLS role, migrations, CI/CD — its table predates the `write` service |
| Routing table | `runtimes.json` | client → runtime; mounted ro at `/etc/ikigai/runtimes.json` |
| Published surfaces | `surfaces.json` | Tailscale funnel surfaces; `state` pending/published |
| Backup / restore | `backup.sh`, `restore.sh` | cron `30 4 * * *`; `restore.sh --list --snapshot <id> --logical\|--physical` |
| Surfaces / allowlist | `apply-surfaces.sh`, `bot-allowlist.sh` | applies `surfaces.json` to `tailscale serve`; prints before it writes |
| Probes | `probes/night-arrow.sh`, `probes/vault-arrow.sh` | exit non-zero when a fact is false |

## CONVENTIONS
- **One image, many roles.** `api`/`ws`/`sync`/`write`/`bot` share
  `Dockerfile`; only `harness` has its own image, because the agent is
  external and its runtime must not leak into the product.
- **The compose is policy in comments.** Each block states *why*, often with a
  measured citation ("Measured on the box (2026-11-xx)").
- **Required config uses `${VAR:?message}`** so compose refuses to boot rather
  than boot misconfigured; optional config uses `${VAR:-default}`.
- **Secrets are file secrets** under `/run/secrets` (mode 600, gitignored),
  written with `printf '%s'` — never `echo`: the trailing newline breaks the
  Authorization header. `docker inspect` prints `Config.Env`, which is why
  keys are files.
- **`.env` is read, never sourced** (`env_get` greps `KEY=`). Bash scripts:
  `set -euo pipefail`, `SCRIPT_DIR` from `BASH_SOURCE`, `sudo -n`, ISO
  timestamps on stdout.
- **Image tags are immutable**: `sha-<commit>` only. Local default
  `ikigai:local` / `ikigai-harness:local`.
- **The healthcheck measures the data plane** (C-2), not the surface. A worker
  that serves no surface (`sync`, `write`) declares `--store-only` instead of
  inheriting the transport check — it would report unhealthy forever.
- **The vault is a volume, not a copy**: mounted read-only. `vault-escrita` is
  the only read-write mount in the deployment.

## ANTI-PATTERNS
- **NEVER** give the bot or the harness a DSN — a fallback to the database is
  "a second writer waiting to happen" (ADR-037 D5). Only `api`, `ws`, `sync`,
  `write` hold `IKIGAI_STORE_DSN`.
- **NEVER** let a container report healthy while the store is unreachable.
- **NEVER** `docker compose pull` (GHCR refuses the manifest HEAD) — pull tags
  by name. **NEVER** let the deploy server build the image it runs.
- **NEVER** `tailscale funnel --bg <port>` without `--https` (it hijacks the
  443 host); **NEVER** `tailscale funnel reset` (wipes the shared serve
  config); never publish a surface `surfaces.json` does not declare.
- **NEVER** set `POSTGRES_INITDB_ARGS` — without `search_path` the container
  exits 1 and restarts forever. Every table is `ikig.`-qualified.
- **NEVER** edit a migration that has already run.
- **DO NOT TOUCH** the Postgres durability settings block in `compose.yml`.
- **NEVER** write to `vault/` from code — `/app/vault` and `/app/zonas` are
  read-only everywhere.

## COMMANDS
```bash
docker compose up -d --build
docker compose exec api python -m src.transport.healthcheck
docker compose exec sync python -m src.transport.healthcheck --store-only
docker compose exec api python -m src.contracts.migrations.apply status
bash probes/night-arrow.sh          # exits non-zero when a fact is false
```
