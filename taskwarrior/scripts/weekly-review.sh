#!/bin/bash
set -e

printf "\n== Weekly Review (#relatorios) ==\n"
task relatorios || true
task modified.after:today-7d summary || true
task completed end.after:today-7d || true
task modified.after:today-7d export > week-tasks.json || true
echo "Exported week-tasks.json (workspace)"
