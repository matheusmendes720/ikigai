#!/usr/bin/env bash
# install_mmx.sh — Install MiniMax MMX-CLI (the vision tool medic uses).
#
# See: https://github.com/MiniMax-AI/skills/blob/main/skills/vision-analysis/SKILL.md
#
# Usage: scripts/install_mmx.sh
#
# Requires:
#   - curl (only for the wheel — pip handles the actual install)
#   - Python 3.8+ (mmx is distributed as a Python wheel)
#   - uv, pipx, or pip on PATH
#   - A MiniMax API key (set as MINIMAX_API_KEY in your env)
#
# After install, medic's vision pipeline (`medic vision critique`) will
# shell out to `mmx` automatically.

set -euo pipefail

if ! command -v pip >/dev/null 2>&1 && ! command -v pipx >/dev/null 2>&1 && ! command -v uv >/dev/null 2>&1; then
    echo "install_mmx: need pip, pipx, or uv on PATH" >&2
    exit 1
fi

if [ -z "${MINIMAX_API_KEY:-}" ]; then
    echo "install_mmx: MINIMAX_API_KEY is not set; mmx will not be usable until it is." >&2
    echo "  → export MINIMAX_API_KEY=… then re-run, or set it in your shell rc." >&2
fi

if command -v pipx >/dev/null 2>&1; then
    echo "→ installing mmx via pipx (isolated)"
    pipx install minimax-mmx-cli
elif command -v uv >/dev/null 2>&1; then
    echo "→ installing mmx via uv tool"
    uv tool install minimax-mmx-cli
else
    echo "→ installing mmx via pip (user)"
    pip install --user minimax-mmx-cli
fi

if command -v mmx >/dev/null 2>&1; then
    echo "✓ mmx installed at $(command -v mmx)"
    if [ -n "${MINIMAX_API_KEY:-}" ]; then
        mmx --version || true
        echo "✓ MINIMAX_API_KEY is set; medic vision is ready."
    else
        echo "⚠ mmx installed but MINIMAX_API_KEY is unset; calls will fail until you set it." >&2
    fi
else
    echo "⚠ mmx not on PATH yet — restart your shell or check your user bin dir" >&2
    exit 1
fi
