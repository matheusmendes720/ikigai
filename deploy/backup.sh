#!/usr/bin/env bash
# backup.sh — the store's backup, and the proof that it happened.
#
# What it backs up:
#   1. pg_dump  — the logical dump of the `ikigai` database (custom format)
#   2. pg_basebackup — the physical cluster, so a restore does not have to
#      replay anything: the exact bytes, with the WAL it needs to recover
#   3. deploy/compose.yml — the shape of the deployment that made the dump
#
# Why both a logical and a physical backup: the dump is portable and is what
# you restore into a fresh cluster; the basebackup is what you restore when
# the cluster itself is suspect. The store is small — a few tens of MB — so
# carrying both costs nothing.
#
# WHY THE DUMP IS TAKEN FROM THE CONTAINER AND NOT FROM THE FILESYSTEM: the
# PGDATA is on a network block device, and a `tar` of a RUNNING cluster
# captures torn files. `pg_dump` and `pg_basebackup` are the two tools that
# know how to take a consistent copy of a cluster that is being written to.
#
# WHY THE SCRIPT FAILS LOUDLY: if the repository is not configured, this
# script EXITS NON-ZERO and records "not configured". The pattern already on
# this box — the meta-brain backup — exits 0 when the repository is missing,
# so a broken backup looks exactly like a working one. A backup that cannot
# fail cannot be trusted.
#
#   30 4 * * *   /opt/mathe/ikigai/deploy/backup.sh >> /var/log/ikigai/backup.log 2>&1
#
# The destination comes from the environment (contract C-5):
#   IKIGAI_BACKUP_REPOSITORY  — the restic repository (sftp:…, s3:…, or a path)
#   IKIGAI_BACKUP_PASSWORD    — the repository password
#   IKIGAI_BACKUP_SSH_KEY     — the key for an sftp repository (optional)
#
# It runs as root (cron) so it can write the node_exporter metric, and it
# runs the compose commands AS mathe, because the deployment belongs to
# mathe and the containers are his.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${IKIGAI_ENV_FILE:-$SCRIPT_DIR/.env}"
WORK_DIR="${IKIGAI_BACKUP_WORKDIR:-/var/tmp/ikigai-backup}"
TEXTFILE_DIR="${IKIGAI_BACKUP_TEXTFILE:-/var/lib/node_exporter/textfile}"
TEXTFILE="$TEXTFILE_DIR/ikigai-backup.prom"
STATUS_FILE="${IKIGAI_BACKUP_STATUS:-$SCRIPT_DIR/.last_backup.status}"
DEPLOY_USER="${IKIGAI_DEPLOY_USER:-mathe}"

log() { printf '[%s] %s\n' "$(date -Iseconds)" "$*"; }
err() { printf '[%s] ERROR %s\n' "$(date -Iseconds)" "$*" >&2; }

# ─── The environment is READ, never sourced ─────────────────────────────────
# Sourcing an .env under `set -u` explodes on a value that contains a `$`
# (the meta-brain backup dies on `/opt/mathe/.env: line 39: $2: unbound
# variable`). Reading a value is parsing, not evaluation.
env_get() {
  local key="$1" file="${2:-$ENV_FILE}"
  [ -f "$file" ] || return 1
  grep -m1 "^${key}=" "$file" | cut -d= -f2- | tr -d '\r' || true
}

# ─── The compose commands run as the owner of the deployment ────────────────
dc() {
  if [ "$(id -u)" = "0" ]; then
    ( cd "$SCRIPT_DIR" && sudo -u "$DEPLOY_USER" -H \
        env PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
        docker compose "$@" )
  else
    ( cd "$SCRIPT_DIR" && docker compose "$@" )
  fi
}

REPOSITORY="${IKIGAI_BACKUP_REPOSITORY:-$(env_get IKIGAI_BACKUP_REPOSITORY || true)}"
PASSWORD="${IKIGAI_BACKUP_PASSWORD:-$(env_get IKIGAI_BACKUP_PASSWORD || true)}"
SSH_KEY="${IKIGAI_BACKUP_SSH_KEY:-$(env_get IKIGAI_BACKUP_SSH_KEY || true)}"

NOW_EPOCH=$(date +%s)

# ─── The outcome is recorded FIRST ──────────────────────────────────────────
# The status file is the visibility that does not depend on anything else on
# this box: the timestamp, the result and the snapshot id, next to the .env.
write_status() {
  local result="$1" detail="$2" snapshot="${3:-}"
  printf 'attempt=%s\nresult=%s\ndetail=%s\nsnapshot=%s\n' \
    "$(date -Iseconds)" "$result" "$detail" "$snapshot" > "$STATUS_FILE" 2>/dev/null \
    || log "WARN the status file could not be written"
  if [ "$(id -u)" = "0" ]; then
    chown "$DEPLOY_USER":"$DEPLOY_USER" "$STATUS_FILE" 2>/dev/null || true
  fi
}

# Every exit that is not a success is recorded. Without this, a script that
# dies in the middle leaves the LAST SUCCESSFUL run in the status file, and
# the status file says "ok" about a backup that did not happen.
trap 'rc=$?; if [ "$rc" -ne 0 ]; then write_status failed "exit_${rc}"; fi' EXIT

# The metric is a COURTESY, never a condition: a backup that succeeded and
# then died writing a .prom file is a backup that happened. So a failure
# here is a warning, not an exit.
write_metric() {
  local status="$1" detail="$2" snapshot="${3:-}"
  write_status "$([ "$status" = "1" ] && echo ok || echo failed)" "$detail" "$snapshot"
  if ! mkdir -p "$TEXTFILE_DIR" 2>/dev/null; then
    log "WARN the textfile directory $TEXTFILE_DIR is not writable — the metric is not visible to Prometheus (the backup itself is fine)"
    return 0
  fi
  local tmp="$TEXTFILE.$$"
  if ! cat > "$tmp" 2>/dev/null <<EOF
# HELP ikigai_backup_last_attempt Unix timestamp of the last backup attempt
# TYPE ikigai_backup_last_attempt gauge
ikigai_backup_last_attempt $NOW_EPOCH
# HELP ikigai_backup_success 1 if the last backup succeeded, 0 if it failed
# TYPE ikigai_backup_success gauge
ikigai_backup_success $status
# HELP ikigai_backup_configured 1 if a backup repository is configured at all
# TYPE ikigai_backup_configured gauge
ikigai_backup_configured $([ -n "$REPOSITORY" ] && echo 1 || echo 0)
# HELP ikigai_backup_detail Free text: what happened
# TYPE ikigai_backup_detail gauge
ikigai_backup_detail{state="$detail"} 1
EOF
  then
    rm -f "$tmp"; log "WARN the metric could not be written (the backup itself is fine)"; return 0
  fi
  chmod 644 "$tmp" 2>/dev/null || true
  mv -f "$tmp" "$TEXTFILE" 2>/dev/null || { rm -f "$tmp"; log "WARN the metric could not be moved into place"; }
}

# ─── Preconditions ─────────────────────────────────────────────────────────
if [ -z "$REPOSITORY" ] || [ -z "$PASSWORD" ]; then
  err "no backup repository configured (IKIGAI_BACKUP_REPOSITORY / IKIGAI_BACKUP_PASSWORD)"
  err "the store is on a volume with NO snapshot: until this is configured, it is ONE disk away from gone"
  write_metric 0 "not_configured"
  exit 2
fi

if ! command -v restic >/dev/null 2>&1; then
  err "restic is not installed on this host"
  write_metric 0 "restic_missing"
  exit 3
fi

export RESTIC_REPOSITORY="$REPOSITORY"
export RESTIC_PASSWORD="$PASSWORD"
[ -n "$SSH_KEY" ] && export RESTIC_SFTP_KEY="$SSH_KEY"

# The repository belongs to the deployment user, whoever runs the script: the
# cron runs it as root (to write the metric) and a human runs it as mathe,
# and a repository whose files change owner between the two is a repository
# that breaks for one of them.
restic_run() {
  if [ "$(id -u)" = "0" ]; then
    sudo -u "$DEPLOY_USER" -H env \
      PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
      RESTIC_REPOSITORY="$REPOSITORY" \
      RESTIC_PASSWORD="$PASSWORD" \
      ${SSH_KEY:+RESTIC_SFTP_KEY="$SSH_KEY"} \
      restic "$@"
  else
    restic "$@"
  fi
}

cd "$SCRIPT_DIR"

# ─── The repository: created if it does not exist yet ───────────────────────
if ! restic_run snapshots --no-lock >/dev/null 2>&1; then
  log "initialising the repository at $REPOSITORY"
  if ! restic_run init 2>&1; then
    err "the repository could not be reached or created — check the credentials and the host"
    write_metric 0 "repository_unreachable"
    exit 4
  fi
fi

# ─── The dumps ─────────────────────────────────────────────────────────────
# The work directory is READ by the repository user, and the repository user
# is not necessarily the user that writes the dumps. Without this, restic
# backs up NOTHING and still reports a snapshot — a backup that is green and
# empty, which is the worst kind.
umask 022
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
chmod 755 "$WORK_DIR"

log "the logical dump"
dc exec -T db pg_dump -U ikigai -d ikigai -Fc > "$WORK_DIR/ikigai.dump"
chmod 644 "$WORK_DIR/ikigai.dump"
[ -s "$WORK_DIR/ikigai.dump" ] || { err "the dump is empty"; write_metric 0 "empty_dump"; exit 5; }

log "the physical cluster (pg_basebackup, WAL included)"
dc exec -T db pg_basebackup -U ikigai -D /tmp/ikigai-basebackup -Ft -z -X stream -c fast
dc exec -T db tar -C /tmp -cf - ikigai-basebackup | gzip -1 > "$WORK_DIR/pgdata-basebackup.tar.gz"
dc exec -T db rm -rf /tmp/ikigai-basebackup
chmod 644 "$WORK_DIR/pgdata-basebackup.tar.gz"
[ -s "$WORK_DIR/pgdata-basebackup.tar.gz" ] || { err "the basebackup is empty"; write_metric 0 "empty_basebackup"; exit 6; }

cp "$SCRIPT_DIR/compose.yml" "$WORK_DIR/compose.yml"
chmod 644 "$WORK_DIR/compose.yml"

log "the sizes"
ls -lh "$WORK_DIR" | tail -n +2 | awk '{print "  " $9 " " $5}'

# ─── The backup ────────────────────────────────────────────────────────────
SNAPSHOT=$(restic_run backup --tag ikigai-store "$WORK_DIR" --host "$(hostname)" 2>&1 | tee /dev/stderr | grep -oE 'snapshot [0-9a-f]+' | tail -1 | awk '{print $2}')
if [ -z "${SNAPSHOT:-}" ]; then
  err "restic did not report a snapshot"
  write_metric 0 "backup_failed"
  exit 7
fi
log "snapshot $SNAPSHOT"

# ─── The snapshot is PROVED, not assumed ───────────────────────────────────
# restic reports a snapshot even when it backed up nothing it could read. So
# the snapshot is opened and looked at: the dump and the basebackup have to
# be IN it. A snapshot without them is a backup of nothing, and it is the
# difference between a backup and the appearance of one.
SNAPSHOT_FILES=$(restic_run ls "$SNAPSHOT" 2>/dev/null || true)
for required in ikigai.dump pgdata-basebackup.tar.gz; do
  if ! printf '%s' "$SNAPSHOT_FILES" | grep -q "$required"; then
    err "the snapshot does NOT contain $required — the backup captured nothing usable"
    err "what it does contain:"
    printf '%s\n' "$SNAPSHOT_FILES" | sed 's/^/    /' | head -20 >&2
    write_metric 0 "snapshot_incomplete"
    exit 8
  fi
  log "the snapshot contains $required"
done

log "retention: 7 daily, 4 weekly, 6 monthly"
restic_run forget --tag ikigai-store --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune 2>&1 | tail -3

rm -rf "$WORK_DIR"
write_metric 1 "ok" "$SNAPSHOT"
log "done — snapshot $SNAPSHOT"
