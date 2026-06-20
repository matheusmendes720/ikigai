#!/bin/bash
# Simple validation/logging (v2-style pass-through)
payload=$(cat)
echo "$(date -Is) on-add: $payload" >> ~/.task/hooks.log

# Example guard: if +revisao without meta_ciclo, warn (pass through)
if echo "$payload" | grep -q '"tags".*"revisao"' && ! echo "$payload" | grep -q '"meta_ciclo"'; then
  echo "WARNING: +revisao without meta_ciclo" >&2
fi

printf "%s" "$payload"
