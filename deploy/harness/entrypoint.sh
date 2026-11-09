#!/bin/sh
# The harness, at boot.
#
# Everything this script does is DERIVED. Nothing is written that the repo
# does not already publish, and nothing is written that a secret touches:
# the provider's key is resolved by pi FROM THE ENVIRONMENT at request time,
# so it never lands in a file, not even inside the container.
set -eu

HARNESS_HOME="${HARNESS_HOME:-/app/harness}"
PI_AGENT_DIR="${PI_AGENT_DIR:-/root/.pi/agent}"
PROJECT_DIR="${HARNESS_CWD:-/app}"
SKILLS_SRC="${HARNESS_ROUTINES_DIR:-/app/specs/harness/skills}"
SKILLS_DIR="${PI_SKILLS_DIR:-$PROJECT_DIR/.pi/skills}"

# ── 1. the routines ─────────────────────────────────────────────────────────
# The projection is the source; `.pi/skills/` is the copy `pi` loads
# (AGENTS.md: "the copy is regenerated from the projection"). Regenerating it
# at boot — instead of baking it into the image — is what makes the container
# and the repo the same thing: a change to a SKILL.md is a change to the
# routine, with no rebuild.
mkdir -p "$SKILLS_DIR"
rm -rf "${SKILLS_DIR:?}/"*
cp -R "$SKILLS_SRC/." "$SKILLS_DIR/"

# ── 2. the provider ─────────────────────────────────────────────────────────
# The model is not a property of this repository: it is an environment
# variable. The provider is a COMPATIBLE ENDPOINT (models.json), so the
# container talks to whatever the operator points it at — MiniMax, a proxy,
# a self-hosted gateway — without a rebuild and without a secret in the tree.
#
# The key is written as a COMMAND, not as a value and not as a variable name:
# pi's models.json resolves `!command` from the command's output, and this is
# the documented way to keep a secret out of the environment. The file is the
# compose secret, mounted at `/run/secrets/harness_provider_key`; the entry in
# the environment is gone, so `docker inspect` cannot print the key and no
# child process inherits it.
#
# `!command` is the documented form — `models.md`: "For an authenticated
# endpoint, `apiKey` … can use `$NAME` or `${NAME}` environment interpolation,
# a literal value, or a leading `!command`", and those commands run at request
# time. `!cat` and not `!tr -d '\n' < …`: the redirection assumes pi runs the
# command through a shell, and that assumption is NOT verified — while the
# credential was rejected (401 "invalid api key", on every header and both
# endpoints) no form could be distinguished. `!cat` needs no shell, so it is
# correct under either execution model.
#
# The cost of that choice is that the FILE must not end in a newline, since
# nothing strips it now: the compose comment and `.env.example` both say
# `printf '%s'`, never `echo`. A stray newline fails loudly at the next
# request (401), which is the one thing a silent key cannot do.
mkdir -p "$PI_AGENT_DIR"
cat > "$PI_AGENT_DIR/models.json" <<JSON
{
  "\$schema": "https://pi.dev/schemas/models.schema.json",
  "providers": {
    "${HARNESS_PROVIDER_ID:-harness}": {
      "baseUrl": "${HARNESS_PROVIDER_BASE_URL:?HARNESS_PROVIDER_BASE_URL is required}",
      "api": "${HARNESS_PROVIDER_API:-anthropic-messages}",
      "apiKey": "!cat ${HARNESS_PROVIDER_KEY_FILE:-/run/secrets/harness_provider_key}",
      "models": [
        {
          "id": "${HARNESS_MODEL_ID:?HARNESS_MODEL_ID is required}",
          "contextWindow": ${HARNESS_MODEL_CONTEXT_WINDOW:-204800},
          "maxTokens": ${HARNESS_MODEL_MAX_TOKENS:-131072}
        }
      ]
    }
  }
}
JSON

# ── 3. the store ────────────────────────────────────────────────────────────
# The harness reaches the store the way every other client does: through the
# api's MCP. It never opens the database, and it is not given a DSN.
mkdir -p "$PROJECT_DIR/.pi"
cat > "$PROJECT_DIR/.pi/mcp.json" <<JSON
{
  "mcpServers": {
    "ikigai": {
      "type": "http",
      "url": "${IKIGAI_MCP_URL:?IKIGAI_MCP_URL is required}",
      "description": "The ikigai store: the vault's artifacts, their relations, and the three ways to search them.",
      "exposure": "direct"
    }
  }
}
JSON

# ── 4. the door ─────────────────────────────────────────────────────────────
exec node "$HARNESS_HOME/server.mjs"
