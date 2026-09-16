#!/usr/bin/env bash
# M38 — Double-fire detection for progress.md
# A TRUE double-fire = 2+ entries with the same task_id AND same minute timestamp
# (truncated to YYYY-MM-DDTHH:MM) AND timestamps within <2 seconds (true concurrent
# invocations). This excludes legitimate rapid-fire cron catchup dispatches
# (same task_id, same minute, ≥2 seconds apart, sequential scheduler behavior)
# and only catches true concurrent invocations.
#
# M38.1 (2026-09-16): added the ≥2-seconds-apart filter that M38 spec documented
# but detect-double-fire.sh didn't implement. Without this filter, every
# legitimate `loop-tick.sh --graph <key>` test run triggered a false-positive
# double-fire (the test invokes the graph multiple times in quick succession
# from the same task_id).
#
# Distinct from the known double-LOG artifact (Windows Cygwin errno 11
# causes two log lines per single tick — that is ONE entry in progress.md).
set -euo pipefail

PROGRESS="${1:-.claude/loop/progress.md}"

if [[ ! -f "$PROGRESS" ]]; then
  echo "ERROR: progress.md not found at $PROGRESS" >&2
  exit 2
fi

# Use python for reliable parsing (stdlib only)
python3 - "$PROGRESS" <<'"'"'PYEOF'"'"'
import sys
import re
from datetime import datetime, timezone
from collections import defaultdict

progress_path = sys.argv[1]

# Parse progress.md into list of (timestamp, task_id, verdict)
# Format: ## {ISO8601} | {task_id} | {verdict}
entries = []
task_id_re = re.compile(r"^##\s+(\S+)\s*\|\s*([^|]+?)\s*\|\s*(\S+)")

with open(progress_path, encoding="utf-8") as f:
    for line in f:
        m = task_id_re.match(line)
        if m:
            ts_str = m.group(1).replace("Z", "+00:00")
            task_id = m.group(2).strip()
            verdict = m.group(3)
            # Parse ISO timestamp (supports Z suffix and +00:00 offset)
            ts_str_norm = ts_str.replace("Z", "+00:00")
            try:
                ts = datetime.fromisoformat(ts_str_norm)
            except ValueError:
                # Fallback: try without timezone
                try:
                    ts = datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
            entries.append((ts, task_id, verdict))

# Group by (task_id, minute_key) where minute_key = timestamp truncated to YYYY-MM-DDTHH:MM
# A double-fire = 2+ entries with the same task_id AND same minute_key
by_task_minute = defaultdict(list)
for ts, task_id, verdict in entries:
    minute_key = ts.strftime("%Y-%m-%dT%H:%M")
    by_task_minute[(task_id, minute_key)].append((ts, verdict))

# Detect TRUE double-fires: same task_id within the same minute AND
# timestamps <2 seconds apart (true concurrent invocations).
# M38.1: filter out legitimate rapid-fire (≥2 seconds apart) per M38 spec.
double_fires = []
for (task_id, minute_key), ts_list in by_task_minute.items():
    if len(ts_list) < 2:
        continue
    ts_list.sort()
    first_ts, first_verdict = ts_list[0]
    last_ts, last_verdict = ts_list[-1]
    delta = (last_ts - first_ts).total_seconds()
    # M38.1: rapid-fire catchup (≥2s apart) is legitimate cron behavior
    if delta >= 2.0:
        continue
    double_fires.append({
        "task_id": task_id,
        "minute": minute_key,
        "count": len(ts_list),
        "first_ts": first_ts.isoformat(),
        "last_ts": last_ts.isoformat(),
        "delta_sec": delta,
        "verdicts": [v for _, v in ts_list],
    })

if double_fires:
    print(f"DOUBLE-FIRES DETECTED: {len(double_fires)}")
    for df in double_fires:
        print(f"  - {df['task_id']} @ {df['minute']}: "
              f"{df['count']} entries, span={df['delta_sec']:.0f}s, "
              f"verdicts={df['verdicts']}")
    sys.exit(1)

print(f"OK: no double-fires detected across {len(entries)} entries")
sys.exit(0)
PYEOF
