#!/usr/bin/env bash
# seed_test_repo.sh — create a tiny throwaway repo to exercise medic end-to-end.
#
# Usage:  scripts/seed_test_repo.sh /tmp/medic-demo
set -euo pipefail
DEST="${1:-/tmp/medic-demo}"

rm -rf "$DEST"
mkdir -p "$DEST"/{src,tests/golden/frames}
cd "$DEST"
git init -q -b main
git config user.email "medic@example.com"
git config user.name  "medic demo"

cat > pyproject.toml <<'EOF'
[project]
name = "medic-demo"
version = "0.1.0"
EOF

cat > src/calc.py <<'EOF'
# TODO: write tests
# FIXME: this is a hack
import os
PATH = "/usr/local/bin"   # hardcoded path — should be flagged

def add(a, b):
    return a + b

def divide(a, b):
    if b == 0:
        pass
    return a / b

def long_function():
    # 100+ lines of trivial logic — should be flagged as too long
    x = 1; y = 2; z = 3; n = 4; m = 5
    print("debug x =", x)
    print("debug y =", y)
    print("debug z =", z)
    print("debug n =", n)
    print("debug m =", m)
EOF

cat > tests/test_calc.py <<'EOF'
from src.calc import add

def test_add():
    assert add(1, 2) == 3
EOF

git add -A
git commit -q -m "feat: initial calculator"

# Add a "feature branch" PR worth
git checkout -q -b feat/big-refactor
echo "" >> src/calc.py
cat >> src/calc.py <<'EOF'


def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b


def another_long_one():
    x = 11; y = 22; z = 33; n = 44; m = 55
    x = 11; y = 22; z = 33; n = 44; m = 55
    x = 11; y = 22; z = 33; n = 44; m = 55
    print("x", x, "y", y, "z", z)
EOF
git add -A
git commit -q -m "feat: add subtract / multiply / another_long_one (no description)"

echo
echo "demo repo at $DEST"
echo "try:  medic health --target $DEST"
echo "      medic patterns --target $DEST/src --family code"
echo "      medic patterns --target $DEST --family workflow"
