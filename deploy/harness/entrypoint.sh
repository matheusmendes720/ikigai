#!/bin/sh
# The harness, at boot.
#
# Everything this script does is DERIVED. Nothing is written that the repo
# does not already publish, and nothing is written that a secret touches:
# the provider's key is resolved by pi FROM THE ENVIRONMENT at request time,
# so it never lands in a file, not even inside the container.
set -eu

HARNESS_HOME="${HARNESS_HOME:-/app/harness}"
# The AGENT's directory: where the agent keeps its settings, its sessions and
# its provider catalogue.
#
# `PI_CODING_AGENT_DIR` is the variable the agent itself reads (measured: with
# only `PI_AGENT_DIR` set, the agent started with "Unknown provider" — the
# catalogue was written somewhere the agent never looked). The old name is
# still honoured as a fallback, so a deployment that already sets it keeps
# working.
AGENT_DIR="${PI_CODING_AGENT_DIR:-${PI_AGENT_DIR:-/root/.pi/agent}}"
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
# The key is written as the LITERAL "$HARNESS_PROVIDER_API_KEY" on purpose:
# pi resolves that from the environment when it builds the request, so the
# key is never in a file.
mkdir -p "$AGENT_DIR"
cat > "$AGENT_DIR/models.json" <<JSON
{
  "\$schema": "https://pi.dev/schemas/models.schema.json",
  "providers": {
    "${HARNESS_PROVIDER_ID:-harness}": {
      "baseUrl": "${HARNESS_PROVIDER_BASE_URL:?HARNESS_PROVIDER_BASE_URL is required}",
      "api": "${HARNESS_PROVIDER_API:-anthropic-messages}",
      "apiKey": "\$HARNESS_PROVIDER_API_KEY",
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
