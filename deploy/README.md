# deploy/ — the service, as a container

One box, three containers, one compose (ADR-037, renewed scope 2026-11-02).

| Container | Image | Command | What it is |
|---|---|---|---|
| `db` | `pgvector/pgvector:pg16` | — | the store. The DOM lives in the `ikig` schema |
| `api` | built from `deploy/Dockerfile` | `python -m src.transport.mcp_server` | the MCP transport over HTTP. **The only writer** |
| `bot` | the SAME image | `python -m src.bot.main` | the Telegram client. A projection of the DOM, not a fork |

The api and the bot share the image on purpose: they share the contracts, the
store client and the service layer, so they must not be allowed to drift apart
in the build. The role is the **command**, not the build.

## The rules this compose encodes

- **One writer per store (ADR-037 D5).** Only the api holds a DSN. The bot
  speaks MCP to the api — it has no `IKIGAI_STORE_DSN`, because a fallback to
  the database would be a second writer waiting to happen.
- **The bot fails closed (contract C-4).** `IKIGAI_BOT_ALLOWED_CHAT_IDS` is
  required; an empty allowlist stops the bot at startup instead of turning it
  into a public write channel.
- **The healthcheck measures the data plane (contract C-2).** It checks that
  the store answers a query and that the transport is listening **on the
  address a client uses** — not that a socket returns bytes, and not that the
  server answered a connection to itself. `python -m src.transport.healthcheck`.
- **Secrets never live in the repo (contract C-5).** Every secret comes from
  the environment; the compose file names each required variable with a `:?`
  guard, so a missing one stops the stack with a readable message.

## The environment variables

| Variable | Required | Meaning |
|---|---|---|
| `IKIGAI_DB_NAME` | no (default `ikigai`) | the database name |
| `IKIGAI_DB_USER` | no (default `ikigai`) | the database user |
| `IKIGAI_DB_PASSWORD` | **yes** | the database password |
| `IKIGAI_MCP_TRANSPORT` | no (default `http`) | ADR-011: `http` for a deployment, `stdio` for the local harness |
| `IKIGAI_BOT_TOKEN` | **yes** | the Telegram bot token — belongs to the bot process only |
| `IKIGAI_BOT_ALLOWED_CHAT_IDS` | **yes** | comma-separated owner chat ids; empty stops the bot |
| `IKIGAI_CLIENT_ID` | no (default `owner`) | the identity written on every write — the claim the RLS policies filter on |

Put them in a `.env` file beside this one. `.env*` is gitignored; no secret
belongs in a tracked file.

## Running it

```bash
docker compose up -d --build
docker compose ps
docker compose exec api python -m src.transport.healthcheck
docker compose logs -f bot
```

## The migrations

The schema is applied by the canonical migration runner, not by the compose
file. The api container waits for the store to be healthy and then:

```bash
docker compose exec api python -m src.contracts.migrations.apply up
docker compose exec api python -m src.contracts.migrations.apply status
```

`up` is idempotent — it applies the versioned SQL in order and records the
schema version. `down --yes` rolls back one step. Never edit a migration that
has already run.

## What is NOT here, and why

- **No `TUI`, no web app, no cluster.** ADR-037 D1: no new product surface
  before the data layer serves, and the cluster is *projected, not built*
  (ADR-0036 — the trigger is not written yet).
- **No LLM SDK, no harness.** The agent is the harness (`pi`), and it is
  EXTERNAL (ADR-037 D7). The published tree imports no model SDK, and the
  drift net now enforces that.
