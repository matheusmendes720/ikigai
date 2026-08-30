#!/usr/bin/env bash
# Phase B6 Task 4 smoke test — vault-from-taskdog CLI
# Usage: bash tests/smoke/test_reverse_sync_vault_from_taskdog.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT"

# Create temp dir for test artifacts
TMPDIR=$(mktemp -d)

cleanup() {
    rm -rf "$TMPDIR"
}
trap cleanup EXIT

echo "=== Step 1: Verify CLI subcommand is registered ==="

# Simple import check - just verify the function is callable
if ! PYTHONPATH=src/ikigai/src python -c "
from ikigai.cli.app import sync_vault_from_taskdog
print('sync_vault_from_taskdog callable exists')
" 2>&1; then
    echo "ERROR: CLI subcommand 'sync_vault_from_taskdog' not registered"
    exit 1
fi
echo "✓ CLI subcommand registered"

echo ""
echo "=== Step 2: Verify reverse_sync() works on minimal fixture ==="

# Verify reverse_sync logic with a fake adapter
if ! PYTHONPATH=src/ikigai/src python -c "
import sys
from pathlib import Path
from ikigai.vault.sync import (
    ReverseSyncState, ReverseSyncTaskEntry, save_reverse_state, reverse_sync
)

state_path = Path('$TMPDIR/state.json')
save_reverse_state(state_path, ReverseSyncState(version=1, tasks={
    'task:a:abcdef01:12345678': ReverseSyncTaskEntry(
        last_seen_status='planned', last_seen_title='A', vault_path='plans/a.md'
    )
}))

class FakeAdapter:
    def list_all(self):
        return [{'ueid': 'task:a:abcdef01:12345678', 'name': 'A', 'status': 'done', 'priority': 1}]

result = reverse_sync(state_path=state_path, adapter=FakeAdapter(), source_fork='taskdog')
assert result.emitted == 1, f'expected 1 emitted, got {result.emitted}'
print('reverse_sync OK')
" 2>&1; then
    echo "ERROR: reverse_sync() logic failed"
    exit 1
fi
echo "✓ reverse_sync logic works"

echo ""
echo "=== Step 3: Verify CLI --dry-run flag ==="

# Check that the function has a dry_run parameter
if ! PYTHONPATH=src/ikigai/src python -c "
from ikigai.cli.app import sync_vault_from_taskdog
import inspect
sig = inspect.signature(sync_vault_from_taskdog)
assert 'dry_run' in sig.parameters, 'dry_run flag missing'
print('dry_run flag present')
" 2>&1; then
    echo "ERROR: --dry-run flag not present"
    exit 1
fi
echo "✓ --dry-run flag present"

echo ""
echo "=== Step 4: Verify CLI --help works ==="

# Verify the CLI help works
if ! PYTHONPATH=src/ikigai/src python -m ikigai.cli.app sync vault-from-taskdog --help 2>&1 | grep -q "review_queue"; then
    echo "ERROR: CLI help output missing expected content"
    exit 1
fi
echo "✓ CLI help works"

echo ""
echo "=== Smoke test PASSED ==="
