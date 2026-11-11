#!/usr/bin/env bash
# vault-arrow.sh — the probe that measures the store → vault arrow (ADR-043).
#
# It runs on the VPS, from the host, against the running stack. It measures
# FIVE facts, and each one is a fact that can be false:
#
#   1. the writer writes files: sha256(file) == body_hash(store), for every file
#   2. the file carries the identity: the frontmatter states the store's ueid
#   3. the store knows where the file is: every live artifact has a vault_path
#   4. the cycle closes: the ingestion creates nothing and rewrites nothing
#   5. the trees are separate: the writer has the new tree rw, the ingestion
#      has every tree ro
#
# It EXITS NON-ZERO when a fact is false. A probe that only prints is a report,
# and a report does not keep anybody honest.
#
# Usage:  bash deploy/probes/vault-arrow.sh
#
# It never prints a secret: the Syncthing API key is read inside the box and
# used as a header, and it is not echoed.

set -u

WRITE_CONTAINER="${WRITE_CONTAINER:-ikigai-write-1}"
SYNC_CONTAINER="${SYNC_CONTAINER:-ikigai-sync-1}"
DB_CONTAINER="${DB_CONTAINER:-ikigai-db-1}"
TREE="${TREE:-/mnt/volume-fsn1-1/vault-escrita}"

failures=0

say() { printf '%s\n' "$*"; }
ok() { printf 'OK    %s\n' "$*"; }
bad() { printf 'FALHA %s\n' "$*"; failures=$((failures + 1)); }

q() { docker exec "$DB_CONTAINER" psql -U ikigai -d ikigai -t -A -F'|' -c "$1"; }

say "=== vault-arrow: a seta store -> vault, medida (UTC $(date -u +%Y-%m-%dT%H:%M:%SZ)) ==="

# --- 1 e 2: o ficheiro e o store dizem a mesma coisa ------------------------
say ""
say "--- 1. o ficheiro e a linha que o originou ---"
rows="$(q "select a.uid, a.body_hash, a.vault_path from ikig.artifacts a
          where a.deleted_at is null and a.vault_path is not null
            and a.client_id <> 'vault-sync'
          order by a.vault_path;")"

total=0; equal=0; diverged=0; missing=0; without_uid=0
while IFS='|' read -r uid body_hash vpath; do
  [ -z "${uid:-}" ] && continue
  total=$((total + 1))
  file="$TREE/$vpath"
  if [ ! -f "$file" ]; then
    bad "o store aponta para um ficheiro que nao existe: $vpath"
    missing=$((missing + 1))
    continue
  fi
  hash="$(sha256sum "$file" | cut -d' ' -f1)"
  if [ "$hash" = "$body_hash" ]; then
    equal=$((equal + 1))
  else
    bad "o ficheiro e o store discordam: $vpath"
    diverged=$((diverged + 1))
  fi
  if ! grep -qF "ueid: $uid" "$file"; then
    bad "o ficheiro nao carrega o ueid da sua linha: $vpath"
    without_uid=$((without_uid + 1))
  fi
done <<EOF
$rows
EOF

[ "$diverged" -eq 0 ] && [ "$missing" -eq 0 ] && [ "$without_uid" -eq 0 ] \
  && ok "$total/$total ficheiros: sha256 == body_hash, e todos com o ueid" \
  || bad "$total ficheiros: $equal iguais, $diverged divergentes, $missing ausentes, $without_uid sem ueid"

# --- 3: o store sabe onde esta o ficheiro ----------------------------------
say ""
say "--- 2. o store sabe onde esta o ficheiro ---"
live="$(q "select count(*) from ikig.artifacts where deleted_at is null;")"
with_path="$(q "select count(*) from ikig.artifacts where deleted_at is null and vault_path is not null;")"
if [ "$live" = "$with_path" ]; then
  ok "$with_path de $live artefactos vivos com vault_path (o escritor nao tem backlog)"
else
  bad "$((live - with_path)) artefactos vivos SEM vault_path (o escritor ainda tem backlog)"
fi
scanned="$(docker logs "$WRITE_CONTAINER" 2>&1 | grep -E '^scanned=' | tail -1)"
say "     o escritor na ultima ronda: ${scanned:-sem log}"

# --- 4: o ciclo fecha ------------------------------------------------------
say ""
say "--- 3. a ingestao que segue o write-back ---"
ingest="$(docker logs "$SYNC_CONTAINER" 2>&1 | grep -E '^scanned=' | tail -1)"
say "     a ingestao na ultima ronda: ${ingest:-sem log}"
created="$(printf '%s' "$ingest" | sed -n 's/.*created=\([0-9]*\).*/\1/p')"
updated="$(printf '%s' "$ingest" | sed -n 's/.*updated=\([0-9]*\).*/\1/p')"
if [ "${created:-1}" = "0" ] && [ "${updated:-1}" = "0" ]; then
  ok "a ingestao nao criou nada e nao reescreveu nada: created=0 updated=0"
else
  bad "a ingestao escreveu: created=${created:-?} updated=${updated:-?}"
fi
by_sync="$(q "select count(*) from ikig.artifact_revisions r
              join ikig.artifacts a on a.uid = r.uid
              where a.vault_path is not null and a.client_id <> 'vault-sync'
                and r.client_id = 'vault-sync';")"
if [ "$by_sync" = "0" ]; then
  ok "zero revisoes escritas pela ingestao nas linhas que o escritor wrote"
else
  bad "$by_sync revisoes escritas pela ingestao (o ciclo reescreveu)"
fi

# --- 5: as arvores sao separadas -------------------------------------------
say ""
say "--- 4. as arvores ---"
if docker inspect "$WRITE_CONTAINER" --format '{{range .Mounts}}{{.Destination}}:{{.RW}} {{end}}' \
    | grep -q '/app/vault-escrita:true'; then
  ok "o escritor tem a arvore nova em rw"
else
  bad "o escritor nao tem a arvore nova em rw"
fi
if docker inspect "$SYNC_CONTAINER" --format '{{range .Mounts}}{{.Destination}}:{{.RW}} {{end}}' \
    | grep -q '/app/vault:false' \
    && docker inspect "$SYNC_CONTAINER" --format '{{range .Mounts}}{{.Destination}}:{{.RW}} {{end}}' \
    | grep -q '/app/zonas:false'; then
  ok "a ingestao tem o vault do clone e as zonas em ro"
else
  bad "a ingestao tem uma das arvores em rw"
fi
if [ -e "$TREE/.git" ]; then
  say "     a arvore escrita E um repositorio git (o commit local passa a existir)"
else
  ok "a arvore escrita nao e um repositorio git (por desenho: o commit e skipped)"
fi

say ""
if [ "$failures" -eq 0 ]; then
  say "=== vault-arrow: TUDO PROVADO ==="
  exit 0
fi
say "=== vault-arrow: $failures FALHA(S) ==="
exit 1
