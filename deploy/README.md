# deploy/ — the service, as a container

One box, six containers, one compose (ADR-037, renewed scope 2026-11-02;
ADR-039 adds the websocket and the ingestion; ADR-037 D7 adds the agent).

| Container | Image | Command | What it is |
|---|---|---|---|
| `db` | `pgvector/pgvector:pg16` | — | the store. The DOM lives in the `ikig` schema |
| `api` | built from `deploy/Dockerfile` | `python -m src.transport.mcp_server` | the MCP transport over HTTP. **The only writer** |
| `ws` | the SAME image | `python -m src.transport.ws_server` | the websocket sync channel: the same six tools, plus the changes the store announces |
| `sync` | the SAME image | `python -m src.services.sync` | the ingestion: the vault prose into the store, and from there into the vector index |
| `bot` | the SAME image | `python -m src.bot.main` | the Telegram client. A projection of the DOM, not a fork |
| `harness` | built from `deploy/harness/Dockerfile` | `node server.mjs` | **the agent**: the `pi` harness, behind an HTTP door, with a SQLite memory. See [`harness/README.md`](./harness/README.md) |

All four of them run the same image on purpose: they share the contracts, the
store client and the service layer, so they must not be allowed to drift apart
in the build. The role is the **command**, not the build.

**The harness is the exception, and it is an exception on purpose.** The agent
is EXTERNAL (ADR-037 D7): it is a Node process, it is not part of the
canonical service, and putting it in the canonical image would put the model
runtime in every container of the product. It has its own image — and it
still reaches the store the way every other client does, through the api's
MCP. It is never given a DSN.

## The rules this compose encodes

- **One writer per store (ADR-037 D5).** Only the api, the ws and the sync
  hold a DSN — and all three go through the same service layer. The bot
  speaks MCP to the api — it has no `IKIGAI_STORE_DSN`, because a fallback to
  the database would be a second writer waiting to happen.
- **The bot fails closed (contract C-4).** `IKIGAI_BOT_ALLOWED_CHAT_IDS` is
  required; an empty allowlist stops the bot at startup instead of turning it
  into a public write channel.
- **The websocket fails closed too (ADR-039).** `IKIGAI_WS_TOKEN` is
  required: the channel is a write path, and a token is the only thing
  between "the bot" and "anyone who reached the network".
- **The healthcheck measures the data plane (contract C-2).** It checks that
  the store answers a query and that the transport is listening **on the
  address a client uses** — not that a socket returns bytes, and not that the
  server answered a connection to itself. `python -m src.transport.healthcheck`.
- **The vault is a volume, not a copy.** `../vault` is mounted read-only into
  the ingestion. The image carries the prose of the commit it was built from;
  the volume carries the prose of now. An ingestion that only saw the copy
  would answer from a stale memory while the vault says otherwise. The path is
  `../vault` and not `./vault`: a relative path in a compose file is resolved
  against the project directory — the directory of the compose file, which is
  `deploy/` — and `deploy/vault` is not in the repository. Docker would have
  created it empty, and the ingestion would have read nothing while looking
  healthy.
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
| `IKIGAI_WS_TOKEN` | **yes** | the token the websocket asks for — it is a write channel, so it fails closed |
| `IKIGAI_VAULT_SYNC_INTERVAL` | no (default `60`) | seconds between two ingestion runs |
| `IKIGAI_VAULT_ROOTS` | no | the trees the ingestion reads, `path=layout`, comma-separated |
| `IKIGAI_EMBEDDING_PROVIDER` | no (default `local`) | `local` (the hashing trick, no key) or `openai` (any compatible endpoint) |
| `IKIGAI_EMBEDDING_BASE_URL` | with `openai` | the endpoint, e.g. `https://api.openai.com/v1` |
| `IKIGAI_EMBEDDING_MODEL` | with `openai` | the model name |
| `IKIGAI_EMBEDDING_API_KEY` | no | the key; it never leaves the environment |
| `IKIGAI_IMAGE` | no | the image the stack runs; the CI/CD workflow sets it to the tag it published |
| `IKIGAI_BOT_TOKEN` | **yes** | the Telegram bot token — belongs to the bot process only |
| `IKIGAI_BOT_ALLOWED_CHAT_IDS` | **yes** | comma-separated owner chat ids; empty stops the bot |
| `IKIGAI_CLIENT_ID` | no (default `owner`) | the identity written on every write. It is written into the ROW; it is **not** the claim the RLS policies filter on — see below |
| `IKIGAI_PGDATA` | no (default `db-data`) | where the store's PGDATA lives. A **path** is a bind mount, a **name** is a Docker named volume |

## Where the store lives

The `db` service mounts `${IKIGAI_PGDATA:-db-data}` at `/var/lib/postgresql/data`. The
default is a Docker named volume, which is what a local checkout wants: portable,
disposable, and it never touches the root disk of a machine that has a real one.

On the deployment box, `IKIGAI_PGDATA` points at a directory on the Hetzner Cloud
Volume — the networked block device that outlives a rebuilt server — so the DOM
survives the server and the store's write path is a network device instead of the
root disk. Nothing else changes: the compose file does not know which one it is,
and the deploy workflow does not need to know where the server keeps its store.

Two things the deployment box has to get right, and the compose does not:

- **the volume's filesystem is `ext4`, mounted `noatime,nodelalloc` and without
  `discard`.** `discard` on a network volume is a round trip per freed block and
  the provider charges for the provisioned size, not the used one — so it is pure
  overhead with no benefit. `nodelalloc` keeps the `ENOSPC` from arriving at the
  `fsync` instead of at the `write`.
- **the store's `PGDATA` is a directory INSIDE the mount point**, never the mount
  point itself: the mount point belongs to `root`, and a cluster whose data
  directory is the mount point breaks on `pg_upgrade` and on a volume that goes
  offline.

And one thing that is not a filesystem question at all: **a Cloud Volume has no
snapshot and no backup.** A server backup does not include it. The store is the
DOM, and the DOM is not reproducible from the prose in `vault/` — `VaultSync`
reads the prose and never writes it back, so everything a client wrote exists
only in Postgres. The backup of the store is a separate thing, and it is not
optional.

Put them in a `.env` file beside this one. `.env*` is gitignored; no secret
belongs in a tracked file.

## Running it

```bash
docker compose up -d --build
docker compose ps
docker compose exec api python -m src.transport.healthcheck
docker compose exec ws python -m src.transport.healthcheck --host 0.0.0.0 --port 8001
docker compose logs -f bot
```

## The CI/CD — the image is built once and published

Two workflows, and the order matters.

**`ci.yml`** gates every pull request: the five-package matrix (ruff, mypy,
pytest) and a `container` job that resolves the compose file and BUILDS the
image. A compose file that no longer interpolates, or an image that no longer
builds, fails there — not on the server, at the deploy, with the service down.

**`deploy.yml`** runs on `main` and does three things:

1. builds the image on the runner and pushes it to GHCR
   (`ghcr.io/matheusmendes720/ikigai`), tagged with the commit SHA;
2. SSHes into the server;
3. pulls THAT image and runs it — `docker compose pull` then
   `docker compose up -d --no-build`.

The server never builds the image it runs. A server that builds on deploy
compiles the deploy, and a deploy that compiles something else than CI tested
is a deploy nobody verified.

The secrets it needs, all in the repository settings:

| Secret | Meaning |
|---|---|
| `IKIGAI_DEPLOY_HOST` | the server |
| `IKIGAI_DEPLOY_USER` | the user to log in as |
| `IKIGAI_DEPLOY_SSH_KEY` | the key |
| `IKIGAI_DEPLOY_PATH` | where the repository is checked out on the server |

The server keeps a clone of this repository at `IKIGAI_DEPLOY_PATH`; the
workflow fetches it, checks out `main` and pulls. The `.env` with the runtime
secrets lives on the server and never travels through CI.

The registry is **not** a secret of the workflow: a private package needs
`docker login ghcr.io` on the server, once, by hand. The deploy never carries
a token — a token in CI is a token that can leak from CI.

To deploy by hand, without the workflow:

```bash
IKIGAI_IMAGE=ghcr.io/matheusmendes720/ikigai:sha-<commit> docker compose pull
IKIGAI_IMAGE=ghcr.io/matheusmendes720/ikigai:sha-<commit> docker compose up -d --no-build
```

## The migrations

The schema is applied by the canonical migration runner — not by the compose
file, and not by hand. The api container runs it before it serves:

```bash
docker compose exec api python -m src.contracts.migrations.apply status
```

`up` is idempotent — it applies the versioned SQL in order and records the
schema version. `down --yes` rolls back one step. Never edit a migration that
has already run.

The api applies them at startup because a service that comes up without its
schema is a green lie: the healthcheck would pass (the store answers) while
every write failed. With the runner in the startup path, a broken schema is a
container that never comes up, and the bot — which waits for the api to be
healthy — never starts either.

## The role the service connects as — and why it matters

The DOM's tables carry row-level security: a row is visible only to the
client whose `client_id` matches the calling claim
(`request.jwt.claim.client_id`).

**The service never sets that claim.** It writes the `client_id` into the row
and leaves the claim alone. So the policies bind only a role that does NOT
own the tables — and the role that owns them bypasses row-level security
outright.

The compose runs the service as `ikigai`, which owns the tables. That is why
the store works today, and it is a **dependency, not a convenience**: with a
role that does not own them, the comparison is against NULL, nothing is
visible, and every write is refused by the policy's `with check`.

Two things follow, and both are enforced rather than assumed:

- the healthcheck **writes a row and rolls it back** instead of running
  `select 1`. A trivial query answers fine under a bound role — RLS does not
  apply to it — while every real write is refused, so `select 1` would have
  reported the container healthy while the store was unusable;
- `src/ikigai/tests/store/test_store_rls.py` proves the policies isolate clients, using
  a role they actually bind, and proves that the healthcheck's probe is
  refused by such a role.

**This is not a debt to be paid; it is the shape of a single-player store.**
The `client_id` is an audit label, not a boundary: the deployment is one
owner, and a second `client_id` is what would make the isolation real (then
the claim has to be set, and the role must stop owning the tables). The
decision and its trigger are in `specs/production-readiness/PRODUCT.md` §6 and
§7 — ADR-038 is where it is recorded.

If the deployment ever moves to a role that does not own the tables, the
service has to start setting the claim: `select set_config(RLS_CLIENT_CLAIM,
<client_id>, true)`, where `RLS_CLIENT_CLAIM` in `src/contracts/store.py` is
the single source of that setting's name — the policies in `0003_rls.sql` and
the drift test both derive from it. Until then, the role must own them.

The provider is the owner's own Postgres (see `PROVIDER` in the same module),
so which role the service connects as is a deployment choice, and the compose
makes it: `ikigai`, the owner. The constraint above is what that choice has
to keep satisfying.

## How the harness reaches the api

The harness is external (ADR-037 D7) and it reaches the store the way every
client does: over MCP, through the api. Pi reads the project's MCP servers
from `.pi/mcp.json`, and the api is declared there:

```json
{
  "mcpServers": {
    "ikigai": {
      "type": "http",
      "url": "http://127.0.0.1:8000/mcp",
      "description": "The ikigai store: the vault's artifacts, their relations, and the three ways to search them.",
      "exposure": "direct"
    }
  }
}
```

`exposure: direct` declares the six tools to the model itself, under the names
`mcp__ikigai__upsert_artifact` and the rest — the surface is small enough to
carry in the context, and the agent has to call the tools by name to do the
daily routines.

The api binds the loopback on purpose: the public surface is the Telegram
client and (later) a reverse proxy, not an open MCP port. A harness on the same
box reaches it there; one on another box reaches the reverse proxy.

**The harness carries the skills.** `specs/harness/skills/` is the published
projection of the routines — the part of the tree that says what a daily note
is. Pi loads the skills from the project's `.pi/skills/`, and the copy is
regenerated from the projection:

```bash
mkdir -p .pi/skills && cp -r specs/harness/skills/* .pi/skills/
```

The projection is the source; the copy is runtime state, so it is gitignored. A
drift test holds the two ends together: a copy that drifted from the
projection is a harness running a routine the repository no longer describes.

Pi reads the project configuration only after the project is trusted, so the
first run asks once. `pi mcp list` connects to every enabled server and
prints its state and its tools — it is the check that the wiring answers,
rather than a configuration that merely looks right.

**The proof.** From the repository root, with the api up:

```bash
pi mcp list                                    # the api is connected, with its six tools
pi -a --print "liste os KPIs do Q4-2026"       # the harness asks the store a question
```

`-a` trusts the project's configuration for that one command, which is what
makes the run scriptable. The verification is the EFFECT, not the format: the
answer comes from the store, and the store is what the api serves.

## What is NOT here, and why

- **No `TUI`, no web app, no cluster.** ADR-037 D1: no new product surface
  before the data layer serves, and the cluster is *projected, not built*
  (ADR-0036 — the trigger is not written yet).
- **No LLM SDK, no harness.** The agent is the harness (`pi`), and it is
  EXTERNAL (ADR-037 D7). The published tree imports no model SDK, and the
  drift net now enforces that.
