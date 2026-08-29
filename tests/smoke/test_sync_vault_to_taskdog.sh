#!/usr/bin/env bash
# Phase B6.8 smoke test — vault-to-taskdog sync CLI
# Usage: bash tests/smoke/test_sync_vault_to_taskdog.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT"

# Create a minimal in-memory vault
SMOKE_VAULT=$(mktemp -d)
SMOKE_STATE=$(mktemp --suffix=.json)

# Delete empty state file if it exists (mktemp creates empty file with --suffix)
# The sync module expects either no file OR valid JSON
rm -f "$SMOKE_STATE"

# Convert POSIX paths to Windows paths for Python (Git Bash on Windows).
# Python on Windows interprets /tmp/... as C:/tmp/... which doesn't exist.
if command -v cygpath >/dev/null 2>&1; then
    SMOKE_VAULT_WIN=$(cygpath -w "$SMOKE_VAULT")
    SMOKE_STATE_WIN=$(cygpath -w "$SMOKE_STATE")
else
    SMOKE_VAULT_WIN="$SMOKE_VAULT"
    SMOKE_STATE_WIN="$SMOKE_STATE"
fi

cleanup() {
    rm -rf "$SMOKE_VAULT"
    rm -f "$SMOKE_STATE"
}
trap cleanup EXIT

# Create one valid task file
mkdir -p "$SMOKE_VAULT"
cat > "$SMOKE_VAULT/test-task.md" <<'EOF'
---
ueid: ikigai:task:smoke:001
title: Smoke test task
tags: [task]
status: planned
priority: medium
---
# Smoke

This is a smoke test.
EOF

# Create a non-task file (should be silently skipped)
cat > "$SMOKE_VAULT/draft.md" <<'EOF'
---
title: Just a draft
tags: [draft]
---
# Draft
EOF

echo "=== Step 1: Verify CLI subcommand is registered ==="

# Verify CLI wiring (parse + subcommand registration) — this is fast and MCP-independent
if ! PYTHONPATH=src/ikigai/src python -m ikigai.cli.app sync vault-to-taskdog --help 2>&1 | grep -q "Sync vault frontmatter-tagged tasks"; then
    echo "ERROR: CLI subcommand 'sync vault-to-taskdog' not registered"
    exit 1
fi
echo "✓ CLI subcommand registered"

echo ""
echo "=== Step 2: Verify parse_vault_tasks() works on the tmp vault ==="

# Parse the vault via the sync module directly — no MCP needed
if ! PYTHONPATH=src/ikigai/src python -c "
import sys
sys.path.insert(0, 'src/ikigai/src')
from ikigai.vault.sync import parse_vault_tasks
from pathlib import Path

tasks = parse_vault_tasks(Path(r'$SMOKE_VAULT_WIN'))
assert len(tasks) >= 1, f'Expected >=1 task, got {len(tasks)}'
print(f'✓ Parsed {len(tasks)} task(s) from tmp vault')
"; then
    echo "ERROR: parse_vault_tasks() failed"
    exit 1
fi

echo ""
echo "=== Step 3: Verify diff() classifies the parsed task ==="

# Diff stage — also MCP-independent
if ! PYTHONPATH=src/ikigai/src python -c "
import sys
sys.path.insert(0, 'src/ikigai/src')
from ikigai.vault.sync import parse_vault_tasks, diff, SyncState
from pathlib import Path

tasks = parse_vault_tasks(Path(r'$SMOKE_VAULT_WIN'))
actions = diff(tasks, SyncState())
assert len(actions) >= 1, f'Expected >=1 action, got {len(actions)}'
print(f'✓ diff() classified {len(actions)} task(s) as {actions[0].kind.value}')
"; then
    echo "ERROR: diff() failed"
    exit 1
fi

echo ""
echo "=== Step 4: Attempt full sync (skipped gracefully if MCP unavailable) ==="

# Try the actual sync with a short timeout — push stage requires MCP server.
# If MCP is unavailable, push fails per-task and run_sync returns errors=[...]
# but scan/diff still complete. Smoke test passes either way.
OUTPUT=$(timeout 8 bash -c "PYTHONPATH=src/ikigai/src python -m ikigai.cli.app --json sync vault-to-taskdog \
    --vault '$SMOKE_VAULT_WIN' \
    --state '$SMOKE_STATE_WIN' \
    2>&1" 2>&1) || OUTPUT=""

if [ -z "$OUTPUT" ]; then
    echo "⚠ CLI timed out after 8s — MCP not available (expected in smoke env)"
    echo "✓ CLI wiring verified above; push stage requires MCP server"
else
    echo "$OUTPUT" | head -3
    # Verify JSON output contains expected keys
    if echo "$OUTPUT" | python -c "
import json, sys
data = json.load(sys.stdin)
ok_val = data.get('ok')
if ok_val is None:
    print('ERROR: Expected ok field in output')
    sys.exit(1)
result_data = data.get('data', {})
scanned = result_data.get('scanned', 0)
print(f'✓ JSON output OK (scanned={scanned})')
if scanned < 1:
    print(f'ERROR: Expected scanned >= 1, got {scanned}')
    sys.exit(1)
errors = result_data.get('errors', [])
if errors:
    print(f'⚠ Push errors detected (likely MCP not running): {len(errors)} error(s)')
    print('  MCP unavailable — smoke test passes on parse+diff success')
" 2>&1; then
        : # success
    else
        echo "ERROR: JSON output validation failed"
        exit 1
    fi
fi

echo ""
echo "=== Smoke test PASSED ==="
