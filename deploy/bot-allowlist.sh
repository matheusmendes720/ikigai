#!/usr/bin/env bash
# bot-allowlist.sh — find the owner's Telegram chat id, and only the owner's.
#
#   ./bot-allowlist.sh            # who has messaged the bot? (read only)
#   ./bot-allowlist.sh --write    # write the FIRST candidate into the .env
#
# WHY THIS EXISTS: the bot refuses to start without an allowlist (contract
# C-4 — the bot is a write channel), and a chat id is not something that can
# be guessed or read out of a config. It comes from the owner talking to the
# bot. Telegram keeps the updates for 24 hours even when nobody is polling,
# so the message can be sent BEFORE the bot is running: it waits in the
# queue, and this script reads it out.
#
# The security boundary is the owner themselves: the chat id is only ever
# taken from an update the owner sent to this bot, and the script PRINTS what
# it found before anything is written. `--write` takes the FIRST candidate,
# so run it once, look at the printed number, and only then use it.
#
# A stranger who finds the bot and writes first would be the first candidate:
# that is why the script prints instead of writing by default, and why the
# owner should compare the printed id with their own before using --write.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${IKIGAI_ENV_FILE:-$SCRIPT_DIR/.env}"

env_get() {
  local key="$1" file="${2:-$ENV_FILE}"
  [ -f "$file" ] || return 1
  grep -m1 "^${key}=" "$file" | cut -d= -f2- | tr -d '\r' || true
}

TOKEN="${IKIGAI_BOT_TOKEN:-$(env_get IKIGAI_BOT_TOKEN || true)}"
[ -n "$TOKEN" ] || { echo "no IKIGAI_BOT_TOKEN in $ENV_FILE" >&2; exit 2; }

echo "### the bot"
curl -s --max-time 20 "https://api.telegram.org/bot${TOKEN}/getMe" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); r=d.get('result') or {}; print('@'+str(r.get('username')), '| id', r.get('id'), '|', r.get('first_name'))" \
  || { echo "the bot token did not answer" >&2; exit 3; }

echo
echo "### the pending updates (who has written to it)"
curl -s --max-time 20 "https://api.telegram.org/bot${TOKEN}/getUpdates" > /tmp/ikigai-updates.json
python3 - <<'PY'
import json
d = json.load(open('/tmp/ikigai-updates.json'))
if not d.get('ok'):
    print('API:', d.get('description')); raise SystemExit(1)
res = d.get('result', [])
print('updates:', len(res))
seen = []
for u in res:
    for k in ('message', 'edited_message', 'channel_post'):
        m = u.get(k)
        if not m:
            continue
        chat = m.get('chat') or {}
        if 'id' in chat:
            frm = m.get('from') or {}
            seen.append((chat['id'], chat.get('type'), frm.get('username'), frm.get('first_name'), m.get('text', '')[:40]))
for s in dict.fromkeys(seen):
    print(s)
if not seen:
    print("(nobody has written to it yet — the updates expire after 24h)")
PY

if [ "${1:-}" = "--write" ]; then
  CANDIDATE=$(python3 - <<'PY'
import json
d = json.load(open('/tmp/ikigai-updates.json'))
seen = []
for u in d.get('result', []):
    for k in ('message', 'edited_message', 'channel_post'):
        m = u.get(k)
        if m and (m.get('chat') or {}).get('id') is not None:
            seen.append(m['chat']['id'])
print(seen[0] if seen else '')
PY
)
  if [ -z "$CANDIDATE" ]; then
    echo "no candidate: nobody has written to the bot" >&2
    exit 4
  fi
  echo
  echo "writing IKIGAI_BOT_ALLOWED_CHAT_IDS=$CANDIDATE into $ENV_FILE"
  if grep -q '^IKIGAI_BOT_ALLOWED_CHAT_IDS=' "$ENV_FILE"; then
    sed -i "s/^IKIGAI_BOT_ALLOWED_CHAT_IDS=.*/IKIGAI_BOT_ALLOWED_CHAT_IDS=$CANDIDATE/" "$ENV_FILE"
  else
    printf 'IKIGAI_BOT_ALLOWED_CHAT_IDS=%s\n' "$CANDIDATE" >> "$ENV_FILE"
  fi
  echo "done — now: docker compose up -d bot"
else
  echo
  echo "(nothing was written. run with --write once you have compared the id above with your own)"
fi
