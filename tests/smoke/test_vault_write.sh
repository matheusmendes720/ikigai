#!/usr/bin/env bash
# Smoke: vault_write MCP tool wiring + safety properties
# Usage: bash tests/smoke/test_vault_write.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

echo "=== Step 1: Verify vault_write function is importable via PYTHONPATH=. ==="
PYTHONPATH=. python -c "
from src.ikigai.src.ikigai.vault.vault_write import vault_write
print('vault_write callable OK')
"

echo ""
echo "=== Step 2: Verify @MCP.tool(name=\"vault_write\") decorator in server.py ==="
grep -q '@MCP.tool' src/ikigai/src/mcp_server/server.py \
    && grep -q 'name="vault_write"' src/ikigai/src/mcp_server/server.py \
    && echo 'vault_write tool wired via @MCP.tool OK' \
    || (echo 'vault_write NOT wired'; exit 1)

echo ""
echo "=== Step 3: Verify path traversal rejection (absolute path raises ValueError) ==="
PYTHONPATH=. python -c "
from pathlib import Path
from src.ikigai.src.ikigai.vault.vault_write import vault_write

try:
    vault_write(
        vault_root=Path('.'),
        vault_path='/etc/passwd.md',  # absolute path
        frontmatter_fields={'x': 1},
        body='bad',
    )
    print('FAIL: absolute path not blocked')
    exit(1)
except ValueError as e:
    print(f'Absolute path blocked: {e}')
"

echo ""
echo "=== Step 4: Verify atomic no .tmp leftover ==="
TMPDIR=$(mktemp -d)
PYTHONPATH=. python -c "
from pathlib import Path
from src.ikigai.src.ikigai.vault.vault_write import vault_write

vault_root = Path('$TMPDIR/vault')
vault_root.mkdir(parents=True)
vault_write(
    vault_root=vault_root,
    vault_path='test.md',
    frontmatter_fields={'ueid': 'task:t:abc:def', 'title': 'Test', 'status': 'planned'},
    body='# Test',
)
# Check no .tmp files left behind
import glob as g
tmp_files = g.glob(str(vault_root / '*.tmp'))
if tmp_files:
    print(f'FAIL: leftover .tmp files: {tmp_files}')
    exit(1)
else:
    print('No .tmp leftover OK')
"
rm -rf "$TMPDIR"

echo ""
echo "=== Smoke test PASSED ==="
