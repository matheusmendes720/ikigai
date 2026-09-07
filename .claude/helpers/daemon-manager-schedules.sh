#!/bin/bash
# daemon-manager-schedules.sh — scheduled-task wiring (loop-engineering).
# Sourced by daemon-manager.sh; do NOT execute directly.
#
# Schedule config lives at .claude/loop/schedules.json (committed,
# declarative, version-controlled). Runtime PID files live under
# .claude-flow/schedules/<name>.pid (gitignored). Each schedule is
# a long-running bash daemon that invokes the command, sleeps the
# interval, and repeats — same nohup pattern as swarm-monitor.

# Parse interval string "60s" / "60m" / "60h" / "60" → integer seconds.
parse_interval_seconds() {
    local raw="$1"
    local num unit
    num=$(echo "$raw" | sed -E 's/([0-9]+).*/\1/')
    unit=$(echo "$raw" | sed -E 's/[0-9]+(.*)/\1/')
    case "$unit" in
        "")    echo "$num" ;;
        s)     echo "$num" ;;
        m)     echo $((num * 60)) ;;
        h)     echo $((num * 3600)) ;;
        d)     echo $((num * 86400)) ;;
        *)     error "Unknown interval unit: $unit (use s/m/h/d)"; return 1 ;;
    esac
}

# Initialize schedules.json if missing.
init_schedules_config() {
    if [ ! -f "$SCHEDULES_CONFIG" ]; then
        echo "[]" > "$SCHEDULES_CONFIG"
    fi
}

# Python helper for JSON config operations on $SCHEDULES_CONFIG.
# `jq` is not installed on PATH; this replaces all schedule config
# read/write operations with portable Python (3.x with json stdlib).
#
# Usage: _py_schedules <op> [key=value ...]
# Ops:  exists|get|append|remove|list|count
# Exit codes follow jq conventions (0=found/matched, 1=not-found).
_py_schedules() {
    SCHEDULES_CONFIG="$SCHEDULES_CONFIG" python - "$@" <<'PYEOF'
import json, os, sys, datetime

path = os.environ["SCHEDULES_CONFIG"]
op = sys.argv[1]
args_dict = {}
for a in sys.argv[2:]:
    if "=" in a:
        k, v = a.split("=", 1)
        args_dict[k] = v


def load():
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(schedules):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(schedules, f, indent=2)
    os.replace(tmp, path)


if op == "exists":
    name = args_dict["name"]
    sys.exit(0 if any(s["name"] == name for s in load()) else 1)

elif op == "get":
    for s in load():
        if s["name"] == args_dict["name"]:
            print(json.dumps(s))
            sys.exit(0)
    sys.exit(1)

elif op == "append":
    schedules = load()
    schedules.append({
        "name": args_dict["name"],
        "interval": args_dict["interval"],
        "interval_seconds": int(args_dict["interval_seconds"]),
        "command": args_dict["command"],
        "cost_cap_usd": float(args_dict.get("cost_cap", "5")),
        "added_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })
    save(schedules)

elif op == "remove":
    save([s for s in load() if s["name"] != args_dict["name"]])

elif op == "list":
    for s in load():
        print(json.dumps(s))

elif op == "count":
    print(len(load()))

else:
    sys.stderr.write(f"_py_schedules: unknown op: {op}\n")
    sys.exit(2)
PYEOF
}

# Tiny helper: extract one field from a JSON object passed as argv[1].
_py_get_field() {
    python -c "import json,sys; print(json.loads(sys.argv[1])[sys.argv[2]])" "$1" "$2"
}

# Add a schedule: persist to config + start daemon immediately.
add_schedule() {
    local name="" interval="" command="" cost_cap=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --name)         name="$2"; shift 2 ;;
            --interval)     interval="$2"; shift 2 ;;
            --command)      command="$2"; shift 2 ;;
            --cost-cap-usd) cost_cap="$2"; shift 2 ;;
            *) error "add_schedule: unknown arg: $1"; return 1 ;;
        esac
    done
    if [ -z "$name" ] || [ -z "$interval" ] || [ -z "$command" ]; then
        error "add_schedule: --name, --interval, --command required"
        return 1
    fi

    init_schedules_config

    # Reject duplicates (idempotency check)
    if _py_schedules exists "name=$name"; then
        error "Schedule '$name' already exists. Use 'remove' first."
        return 1
    fi

    local interval_seconds
    interval_seconds=$(parse_interval_seconds "$interval") || return 1

    # Append to config (preserve insertion order)
    _py_schedules append \
        "name=$name" \
        "interval=$interval" \
        "interval_seconds=$interval_seconds" \
        "command=$command" \
        "cost_cap=${cost_cap:-5}"

    success "Schedule '$name' added (interval=$interval, every ${interval_seconds}s, cost_cap=\$${cost_cap:-5})"

    # Start daemon immediately
    start_schedule "$name"
}

# Start a single schedule daemon by name (reads config, spawns nohup loop).
start_schedule() {
    local name="$1"
    init_schedules_config

    local schedule
    schedule=$(_py_schedules get "name=$name") || {
        error "Schedule '$name' not found in $SCHEDULES_CONFIG"
        return 1
    }

    local interval_seconds command
    interval_seconds=$(_py_get_field "$schedule" interval_seconds)
    command=$(_py_get_field "$schedule" command)

    local pid_file="$SCHEDULES_DIR/$name.pid"
    local log_file="$LOG_DIR/schedules/$name.log"
    mkdir -p "$LOG_DIR/schedules"

    if is_running "$pid_file"; then
        log "Schedule '$name' already running (PID: $(cat "$pid_file"))"
        return 0
    fi

    log "Starting schedule '$name' (every ${interval_seconds}s)..."

    # nohup loop: run command → log → sleep → repeat
    nohup bash -c "while true; do
        echo \"[\$(date -u +%FT%TZ)] schedule=$name: firing \$0 \$@\"
        eval \"$command\" >> \"$log_file\" 2>&1
        rc=\$?
        echo \"[\$(date -u +%FT%TZ)] schedule=$name: done rc=\$rc; sleeping ${interval_seconds}s\"
        sleep $interval_seconds
    done" >> "$log_file" 2>&1 &
    local pid=$!

    echo "$pid" > "$pid_file"
    success "Schedule '$name' started (PID: $pid, log: $log_file)"
}

# Stop a single schedule daemon by name.
stop_schedule() {
    local name="$1"
    local pid_file="$SCHEDULES_DIR/$name.pid"
    stop_daemon "$pid_file" "Schedule '$name'"
}

# Remove a schedule: stop daemon + delete from config.
remove_schedule() {
    local name="$1"
    if [ -z "$name" ]; then
        error "remove_schedule: --name required"
        return 1
    fi
    stop_schedule "$name"
    if [ -f "$SCHEDULES_CONFIG" ]; then
        _py_schedules remove "name=$name"
    fi
    success "Schedule '$name' removed"
}

# List all configured schedules + their running state.
list_schedules() {
    init_schedules_config

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════${RESET}"
    echo -e "${CYAN}       Scheduled Tasks (loop-engineering)${RESET}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${RESET}"
    echo ""

    local count
    count=$(_py_schedules count 2>/dev/null || echo 0)
    if [ -z "$count" ] || [ "$count" = "0" ]; then
        echo -e "  ${YELLOW}No schedules configured${RESET}"
        echo -e "  Add one with: $0 add --name X --interval 60m --command 'bash .claude/loop/loop-tick.sh'"
        echo ""
        return 0
    fi

    # Iterate schedules and show config + status
    while IFS= read -r schedule; do
        local s_name s_interval s_command s_cost_cap
        s_name=$(_py_get_field "$schedule" name)
        s_interval=$(_py_get_field "$schedule" interval)
        s_command=$(_py_get_field "$schedule" command)
        s_cost_cap=$(_py_get_field "$schedule" cost_cap_usd)

        local pid_file="$SCHEDULES_DIR/$s_name.pid"
        if is_running "$pid_file"; then
            echo -e "  ${GREEN}●${RESET} ${CYAN}$s_name${RESET}    ${GREEN}RUNNING${RESET} (PID: $(cat "$pid_file"), every $s_interval, cost_cap=\$$s_cost_cap)"
        else
            echo -e "  ${RED}○${RESET} ${CYAN}$s_name${RESET}    ${RED}STOPPED${RESET}  (every $s_interval, cost_cap=\$$s_cost_cap)"
        fi
        echo -e "      ${YELLOW}command${RESET}: $s_command"
    done < <(_py_schedules list)

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════${RESET}"
    echo ""
}

# Fire a schedule once, right now (don't restart the daemon).
fire_schedule_once() {
    local name="$1"
    init_schedules_config

    local schedule command
    schedule=$(_py_schedules get "name=$name") || {
        error "Schedule '$name' not found"
        return 1
    }
    command=$(_py_get_field "$schedule" command)

    log "Firing schedule '$name' once: $command"
    eval "$command"
    local rc=$?
    log "Schedule '$name' one-shot done (rc=$rc)"
    return $rc
}
