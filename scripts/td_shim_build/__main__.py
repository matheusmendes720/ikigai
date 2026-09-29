#!/usr/bin/env python3
"""td shim — minimal Python launcher for the life-oss taskdog CLI.

Hardcoded repo path (this machine only). For a portable shim, replace
REPO_ROOT with a search based on sys.argv[0]/sys.executable.

Build with:
    python -m zipapp . -o td.exe -p "C:\Python314\python.exe"
"""
import sys
from pathlib import Path
import os

REPO_ROOT = Path(r'C:\Users\mathe\code_space\life-oss\life')
if not (REPO_ROOT / 'src' / 'mesh' / 'taskdog_cli.py').exists():
    sys.stderr.write('error: life-oss repo not found at ' + str(REPO_ROOT) + '\n')
    sys.exit(2)

sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src" / "ikigai" / "src"))
from src.mesh.taskdog_cli import main

sys.exit(main(sys.argv[1:]))
