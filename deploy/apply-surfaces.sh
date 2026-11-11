#!/usr/bin/env bash
# THE PUBLISHED SURFACES: the route the repository declares, applied on the box.
#
# The table (`deploy/surfaces.json`) is the truth about WHERE a surface is and
# WHETHER it is published. This script applies it to the tailscale's serve
# config, and it is deliberately NARROW — the box's tailscale config is shared
# with services this repository does not own.
#
# Three shapes are forbidden here, and each one was measured on this box:
#
#   * `tailscale funnel --bg <port>` WITHOUT `--https`. The funnel then
#     assumes the **443** host and REPLACES that host's `/` handler. Measured:
#     it took the MCP api's route down (443 `/` was 127.0.0.1:8000 and
#     became 127.0.0.1:10000) and left `AllowFunnel` on 443.
#   * `tailscale funnel reset`. It wipes the WHOLE serve config — measured:
#     the 443, the 8443 and the 8444 of another deployment went with it.
#   * a port or a path the table does not declare. The 443 host of this box
#     carries the MCP api, the agent's harness and three routes of another
#     project; a surface published from there publishes all of them.
#
# So: the script touches ONLY the host:port and path the table declares, it
# ALWAYS passes `--https` and `--set-path`, it never resets anything, and it
# photographs the config before and after — restoring the other surfaces'
# handlers if a command moved them.
#
# The publication switch is the STATE, and it fails closed: `pending` keeps
# the surface inside the tailnet, `published` puts it on the internet. Only
# the owner moves between the two, and only in the repository.
set -uo pipefail

TABLE="${IKIGAI_SURFACES_TABLE:-$(cd "$(dirname "$0")" && pwd)/surfaces.json}"

if [ ! -f "$TABLE" ]; then
  echo "::error::the table of published surfaces is missing: $TABLE"
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "::error::jq is not installed — the table cannot be read, and a route"
  echo " that cannot be read is a route nobody applied."
  exit 1
fi

snapshot() {
  # `sudo -n` NEVER prompts: the deploy runs over a non-interactive ssh, and
  # a command waiting for a password is a command that hangs the deploy.
  sudo -n tailscale serve status --json 2>/dev/null || echo "{}"
}

# The routes as a flat list: "host:port|path|proxy", one per line.
routes_of() {
  jq -r '
    .Web // {} | to_entries[] | .key as $hp | .value.Handlers // {}
    | to_entries[] | $hp + "|" + .key + "|" + (.value.Proxy // "")
  ' 2>/dev/null | sort
}

echo "=== the published surfaces, as the repository declares them ==="
jq -r '.surfaces // {} | to_entries[] | "  " + .key + ": " + .value.host + ":" + (.value.https_port|tostring) + .value.path + "  mode=" + .value.mode + "  state=" + .value.state' "$TABLE"

BEFORE="$(snapshot)"
BEFORE_ROUTES="$(routes_of <<<"$BEFORE")"

failures=0

while IFS=$'\t' read -r name host port path target mode state; do
  [ -n "${name:-}" ] || continue
  echo ""
  echo "=== $name: $host:$port$path -> $target (mode=$mode, state=$state) ==="

  case "$state" in
    published)
      if [ "$mode" != "funnel" ]; then
        echo "::error::$name is declared published but its mode is '$mode', not 'funnel'."
        echo " A surface that does not know how to be published stays unpublished."
        failures=$((failures + 1))
        continue
      fi
      # The funnel, with BOTH flags: --https says which host, --set-path says
      # which path. Without them the funnel takes the 443 host's `/`.
      #
      # The output is CAPTURED and the exit code is the funnel's own: piping
      # it into `head` would make the status the status of `head`, and a
      # refused funnel would look like a successful one.
      if ! output="$(sudo -n tailscale funnel --bg --https="$port" --set-path="$path" "$target" 2>&1)"; then
        printf '%s\n' "$output" | head -6
        echo "::error::the funnel refused $name."
        failures=$((failures + 1))
        continue
      fi
      printf '%s\n' "$output" | head -6
      ;;
    pending)
      # `tailscale serve` with the same flags RE-APPLIES the route and takes
      # the funnel flag off that host with it ("Removing Funnel for ...").
      # That is the fail-closed direction: declared, and not published.
      if ! output="$(sudo -n tailscale serve --bg --https="$port" --set-path="$path" "$target" 2>&1)"; then
        printf '%s\n' "$output" | head -6
        echo "::error::the route for $name could not be applied."
        failures=$((failures + 1))
        continue
      fi
      printf '%s\n' "$output" | head -6
      ;;
    *)
      echo "::error::$name has an unknown state '$state'."
      failures=$((failures + 1))
      continue
      ;;
  esac
done < <(jq -r '
  (.surfaces // {}) | to_entries[]
  | [.key, .value.host, (.value.https_port|tostring), .value.path,
     .value.target, .value.mode, .value.state] | @tsv
' "$TABLE")

AFTER="$(snapshot)"
AFTER_ROUTES="$(routes_of <<<"$AFTER")"

echo ""
echo "=== what changed in the box's routes ==="
if [ "$BEFORE_ROUTES" = "$AFTER_ROUTES" ]; then
  echo "  the handlers are identical (only the publication flag can have moved)"
else
  diff <(echo "$BEFORE_ROUTES") <(echo "$AFTER_ROUTES") || true
fi

echo ""
echo "=== the routes, now ==="
echo "$AFTER_ROUTES" | sed 's/^/  /'

# THE GUARD: no handler of another surface may have moved. The declared
# surface's own handler is allowed to change (that is the point); everything
# else must be exactly as it was.
echo ""
echo "=== the other surfaces are untouched? ==="
DECLARED_HOSTPORTS="$(jq -r '(.surfaces // {})[] | .host + ":" + (.https_port|tostring)' "$TABLE" | sort -u | tr '\n' ' ')"
other_before="$(echo "$BEFORE_ROUTES" | while IFS='|' read -r hp p proxy; do
  case " $DECLARED_HOSTPORTS " in *" $hp "*) continue ;; esac
  echo "$hp|$p|$proxy"
done | sort)"
other_after="$(echo "$AFTER_ROUTES" | while IFS='|' read -r hp p proxy; do
  case " $DECLARED_HOSTPORTS " in *" $hp "*) continue ;; esac
  echo "$hp|$p|$proxy"
done | sort)"

if [ "$other_before" = "$other_after" ]; then
  echo "  OK: the other surfaces' handlers are exactly as they were"
else
  echo "::error::a command moved a handler that belongs to another surface."
  diff <(echo "$other_before") <(echo "$other_after") || true
  echo ""
  echo "  restoring them from the photograph taken before the commands:"
  echo "$BEFORE_ROUTES" | while IFS='|' read -r hp p proxy; do
    case " $DECLARED_HOSTPORTS " in *" $hp "*) continue ;; esac
    port="${hp##*:}"
    sudo -n tailscale serve --bg --https="$port" --set-path="$p" "$proxy" >/dev/null 2>&1 \
      && echo "    restored $hp$p -> $proxy" \
      || echo "    ::error::could not restore $hp$p"
  done
  failures=$((failures + 1))
fi

echo ""
if [ "$failures" -ne 0 ]; then
  echo "::error::the published surfaces could not be applied ($failures failure(s))."
  exit 1
fi
echo "the published surfaces are as the repository declares them"
