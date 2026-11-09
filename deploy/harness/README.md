# The harness — the `pi` agent, in a container, with a SQLite memory

> The agent is EXTERNAL (ADR-037 D7). This directory is the deploy artefact
> that puts it in a container and gives it a door. `src/` never imports it,
> and the drift net does not see it.

## What it is

A small HTTP facade over the [`pi`](https://github.com/earendil-works/pi)
agent. `pi` speaks JSONL on its own stdin/stdout (its *RPC mode*); this
process owns that pipe and exposes it on a socket.

```text
  Telegram ──▶ bot ──▶ harness (this) ──▶ pi (RPC subprocess) ──▶ api
                   │                                        │
                   └──────── the report, as a message        │
                                                            ▼
                                                          store
```

The arrow that matters is the one coming back: **the harness reaches the
store through the api's MCP**, exactly like every other client. It never
opens the database and it is never given a DSN. The harness writes the DOM
through `store-write` and reads it through `store-read`; this facade is not
in that path.

**Who calls it:** the bot. The owner asks for a cadence from Telegram, the
bot asks the harness to run it, and the harness answers with the agent's
report — which the bot delivers as a second message. The api is NOT in the
middle: its surface is exactly six tools (ADR-011), and a seventh would make
the canonical service depend on the agent's availability and vocabulary,
which is what "the agent is external" forbids. The flow is linear, so there
is nothing to deadlock — the agent's write back into the api is an ordinary
MCP request.

## The three pieces

| Piece | File | What it is |
|---|---|---|
| The door | `server.mjs` | HTTP façade, session pool, routine runner |
| The memory | `memory.mjs` | SQLite: `entries`, `events`, `sessions` |
| The boot | `entrypoint.sh` | the projection → `.pi/skills/`, the provider, the MCP server |

## Why SQLite, and why not the store

The store (Postgres + pgvector) is the DOM — the product's state, its
revisions and its relations. SQLite here is the **agent's** state: what the
harness learned in a session, when, and what it did.

Two stores, two writers, two lifetimes:

- the store has **one** writer (`src/services/`), and the harness reaches it
  only through MCP;
- the SQLite database has **one** writer too: `memory.mjs`, inside this
  container.

There are **no vectors** here. The api embeds every write it accepts, so the
vector index belongs to the store and is served by MCP; a second index in the
harness would be a second answer to the same question, and the two would
drift. A stale row in SQLite costs a re-read, not a divergence.

## The routines

The whitelist is **the published projection**, read from disk:
`specs/harness/skills/<id>/SKILL.md`. A routine that is not there does not
run — the harness fails closed, the way the bot fails closed without
`IKIGAI_BOT_ALLOWED_CHAT_IDS`.

The container copies the projection into `.pi/skills/` at boot (not at build
time), so a change to a `SKILL.md` is a change to the routine with no
rebuild. The copy is regenerated; the projection is the source.

A routine is invoked with pi's **forced** skill form, `/skill:<id>` —
without it the model decides whether the description matches, and a routine
the owner asked for can come back "not quite applicable".

## The sessions

`pi` owns a conversation. Two Telegram chats are two conversations and cannot
share one context, so **one session id maps to one `pi` process**, pinned
with `--session-id`, and the process is persisted by the `harness-state`
volume — a session survives the container.

The session id has to survive two vocabularies: `pi` refuses an id that is
not alphanumerics, `-`, `_` and `.` (a chat key like `tg:9138296750` kills
the agent on the first prompt). So the id is sanitised once, on arrival, and
the same value is used for the agent and for the memory.

## The API

### `GET /v1/health` — shallow

Is this process alive and does the memory answer? Cheap; safe for a
heartbeat.

### `GET /v1/ready` — deep

Spawns a real `pi`, asks it for its state and checks that a **model** came
back. This is the data plane, not the surface: a socket that returns bytes
is not health (contract C-2). The container's `HEALTHCHECK` calls this.

### `GET /v1/routines`

The routines it found, with their sizes.

### `POST /v1/routine`

```json
{
  "routine": "daily-note",
  "session_id": "tg:9138296750",
  "chat_id": 9138296750,
  "message": "the owner's own words",
  "context": { "anything": "the caller may add" },
  "date": "2026-11-08",
  "timeout_ms": 600000
}
```

```json
{
  "ok": true,
  "routine": "daily-note",
  "session_id": "tg-9138296750",
  "text": "…",
  "bytes": 140,
  "events": 22,
  "memory_entry_id": 1,
  "duration_ms": 9446
}
```

The answer is written to the memory as an `entry`, and the run is logged as
two `events` (`routine.started`, `routine.finished`).

### `GET /v1/memory?session=…&kind=…&limit=…`

What the harness remembers. The session key is sanitised on the way in and
on the way out, so the caller may send the raw key it has.

## The environment

| Variable | Default | Meaning |
|---|---|---|
| `HARNESS_PORT` | `8002` | the door |
| `HARNESS_HOST` | `0.0.0.0` | the address |
| `HARNESS_CWD` | `/app` | pi's working directory (where `.pi/` lives) |
| `HARNESS_ROUTINES_DIR` | `/app/specs/harness/skills` | the projection = the whitelist |
| `HARNESS_MEMORY_DB` | `/app/memory/memory.sqlite` | the memory |
| `HARNESS_PROVIDER_ID` | `harness` | the provider's name |
| `HARNESS_PROVIDER_BASE_URL` | **required** | the endpoint |
| `HARNESS_PROVIDER_API` | `anthropic-messages` | the wire protocol |
| `HARNESS_MODEL_ID` | `MiniMax-M2.7` | the model |
| `HARNESS_MAX_SESSIONS` | `8` | how many `pi` processes may live |
| `HARNESS_SESSION_TTL_MS` | `900000` | idle eviction |
| `HARNESS_TIMEOUT_MS` | `600000` | the run's ceiling |
| `IKIGAI_MCP_URL` | **required** | the store's door |

**The key is a FILE, not an environment variable.** It used to be an
`environment:` entry, and an environment entry is not a secret store: the
engine keeps it in the container's `Config.Env`, so `docker inspect` prints it,
and in `/proc/1/environ`, so every process the agent spawns inherits it.
Measured on the box before the change: the 125-character key was one
`docker inspect` away from anyone allowed to run `docker` there.

It is now a compose secret, mounted at `/run/secrets/harness_provider_key`,
and the entrypoint gives the agent its **path**, not its value:

```json
"apiKey": "!cat /run/secrets/harness_provider_key"
```

`!command` is the documented form — `models.md`: *"`apiKey` … can use `$NAME` or
`${NAME}` environment interpolation, a literal value, or a leading
`!command`"*, and those commands run at request time. It is `!cat` and not a
`tr` with a redirect on purpose: a redirect assumes pi runs the command through
a shell, and that assumption is **not verified**, so the form that needs no
shell is the one that stays.

The cost is that the file must not end in a newline, because nothing strips it:
write it with `printf '%s'`, never `echo`. A stray newline fails loudly at the
next request (401), which is the one thing a silently wrong key cannot do.

Create it once, mode 600, outside the repository (`deploy/secrets/` is
gitignored):

```bash
mkdir -p deploy/secrets
install -m 600 /dev/null deploy/secrets/harness_provider_key
printf '%s' '<the key>' > deploy/secrets/harness_provider_key
```

The engine does not encrypt a file secret at rest, so the filesystem is what
protects it. What the change removes is the **copy**: nothing in `docker
inspect`, nothing in `/proc/*/environ`, nothing inherited by child processes.

## The volumes

| Volume | Mounted at | What survives |
|---|---|---|
| `harness-state` | `/root/.pi/agent` | the agent's settings and sessions |
| `harness-memory` | `/app/memory` | the SQLite memory |
| `vault/` | `/app/vault` (ro) | the prose — never written (ADR-012) |
| `strategics/` | `/app/strategics` (ro) | the conceptual material the routines ground on |

The two prose trees are mounted, not copied: the image carries the prose of
the commit it was built from, the mount carries the prose of now. A container
that only sees the baked copy answers from last week's memory while the vault
says otherwise.

The host's `~/.pi/agent` is **not** mounted. It carries ~300 skills the
product does not use and the owner's credentials.

## Run it

```bash
cd deploy
docker compose up -d --build harness
docker compose exec api python -m src.transport.healthcheck
curl -s http://127.0.0.1:8002/v1/ready | python -m json.tool
```

Without Docker, the facade runs as-is against a local `pi`:

```bash
cd deploy/harness && npm install
HARNESS_PORT=8002 \
HARNESS_CWD=<repo> \
PI_CLI_PATH=<pi>/dist/bundle/cli.js \
HARNESS_ROUTINES_DIR=<repo>/specs/harness/skills \
HARNESS_MEMORY_DB=/tmp/memory.sqlite \
node server.mjs
```

## Measured

On 2026-11-08, against the real `pi` 1.5.0 (`@earendil-works/pi-coding-agent`):

| Measure | Value |
|---|---|
| `/v1/ready` (spawns a `pi`, gets a model) | **763–882 ms** |
| a routine, end to end (`/skill:store-read`) | **9 446 ms** · 22 events · 140 B |
| the routines the projection holds | **7** |
| the commands the host's `pi` advertises | **307** — the container must not inherit them |
| the model | `MiniMax-M2.7` · provider `minimax` · context **204 800** |

Two failures were found and fixed by measuring, not by reading:

1. `--session-id` with a `:` kills the agent (`Session id must be …`) ⇒ the
   session id is sanitised on arrival;
2. `RpcClient` does **not** implement the `extension_ui` sub-protocol ⇒ the
   container runs `pi` with `--no-extensions` (the MCP client is core, so the
   store stays reachable).
