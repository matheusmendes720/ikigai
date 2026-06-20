#!/bin/bash
set -e

printf "\n== Daily Review (#narrativa) ==\n"
task narrativa || true
task due:today list || true
task blocos || true
task completed end:today || true
task due:today summary || true
task due:tomorrow list || true
