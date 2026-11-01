# ~/.openwiki/.env — OpenWiki local secrets (DO NOT COMMIT)
#
# This file is read by the OpenWiki CLI to configure model provider + LangSmith
# tracing. OpenWiki restricts this directory's permissions to the current user.
#
# To populate:
#   1. Copy this file to ~/.openwiki/.env
#   2. Replace each REPLACE_ME with the real value
#   3. `chmod 600 ~/.openwiki/.env` (Linux/macOS) or rely on Windows ACL
#
# Source for key names: https://github.com/langchain-ai/openwiki/blob/main/src/config/constants.ts
# AND the existing deepagents harness at life-ops/ikigai/src/agents/deepagents_harness.py

# -----------------------------------------------------------------------------
# Provider — Anthropic-compatible (matches existing deepagents_harness.py)
# -----------------------------------------------------------------------------
# The repo's deepagents harness already uses ChatAnthropic against the
# MiniMax Anthropic-compatible endpoint. OpenWiki supports the same path
# via provider=anthropic + ANTHROPIC_BASE_URL.
OPENWIKI_PROVIDER=anthropic

# Model id — the same MiniMax model the harness already calls.
OPENWIKI_MODEL_ID=MiniMax-M2.7-highspeed

# API key — order of precedence in OpenWiki:
#   1. ANTHROPIC_API_KEY
#   2. MINIMAX_API_KEY (custom, used by the existing harness)
# We keep both as fallbacks. Either is acceptable.
ANTHROPIC_API_KEY=REPLACE_ME_WITH_MINIMAX_OR_ANTHROPIC_KEY
# MINIMAX_API_KEY=REPLACE_ME_ALT

# Base URL — MiniMax Anthropic-compatible gateway.
ANTHROPIC_BASE_URL=https://api.minimax.io/anthropic

# Reasoning effort (optional). Leave unset for MiniMax M-series.
# OPENWIKI_REASONING_EFFORT=medium

# Max output tokens (default 16384 for anthropic).
# OPENWIKI_MAX_OUTPUT_TOKENS=16384

# -----------------------------------------------------------------------------
# LangSmith — required because the user asked for tracing on
# -----------------------------------------------------------------------------
# LangSmith OTEL ingest — public endpoint. Override for EU/APAC.
# LANGSMITH_OTEL_ENDPOINT=https://api.smith.langchain.com/api/v1/otel/v1/traces
# LANGSMITH_OTEL_ENDPOINT=https://eu.api.smith.langchain.com/api/v1/otel/v1/traces
# LANGSMITH_OTEL_ENDPOINT=https://apac.api.smith.langchain.com/api/v1/otel/v1/traces

LANGSMITH_TRACING=true
LANGSMITH_API_KEY=REPLACE_ME_WITH_LANGSMITH_KEY
LANGSMITH_PROJECT=algorithmic-life-os-openwiki
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_PROJECT=algorithmic-life-os-openwiki

# Langfuse (optional — the repo's OTel init wires both, but OpenWiki
# uses LangSmith as the primary backend; Langfuse is a secondary mirror
# configured inside the ikigai observability layer, not openwiki).
# LANGFUSE_PUBLIC_KEY=REPLACE_ME
# LANGFUSE_SECRET_KEY=REPLACE_ME
# LANGFUSE_HOST=https://cloud.langfuse.com

# -----------------------------------------------------------------------------
# Telemetry opt-out (recommended for production CI)
# -----------------------------------------------------------------------------
OPENWIKI_TELEMETRY_DISABLED=1
