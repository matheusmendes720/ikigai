#!/bin/bash
set -e

# Backup — outdir = repo root (script lives at taskwarrior/scripts/)
SCRIPT_ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_ROOT/../.." && pwd)"
outdir="$REPO_ROOT"
file=backup-$(date +%Y%m%d_%H%M%S).json
task export > "$outdir/$file"
echo "Backup written: $outdir/$file"

# Helper recur templates
# Daily example: task add recur:daily due:today+1d "Daily task"
# Weekly example: task add recur:weekly due:next Monday "Weekly review"
# 15d example: task add recur:2w due:today+15d "Meta quinzenal"
# 5d micro example (manual): task add recur:5d due:today+5d "Microciclo"
