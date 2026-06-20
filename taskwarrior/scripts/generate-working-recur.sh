#!/bin/bash
set -e

if [ "$#" -lt 3 ]; then
  echo "usage: $(basename "$0") <start-date:YYYY-MM-DD> <working-days> \"<description>\" [additional task args]"
  echo "example: $(basename "$0") 2026-01-06 15 \\\\\"Meta 15 dias uteis\\\\\" +revisao meta_ciclo:1"
  exit 1
fi

start="$1"
days="$2"
shift 2
desc="$1"
shift 1

SCRIPT_ROOT="$(cd "$(dirname "$0")" && pwd)"
due=$(python3 "$SCRIPT_ROOT/working-days.py" "$start" "$days")
task add due:"$due" "$desc" "$@"
