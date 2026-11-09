#!/usr/bin/env bash
# restore.sh — put the store back, from a backup, in one command.
#
#   ./restore.sh --list
#   ./restore.sh --snapshot <id> --logical
#   ./restore.sh --snapshot <id> --physical
#
# The two paths exist for two different failures:
#
#   --logical   the store's DATA is wrong, the cluster is fine. A pg_dump
#               restored into the running cluster. Fast, portable, and it
#               keeps the current cluster.
#   --physical  the CLUSTER is wrong (corrupted, or the volume died mid-write).
#               The pg_basebackup is unpacked into the PGDATA directory and
#               the store is started on it. This is the one that recovers
#               from a torn volume, and it needs the container stopped.
#
# The restore is NOT run against the live store without saying so: a logical
# restore with --clean DROPS the objects it replaces. The script prints the
# current artifact count before and after, so the effect is visible and not
# assumed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${IKIGAI_ENV_FILE:-$SCRIPT_DIR/.env}"
WORK_DIR="${IKIGAI_BACKUP_WORKDIR:-/var/tmp/ikigai-restore}"

env_get() {
  local key="$1" file="${2:-$ENV_FILE}"
  [ -f "$file" ] || return 1
  grep -m1 "^${key}=" "$file" | cut -d= -f2- | tr -d '\r' || true
}

REPOSITORY="${IKIGAI_BACKUP_REPOSITORY:-$(env_get IKIGAI_BACKUP_REPOSITORY || true)}"
PASSWORD="${IKIGAI_BACKUP_PASSWORD:-$(env_get IKIGAI_BACKUP_PASSWORD || true)}"
SSH_KEY="${IKIGAI_BACKUP_SSH_KEY:-$(env_get IKIGAI_BACKUP_SSH_KEY || true)}"

if [ -z "$REPOSITORY" ] || [ -z "$PASSWORD" ]; then
  echo "no backup repository configured (IKIGAI_BACKUP_REPOSITORY / IKIGAI_BACKUP_PASSWORD)" >&2
  exit 2
fi
export RESTIC_REPOSITORY="$REPOSITORY"
export RESTIC_PASSWORD="$PASSWORD"
[ -n "$SSH_KEY" ] && export RESTIC_SFTP_KEY="$SSH_KEY"

cd "$SCRIPT_DIR"

SNAPSHOT=""
MODE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --list) restic snapshots --tag ikigai-store; exit 0 ;;
    --snapshot) SNAPSHOT="$2"; shift 2 ;;
    --logical|--physical) MODE="$1"; shift ;;
    *) echo "unknown argument: $1" >&2; exit 64 ;;
  esac
done
[ -n "$SNAPSHOT" ] || { echo "--snapshot is required" >&2; exit 64; }
[ -n "$MODE" ] || { echo "--logical or --physical is required" >&2; exit 64; }

rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
restic restore "$SNAPSHOT" --target "$WORK_DIR" >/dev/null
DUMP=$(find "$WORK_DIR" -name 'ikigai.dump' -type f | head -1)
BASE=$(find "$WORK_DIR" -name 'pgdata-basebackup.tar.gz' -type f | head -1)

count_artifacts() {
  docker compose exec -T db psql -U ikigai -d ikigai -tAc \
    "select count(*) from ikig.artifacts" 2>/dev/null | tr -d '[:space:]' || echo "?"
}

if [ "$MODE" = "--logical" ]; then
  [ -n "$DUMP" ] || { echo "the snapshot has no logical dump" >&2; exit 5; }
  echo "the artifacts BEFORE the restore: $(count_artifacts)"
  echo "this DROPS the objects it replaces. Ctrl-C in the next 5 seconds to stop."
  sleep 5
  docker compose exec -T db pg_restore -U ikigai -d ikigai --clean --if-exists --no-owner < "$DUMP"
  echo "the artifacts AFTER  the restore: $(count_artifacts)"
  exit 0
fi

if [ "$MODE" = "--physical" ]; then
  [ -n "$BASE" ] || { echo "the snapshot has no physical basebackup" >&2; exit 5; }
  PGDATA=$(docker compose exec -T db sh -c 'echo /var/lib/postgresql/data' | tr -d '\r')
  echo "the store is being REPLACED, not merged. The container stops now."
  docker compose stop db
  echo "unpacking the basebackup into $PGDATA"
  docker compose run --rm --no-deps --entrypoint sh db -c "
    rm -rf /var/lib/postgresql/data/* && tar -C /var/lib/postgresql/data -xzf -" < "$BASE"
  docker compose up -d db
  for i in $(seq 1 40); do
    st=$(docker inspect --format '{{.State.Health.Status}}' ikigai-db-1 2>/dev/null)
    [ "$st" = "healthy" ] && break
    sleep 2
  done
  echo "the artifacts AFTER the restore: $(count_artifacts)"
  exit 0
fi
