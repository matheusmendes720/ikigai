#!/usr/bin/env bash
#
# THE CEILING PROBE — does a run that exceeds its ceiling KILL the agent it
# was running?
#
# This is a MEASUREMENT, not a test. It runs on the box, against the deployed
# harness, and it prints what it saw. The gate it backs is in
# `specs/harness/CHAINED-ROUTINES.md` §11 ("WHAT THE CEILING WAS MEASURED
# AGAINST").
#
# WHAT IT MEASURES, and ONLY that:
#   1. the run's answer (cancelled? failed? timed out?)
#   2. the LINE TEMPORAL of the agent process: baseline -> alive -> gone
#   3. the agent's LAST WRITE on the session file: it must stop at the ceiling
#      (the defect this probe was written for answered at the ceiling and kept
#      writing for three minutes)
#   4. the harness's events, and the pool's live_sessions back to baseline
#
# HOW TO RUN IT (from the box, with the stack up):
#
#   bash deploy/harness/probes/ceiling-timeline.sh
#
# The routine it runs is `store-read`, which only READS: a probe that wrote
# would change the store it is measuring.
#
# ── THE TWO WRONG NEEDLES, AND WHY THEY MATTER ─────────────────────────────────
#
# The first version looked for `--mode rpc` in `/proc/<pid>/cmdline` and
# **counted itself**: the probe's own source carried the literal in its argv,
# so the counter read 1 before the run, 1 during it and 1 after it — and
# proved nothing while looking like a measurement.
#
# The second version looked for `pi-coding-agent`, which is **never** in the
# cmdline: the agent rewrites its `process.title`, so `/proc/<pid>/cmdline`
# reads exactly `pi`.
#
# The needle that works is the agent's own title. It is assembled at runtime
# (`["p", "i"].join("")`) so this script's own argv never carries it, and the
# probe skips its own pid besides. A counter that counts itself is worse than
# no counter.
set -uo pipefail

HARNESS=${HARNESS:-http://127.0.0.1:8002}
SESSION=${SESSION:-ceiling-probe}
CEILING_MS=${CEILING_MS:-25000}
CONTAINER=${CONTAINER:-ikigai-harness-1}
ANSWER=${ANSWER:-/tmp/ceiling-answer.json}

# The agent's processes, read from inside the container with the container's
# own node (the container has node and no `ps`).
agents() {
  docker exec "$CONTAINER" node -e '
const fs = require("fs");
const needle = ["p", "i"].join("");
let agent = 0, mcp = 0;
const detail = [];
for (const pid of fs.readdirSync("/proc")) {
  if (!/^\d+$/.test(pid)) continue;
  if (Number(pid) === process.pid) continue;
  let cmd = "";
  try { cmd = fs.readFileSync(`/proc/${pid}/cmdline`, "utf8").replace(/\0/g, " ").trim(); } catch { continue; }
  if (cmd === needle) { agent += 1; detail.push("agent pid=" + pid); continue; }
  if (cmd.includes("owner-mcp")) { mcp += 1; detail.push("mcp pid=" + pid); }
}
console.log(JSON.stringify({ agent, mcp, detail }));
'
}

# The session file: size and mtime — WHEN did the agent last write?
session_stat() {
  docker exec "$CONTAINER" sh -c "stat -c '%s %Y' /root/.pi/agent/sessions/*_${SESSION}.jsonl 2>/dev/null | tail -1"
}

pool() {
  curl -s -m 10 "$HARNESS/v1/health" 2>/dev/null | head -c 400
}

echo "== clock (host): $(date -u +%H:%M:%SZ)"
echo "== baseline pool: $(pool)"
echo "== baseline agents: $(agents)"
echo "== baseline session file (size mtime): $(session_stat)"

START=$(date +%s%3N)
curl -s -m 180 -X POST "$HARNESS/v1/routine" \
  -H 'content-type: application/json' \
  -d "{\"routine\":\"store-read\",\"session_id\":\"$SESSION\",\"chat_id\":\"ceiling-probe\",\"message\":\"Prova de tecto: le o store com calma, pagina a pagina, sem resumir, ate ao fim.\",\"timeout_ms\":$CEILING_MS}" \
  -o "$ANSWER" -w 'http=%{http_code}\n' &
CURL=$!

# The line temporal. Each sample carries its OWN wall clock, because the
# sample itself takes time.
for i in $(seq 1 20); do
  sleep 2
  printf 't=%sms agents=%s session=(%s)\n' "$(($(date +%s%3N) - START))" "$(agents)" "$(session_stat)"
  kill -0 $CURL 2>/dev/null || break
done
wait $CURL
END=$(date +%s%3N)

echo "== elapsed_ms: $((END - START))  (the ceiling was ${CEILING_MS})"
echo "== answer: $(head -c 400 "$ANSWER" 2>/dev/null)"
echo "== agents right after the run: $(agents)"
echo "== session file at the ceiling: $(session_stat)"
sleep 5
echo "== agents 5s later: $(agents)"
echo "== session file 5s later: $(session_stat)"
echo "== pool after the run: $(pool)"

echo "== the harness's events for this session:"
curl -s -m 10 "$HARNESS/v1/events?session=$SESSION&limit=10" 2>/dev/null | head -c 1500
echo
