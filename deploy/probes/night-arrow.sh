#!/usr/bin/env bash
# night-arrow.sh — the probe that measures ONE night of the cadence, end to end.
#
# It runs on the VPS, from the host, against the running stack. It measures ONE
# night — the cadence's night — and EIGHT facts, and each one is a fact that can
# be false:
#
#   1. the cadence fired ITSELF: a routine.started in the cadence hour whose
#      agent turn is the skill invocation and NOTHING else (no human sentence)
#   2. the run FINISHED: a routine.finished after it, and no failure between
#   3. the note LANDED: a live `nota` artifact, written that day, by the agent
#   4. the arrow: the file's sha256 == the store's body_hash
#   5. the authorship: +1 revision by `vault-write`, ZERO by `vault-sync`
#   6. the ingestion wrote NOTHING: created=0 updated=0
#   7. the writer has NO backlog: every live artifact has a vault_path
#   8. the delivery is WIRED: the Syncthing folder that watches the tree is in
#      sync (needFiles 0, errors 0)
#
# It EXITS NON-ZERO when a fact is false. A probe that only prints is a report,
# and a report does not keep anybody honest.
#
# Usage:  bash deploy/probes/night-arrow.sh [YYYY-MM-DD]
#
# Without an argument it measures the day named by the LAST daily-note run in
# the harness ledger. With one, it measures that day.
#
# It never prints a secret: the Syncthing API key is read on the box and used
# as a header, and it is not echoed.

set -u

DB_CONTAINER="${DB_CONTAINER:-ikigai-db-1}"
HARNESS_CONTAINER="${HARNESS_CONTAINER:-ikigai-harness-1}"
WRITE_CONTAINER="${WRITE_CONTAINER:-ikigai-write-1}"
SYNC_CONTAINER="${SYNC_CONTAINER:-ikigai-sync-1}"
TREE="${TREE:-/mnt/volume-fsn1-1/vault-escrita}"
SYNCTHING_CONFIG="${SYNCTHING_CONFIG:-/var/lib/syncthing/config.xml}"
SYNCTHING_FOLDER="${SYNCTHING_FOLDER:-notas-escrita}"
SYNCTHING_URL="${SYNCTHING_URL:-http://localhost:8384}"
# The directory the agent's session files live in, INSIDE the harness container.
# It is passed with -e on purpose: `docker exec` does not inherit the host's
# environment, and a probe whose falsification cannot be driven is a probe
# whose power is unknown.
SESSION_DIR="${SESSION_DIR:-}"
DAY="${1:-}"

failures=0

say() { printf '%s\n' "$*"; }
ok() { printf 'OK    %s\n' "$*"; }
bad() { printf 'FALHA %s\n' "$*"; failures=$((failures + 1)); }

q() { docker exec "$DB_CONTAINER" psql -U ikigai -d ikigai -t -A -F'|' -c "$1"; }

say "=== night-arrow: a noite do ciclo, medida (UTC $(date -u +%Y-%m-%dT%H:%M:%SZ)) ==="

# --- o ledger e a sessao do agente ------------------------------------------
# The JS is written to a file and copied into the container: the harness has
# node and node:sqlite, and nothing else.
tmp_js="$(mktemp /tmp/night-arrow-XXXXXX.js)"
cat >"$tmp_js" <<'JSEOF'
const { DatabaseSync } = require('node:sqlite');
const fs = require('node:fs');
const path = require('node:path');

const wanted = process.argv[2] || null;
const db = new DatabaseSync('/app/memory/memory.sqlite', { readOnly: true });

const events = db
  .prepare("select seq, ts, kind, key, session, payload from events where kind like 'routine.%' order by seq")
  .all();

const parse = (e) => {
  try { return JSON.parse(e.payload || '{}'); } catch { return {}; }
};

const starts = events.filter((e) => e.kind === 'routine.started' && e.key === 'daily-note');

// Without an argument, the day is the one named by the LAST run.
const lastStart = starts[starts.length - 1];
const day = wanted || (lastStart ? parse(lastStart).date : null);

const out = { day, run: null, turn: null };

if (day) {
  const candidates = starts.filter((e) => parse(e).date === day);
  const start = candidates[candidates.length - 1] || null;
  out.run = { found: false };
  if (start) {
    const after = events.filter((e) => e.seq > start.seq);
    const finish = after.find((e) => e.kind === 'routine.finished' && e.key === 'daily-note') || null;
    const failures = after.filter(
      (e) => e.seq <= (finish ? finish.seq : Number.MAX_SAFE_INTEGER) &&
        (e.kind === 'routine.failed' || e.kind === 'routine.timed_out')
    );
    out.run = {
      found: true,
      session: start.session,
      started_ts: start.ts,
      started_iso: new Date(start.ts).toISOString(),
      started_payload: parse(start),
      finished: finish ? { seq: finish.seq, ts: finish.ts, iso: new Date(finish.ts).toISOString(), payload: parse(finish) } : null,
      failures: failures.map((e) => ({ kind: e.kind, ts: e.ts })),
      duration_ms: finish ? finish.ts - start.ts : null,
    };

    // THE HUMAN FACT: the agent's own turn. A human message would be a
    // sentence in front of the skill invocation. The turn must be the skill
    // invocation and the session context — nothing else.
    const dir = process.env.SESSION_DIR || '/root/.pi/agent/sessions';
    let file = null;
    if (fs.existsSync(dir)) {
      const all = fs
        .readdirSync(dir)
        .filter((f) => f.endsWith('.jsonl'))
        .map((f) => path.join(dir, f))
        .filter((f) => fs.statSync(f).size > 0);
      // The session file that carries THIS run is the one named after the
      // session of the started event; the newest file is only the fallback.
      const named = all.filter((f) => f.endsWith('_' + start.session + '.jsonl'));
      file = (named.length ? named : all).sort(
        (a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs
      )[0] || null;
      out.turn_file = file;
    }
    if (file) {
      const lines = fs.readFileSync(file, 'utf8').split('\n');
      const turns = [];
      for (const line of lines) {
        if (!line.trim()) continue;
        let d;
        try { d = JSON.parse(line); } catch { continue; }
        if (d.type !== 'message') continue;
        const m = d.message || {};
        if (m.role !== 'user') continue;
        let content = m.content || '';
        if (Array.isArray(content)) {
          content = content.map((c) => (c && c.text) || '').join(' ');
        }
        turns.push({ ts: d.timestamp || '', text: String(content) });
      }
      const from = new Date(start.ts).getTime();
      const to = finish ? finish.ts : from + 30 * 60 * 1000;
      const inWindow = turns.filter((t) => {
        const ts = Date.parse(t.ts);
        return ts >= from - 5000 && ts <= to + 5000;
      });
      let human = null;
      let skillOnly = false;
      let contextDate = null;
      if (inWindow.length > 0) {
        const turn = inWindow[0];
        const text = turn.text;
        const firstLine = text.split('\n')[0].trim();
        const rest = text.slice(text.indexOf('\n') + 1);
        const open = rest.indexOf('{');
        const close = rest.lastIndexOf('}');
        let outside = null;
        let ctx = null;
        if (open >= 0 && close > open) {
          outside = (rest.slice(0, open) + rest.slice(close + 1)).trim();
          try { ctx = JSON.parse(rest.slice(open, close + 1)); } catch { ctx = null; }
        }
        skillOnly = firstLine.startsWith('/skill:') && outside !== null && outside === 'Contexto da sessao (JSON):';
        contextDate = ctx ? ctx.date : null;
        human = text;
        out.turn = {
          ts: turn.ts,
          first_line: firstLine,
          skill_only: skillOnly,
          outside_context: outside,
          context_date: contextDate,
          context: ctx,
          raw: human.slice(0, 800),
        };
      }
    }
  }
}

process.stdout.write(JSON.stringify(out));
JSEOF

docker cp "$tmp_js" "$HARNESS_CONTAINER":/tmp/night-arrow.js >/dev/null
LEDGER="$(docker exec -e SESSION_DIR="$SESSION_DIR" "$HARNESS_CONTAINER" node /tmp/night-arrow.js "$DAY")"
docker exec "$HARNESS_CONTAINER" rm -f /tmp/night-arrow.js
rm -f "$tmp_js"

DAY_MEASURED="$(printf '%s' "$LEDGER" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("day") or "")')"
say "a noite medida: ${DAY_MEASURED:-NENHUMA}"

if [ -z "$DAY_MEASURED" ]; then
  bad "o ledger nao nomeou nenhuma noite (nenhum run de daily-note)"
fi

# --- 1. a cadencia disparou sozinha ----------------------------------------
say ""
say "--- 1. a cadencia disparou sozinha ---"
if [ -n "$DAY_MEASURED" ]; then
  TURN="$(printf '%s' "$LEDGER" | python3 -c '
import json,sys
d=json.load(sys.stdin)
r=d.get("run") or {}
t=d.get("turn") or {}
started=r.get("started_iso","")
print("|".join([
  started,
  str(t.get("skill_only")).lower(),
  str(t.get("context_date") or ""),
  str(t.get("first_line") or ""),
  str(r.get("session") or ""),
  str(r.get("started_payload",{}).get("client") or ""),
]))' )"
  IFS='|' read -r started_iso skill_only context_date first_line session client <<<"$TURN"

  if [ "$skill_only" = "true" ] && [ "$context_date" = "$DAY_MEASURED" ]; then
    ok "o turno do agente foi so a invocacao do skill ('$first_line') com date=$context_date — sem frase humana"
  else
    bad "o turno do agente nao foi so o skill (skill_only=$skill_only, date=$context_date)"
  fi
  if [ -n "$started_iso" ]; then
    ok "a corrida comecou as $started_iso, sessao $session, cliente $client"
  else
    bad "a corrida da noite nao esta no ledger"
  fi
  case "$started_iso" in
    "${DAY_MEASURED}T00:5"*|"${DAY_MEASURED}T01:0"*|"${DAY_MEASURED}T01:1"*)
      ok "a corrida caiu na hora da cadencia (01:00Z)" ;;
    *)
      bad "a corrida nao caiu na hora da cadencia: $started_iso" ;;
  esac
fi

# --- 2. a corrida acabou ---------------------------------------------------
say ""
say "--- 2. a corrida acabou ---"
if [ -n "$DAY_MEASURED" ]; then
  RUN="$(printf '%s' "$LEDGER" | python3 -c '
import json,sys
r=(json.load(sys.stdin).get("run") or {})
print("|".join([
  str(r.get("found")).lower(),
  str((r.get("finished") or {}).get("iso") or ""),
  str(r.get("duration_ms") if r.get("duration_ms") is not None else ""),
  str(len(r.get("failures") or [])),
  str((r.get("finished") or {}).get("payload",{}).get("fell_back")),
]))' )"
  IFS='|' read -r run_found finished_iso duration_ms n_failures fell_back <<<"$RUN"
  if [ "$run_found" = "true" ] && [ -n "$finished_iso" ]; then
    ok "a corrida terminou as $finished_iso, em ${duration_ms} ms"
  else
    bad "a corrida nao terminou"
  fi
  if [ "$n_failures" = "0" ]; then
    ok "nenhum routine.failed / routine.timed_out entre o inicio e o fim"
  else
    bad "$n_failures falha(s) entre o inicio e o fim"
  fi
  if [ "$fell_back" = "None" ] || [ "$fell_back" = "null" ] || [ -z "$fell_back" ]; then
    ok "a corrida nao caiu para o modelo de reserva (fell_back=$fell_back)"
  else
    bad "a corrida caiu para o modelo de reserva: $fell_back"
  fi
fi

# --- 3. a nota aterrou no store --------------------------------------------
say ""
say "--- 3. a nota aterrou no store ---"
NOTE_UID=""
if [ -n "$DAY_MEASURED" ]; then
  rows="$(q "select a.uid, a.client_id, a.revision, a.body_hash, a.vault_path, a.created_at
            from ikig.artifacts a
            where a.kind = 'nota' and a.deleted_at is null
              and a.created_at >= '${DAY_MEASURED}T00:00:00+00'
              and a.created_at <  '${DAY_MEASURED}T23:59:59+00'
            order by a.created_at;")"
  count="$(printf '%s' "$rows" | grep -c 'not:' || true)"
  if [ "$count" = "1" ]; then
    ok "a nota da noite e uma so: $rows"
    IFS='|' read -r NOTE_UID client_id revision body_hash vault_path created_at <<<"$rows"
  else
    bad "$count notas com data de $DAY_MEASURED (devia ser 1)"
    NOTE_UID="$(printf '%s' "$rows" | head -1 | cut -d'|' -f1)"
  fi
  if [ -n "$NOTE_UID" ]; then
    case "$client_id" in
      pi-*) ok "a nota foi escrita pelo agente (client_id=$client_id)" ;;
      *) bad "a nota nao foi escrita pelo agente (client_id=$client_id)" ;;
    esac
  fi
fi

# --- 4. a seta -------------------------------------------------------------
say ""
say "--- 4. a seta: o ficheiro e o store dizem a mesma coisa ---"
if [ -n "$NOTE_UID" ] && [ -n "$vault_path" ]; then
  file="$TREE/$vault_path"
  if [ ! -f "$file" ]; then
    bad "o store aponta para um ficheiro que nao existe: $vault_path"
  else
    hash="$(sha256sum "$file" | cut -d' ' -f1)"
    if [ "$hash" = "$body_hash" ]; then
      ok "sha256(ficheiro) == body_hash(store) — $hash"
    else
      bad "o ficheiro e o store discordam: $hash != $body_hash"
    fi
    if grep -qF "ueid: $NOTE_UID" "$file"; then
      ok "o ficheiro carrega o ueid da sua linha"
    else
      bad "o ficheiro nao carrega o ueid da sua linha"
    fi
    say "     $(stat -c '%s bytes, mtime %y' "$file")"
  fi
else
  bad "sem nota para comparar com o ficheiro"
fi

# --- 5. a autoria ----------------------------------------------------------
say ""
say "--- 5. a autoria: quem sobe a revisao ---"
if [ -n "$NOTE_UID" ]; then
  revs="$(q "select revision, author, client_id, created_at from ikig.artifact_revisions
             where uid = '$NOTE_UID' order by revision;")"
  say "     $revs"
  by_write="$(printf '%s\n' "$revs" | awk -F'|' '$3 == "vault-write"' | grep -c . || true)"
  by_sync="$(printf '%s\n' "$revs" | awk -F'|' '$3 == "vault-sync"' | grep -c . || true)"
  by_agent="$(printf '%s\n' "$revs" | awk -F'|' '$3 ~ /^pi-/' | grep -c . || true)"
  if [ "$by_write" -ge 1 ]; then
    ok "$by_write revisao(es) do writer (vault-write)"
  else
    bad "nenhuma revisao do writer — a seta nao passou pela nota"
  fi
  if [ "$by_sync" = "0" ]; then
    ok "zero revisoes da ingestao (vault-sync)"
  else
    bad "$by_sync revisoes escritas pela ingestao — o ciclo reescreveu"
  fi
  if [ "$by_agent" -ge 1 ]; then
    ok "$by_agent revisao(es) do agente (a corrida)"
  else
    bad "nenhuma revisao do agente"
  fi
  say "     a chave de idempotencia:"
  q "select key from ikig.idempotency_keys where key like 'vault-write:$NOTE_UID%';"
fi

# --- 6. a ingestao nao escreveu nada --------------------------------------
say ""
say "--- 6. a ingestao que segue o write-back ---"
ingest="$(docker logs "$SYNC_CONTAINER" 2>&1 | grep -E '^scanned=' | tail -1)"
say "     a ultima ronda: ${ingest:-sem log}"
created="$(printf '%s' "$ingest" | sed -n 's/.*created=\([0-9]*\).*/\1/p')"
updated="$(printf '%s' "$ingest" | sed -n 's/.*updated=\([0-9]*\).*/\1/p')"
if [ "${created:-1}" = "0" ] && [ "${updated:-1}" = "0" ]; then
  ok "a ingestao nao criou nada e nao reescreveu nada: created=0 updated=0"
else
  bad "a ingestao escreveu: created=${created:-?} updated=${updated:-?}"
fi

# --- 7. o escritor nao tem backlog -----------------------------------------
say ""
say "--- 7. o escritor nao tem backlog ---"
live="$(q "select count(*) from ikig.artifacts where deleted_at is null;")"
with_path="$(q "select count(*) from ikig.artifacts where deleted_at is null and vault_path is not null;")"
if [ "$live" = "$with_path" ]; then
  ok "$with_path de $live artefactos vivos com vault_path"
else
  bad "$((live - with_path)) artefactos vivos SEM vault_path"
fi

# --- 8. a entrega ao desktop esta ligada -----------------------------------
say ""
say "--- 8. a entrega: o Syncthing que traz a arvore ao desktop ---"
if [ ! -f "$SYNCTHING_CONFIG" ]; then
  bad "a config do Syncthing nao esta em $SYNCTHING_CONFIG — a entrega nao e mensuravel"
else
  KEY="$(grep -oP '(?<=<apikey>)[^<]+' "$SYNCTHING_CONFIG" | head -1)"
  folder_path="$(curl -s --compressed -H "X-API-Key: $KEY" "$SYNCTHING_URL/rest/config/folders" \
    | python3 -c '
import json,sys
folders=json.load(sys.stdin)
for f in folders:
    if f.get("id")==sys.argv[1]:
        print(f.get("path",""))
        break
' "$SYNCTHING_FOLDER")"
  if [ "$folder_path" = "$TREE" ]; then
    ok "a pasta $SYNCTHING_FOLDER vigia a arvore do writer ($folder_path)"
  else
    bad "a pasta $SYNCTHING_FOLDER vigia '$folder_path', e o writer escreve em '$TREE'"
  fi
  status="$(curl -s --compressed -H "X-API-Key: $KEY" \
    "$SYNCTHING_URL/rest/db/status?folder=$SYNCTHING_FOLDER" \
    | python3 -c '
import json,sys
d=json.load(sys.stdin)
print("|".join([str(d.get("state")),str(d.get("needFiles")),str(d.get("errors")),str(d.get("pullErrors")),str(d.get("localFiles")),str(d.get("globalFiles"))]))')"
  IFS='|' read -r state need_files errors pull_errors local_files global_files <<<"$status"
  say "     estado=$state needFiles=$need_files errors=$errors pullErrors=$pull_errors localFiles=$local_files globalFiles=$global_files"
  if [ "${need_files:-1}" = "0" ] && [ "${errors:-1}" = "0" ] && [ "${pull_errors:-1}" = "0" ]; then
    ok "a pasta esta em sincronia ($local_files ficheiros dos dois lados)"
  else
    bad "a pasta nao esta em sincronia: needFiles=$need_files errors=$errors pullErrors=$pull_errors"
  fi
fi

say ""
if [ "$failures" -eq 0 ]; then
  say "=== night-arrow: TUDO PROVADO (noite $DAY_MEASURED) ==="
  exit 0
fi
say "=== night-arrow: $failures FALHA(S) (noite $DAY_MEASURED) ==="
exit 1
