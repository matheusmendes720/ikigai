# syntax=docker/dockerfile:1
#
# The harness, as a container (ADR-037 D7: the agent is EXTERNAL).
#
# This is a SECOND image on purpose. The canonical service (`deploy/Dockerfile`)
# is one Python image with five roles — db aside, the api, the websocket, the
# ingestion and the bot — because they share the contracts, the store client
# and the service layer, and must not be allowed to drift apart in the build.
# The agent is not one of them: it is an external process (`pi`), with its own
# runtime (Node), its own package and its own lifecycle. Putting it in the
# canonical image would put the model runtime in every container of the
# product, and would make the agent stop being external.
#
# The harness does NOT import the agent's package into the published tree.
# This directory is a deploy artefact: `src/` never imports it, and the drift
# net does not see it.
#
# The version is PINNED (`1.5.0`, no `^`). The harness talks a PROTOCOL to
# the agent — JSONL over stdin/stdout — and a protocol that moves under the
# agent's feet is a protocol the container cannot rely on.
#
#   docker compose build harness
#   docker compose up -d harness
FROM node:24-bookworm-slim

# git and ripgrep are the agent's tools: a routine that reads the vault and
# the strategics needs to search them.
RUN apt-get update \
 && apt-get install -y --no-install-recommends bash ca-certificates git ripgrep \
 && rm -rf /var/lib/apt/lists/*

# `PI_CODING_AGENT_DIR` is the AGENT's own variable: measured, the agent
# reads its directory from it, and from `~/.pi/agent` when it is unset. The
# image used to declare `PI_AGENT_DIR`, which the agent does NOT read — the
# two only coincided because HOME was /root and the default is `~/.pi/agent`.
# An operator who moved `PI_AGENT_DIR` moved the provider catalogue away
# from the agent, and every routine failed with "Unknown provider".
ENV NODE_ENV=production \
    PI_CODING_AGENT_DIR=/root/.pi/agent \
    PI_SESSION_DIR=/root/.pi/agent/sessions \
    PI_CLI_PATH=/app/harness/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js \
    HARNESS_HOME=/app/harness \
    HARNESS_CWD=/app \
    HARNESS_PORT=8002 \
    HARNESS_HOST=0.0.0.0 \
    HARNESS_MEMORY_DB=/app/memory/memory.sqlite \
    HARNESS_ROUTINES_DIR=/app/specs/harness/skills \
    PI_SKILLS_DIR=/app/.pi/skills

WORKDIR /app/harness

# Dependencies first: a change to the facade must not reinstall the agent.
# `npm ci` and not `npm install`: the lock is what makes the container the same
# container on the owner's machine and on a fresh clone, and what lets the CI
# say "the agent is the version we said it was".
COPY deploy/harness/package.json deploy/harness/package-lock.json /app/harness/
RUN npm ci --omit=dev --ignore-scripts

# The facade: the HTTP door, the session pool and the SQLite memory.
COPY deploy/harness/server.mjs /app/harness/server.mjs
COPY deploy/harness/memory.mjs /app/harness/memory.mjs
COPY deploy/harness/entrypoint.sh /app/harness/entrypoint.sh
RUN chmod +x /app/harness/entrypoint.sh

# The ROUTINES: the published projection. `specs/harness/skills/<id>/SKILL.md`
# is the source; the entrypoint copies it to `.pi/skills/`, which is what `pi`
# loads. Copying a path the branch does not publish fails the BUILD with a
# message that says nothing about the cause — so this path is tracked, and the
# drift net holds both ends.
COPY specs/harness/skills/ /app/specs/harness/skills/

# The vault and the strategics are MOUNTED, not copied: the image carries the
# prose of the commit it was built from, and the mount carries the prose of
# NOW. A container that only sees the baked copy answers from last week's
# memory while the vault says otherwise.
RUN mkdir -p /app/vault /app/strategics /app/memory

# The agent's own directory: settings, credentials and sessions. A named
# volume, so a session survives the container. The host's `~/.pi/agent` is NOT
# mounted: it carries 300 skills the product does not use, and the owner's
# credentials.
VOLUME ["/root/.pi/agent", "/app/memory"]

# The healthcheck measures the DATA PLANE (contract C-2): a socket that
# returns bytes is not health. `/v1/ready` spawns a `pi`, asks it for its
# state and checks that a model came back — which is what running a routine
# needs. The shallow probe is `/v1/health`.
HEALTHCHECK --interval=60s --timeout=45s --start-period=30s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:8002/v1/ready').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

ENTRYPOINT ["/app/harness/entrypoint.sh"]
