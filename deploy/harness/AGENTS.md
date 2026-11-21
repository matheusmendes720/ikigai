# deploy/harness — the external agent, behind a door

Score 16 — distinct domain: the `pi` harness facade. Node/ESM, its own image,
its own lifecycle; `src/` never imports it and the drift net does not see it.

## OVERVIEW
The agent (ADR-037 D7) as an HTTP facade over `pi`, with a SQLite memory: a
deploy artefact, not part of the canonical service.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| HTTP door | `server.mjs` | ~1.3k lines: routes, session pool, `pi` spawning, fallback-on-429 |
| Memory | `memory.mjs` | SQLite (`entries`/`events`/`sessions`/`questions`); `Memory`, `hashContent` |
| Runtime registry | `runtimes.mjs` | `buildRegistry`, `routeClient`, `readRegistryConfig`, `describeRuntime` |
| Owner questions | `owner.mjs`, `owner-mcp.mjs` | `Owner.ask/read/answer/pending`; the stdio MCP server with the `ask` tool |
| The ceiling | `ceiling.mjs` | `Ceiling`, `hitCeiling`, `killExpiredAgent` — the run's own clock |
| Stop / refusal | `stop.mjs`, `refusal.mjs` | `createStopSignal`, `requestStop`; 409 `sessionBusyRefusal` |
| Boot | `entrypoint.sh` | copies the routines projection into `.pi/skills/`, writes the provider |
| Image | `Dockerfile` | `node:24-bookworm-slim`; `npm ci --omit=dev --ignore-scripts` |
| Tests | `test/*.test.mjs` | `node --test`; `image.test.mjs` diffs the Dockerfile's COPY list |
| Contract in prose | `README.md` | the facade's API, env, volumes |

## API SURFACE
JSON under `/v1/*` — shape `{ok, routine, session_id, text, bytes, events,
memory_entry_id, duration_ms}`; errors carry `{ok:false, error, detail}`.

`GET /v1/health` (shallow) · `/v1/ready` (deep) · `/v1/routines` ·
`/v1/memory` · `/v1/runtimes` · `/v1/routing` · `/v1/session` · `/v1/events` ·
`POST /v1/routine` · `POST /v1/routine/cancel` · `POST /v1/owner/ask` ·
`GET|POST /v1/owner/answer`

## CONVENTIONS
- **ESM only**: `.mjs` extension, explicit `.mjs` in import specifiers,
  `node:`-prefixed builtins; `node:test` + `node:assert/strict`.
- **The agent is a PROTOCOL, not a library**: JSONL over stdin/stdout.
  `pi-coding-agent` is pinned at `1.5.0` (no `^`) — a protocol that moves
  under the agent's feet is one the container cannot rely on.
- **The provider is a compatible endpoint** (`models.json`), chosen by env;
  the key is read from a FILE at request time, never written into the
  environment.
- `PI_CODING_AGENT_DIR` is the variable the agent reads (the old
  `PI_AGENT_DIR` only coincided because `HOME=/root`).
- **The routines are regenerated at BOOT** from `specs/harness/skills/` into
  `.pi/skills/` — the projection is the source, the copy is runtime state.
- **The memory is SQLite, not the store**: the harness reaches the DOM only
  through the api's MCP.
- **The facade owns the ceiling.** The SDK timer only *rejects a promise*; it
  does not stop a process, so the harness kills the agent.
- `pi` always runs with `--session-id` (sanitised: `tg:` kills the agent) and
  `--no-extensions` (RpcClient has no `extension_ui` sub-protocol).

## ANTI-PATTERNS
- **NEVER** give the harness a DSN — it reaches the store only through the
  api's MCP.
- **NEVER** add a tool to the api's six-tool surface to serve owner
  questions — `owner-mcp.mjs` is a separate stdio server.
- **NEVER** add a module without copying it in `harness/Dockerfile`: the file
  list is copied one by one, so a missing module fails at boot, not at build.
  `test/image.test.mjs` guards exactly this.
- **NEVER** let the SDK timeout be the authority; **NEVER** write the provider
  key with `echo` (the newline breaks the header).
- **NEVER** mount the host's `~/.pi/agent`: it carries 300 skills the product
  does not use, and the owner's credentials.
- **ALWAYS** fail closed — an invalid routing-table entry is REFUSED with a
  reason, never a silent fallback that looks like success.

## COMMANDS
```bash
docker compose build harness && docker compose up -d harness
curl -s http://127.0.0.1:8002/v1/ready | python -m json.tool
node --test deploy/harness/test/
HARNESS_PORT=8002 HARNESS_CWD=<repo> PI_CLI_PATH=<pi>/dist/bundle/cli.js \
HARNESS_ROUTINES_DIR=<repo>/specs/harness/skills node server.mjs
```
