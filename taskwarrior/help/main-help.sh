#!/bin/bash
# Custom Taskwarrior Help System Router
# Routes to different help topics based on argument

HELP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
HELP_DIR="$HELP_ROOT/content"
QUICK_MODE=0
TOPIC="${1:-overview}"

# Check for quick mode
if [ "$1" = "--quick" ] || [ "$1" = "-q" ]; then
    QUICK_MODE=1
    TOPIC="${2:-overview}"
fi

# Map topic names to files
case "$TOPIC" in
    overview|00|"")
        FILE="00-overview.md"
        ;;
    hierarchy|01|hier)
        FILE="01-hierarchy.md"
        ;;
    workflows|02|workflow)
        if [ $QUICK_MODE -eq 1 ]; then
            FILE="workflows-quick.md"
        else
            FILE="02-workflows.md"
        fi
        ;;
    filters|03|filter)
        if [ $QUICK_MODE -eq 1 ]; then
            FILE="filters-quick.md"
        else
            FILE="03-filters.md"
        fi
        ;;
    args|04|arguments|parameters)
        FILE="04-args.md"
        ;;
    flags|05|flag|modifiers)
        FILE="05-flags.md"
        ;;
    reports|06|report)
        if [ $QUICK_MODE -eq 1 ]; then
            FILE="reports-quick.md"
        else
            FILE="06-reports.md"
        fi
        ;;
    contexts|07|context)
        FILE="07-contexts.md"
        ;;
    recurrence|08|recur)
        FILE="08-recurrence.md"
        ;;
    udas|09|uda)
        if [ $QUICK_MODE -eq 1 ]; then
            FILE="udas-quick.md"
        else
            FILE="09-udas.md"
        fi
        ;;
    aliases|10|alias)
        if [ $QUICK_MODE -eq 1 ]; then
            FILE="aliases-quick.md"
        else
            FILE="10-aliases.md"
        fi
        ;;
    blocks|11|block|blocos)
        FILE="11-blocks.md"
        ;;
    metrics|12|metric)
        FILE="12-metrics.md"
        ;;
    *)
        # Fallback to vanilla Taskwarrior help
        task help "$@"
        exit $?
        ;;
esac

# Set formatter based on mode
HELP_FILE="$HELP_DIR/$FILE"
if [ $QUICK_MODE -eq 1 ]; then
    FORMATTER="$HELP_ROOT/format-quick.py"
else
    FORMATTER="$HELP_ROOT/format-markdown.sh"
fi

if [ -f "$HELP_FILE" ]; then
    # Set UTF-8 encoding
    export LC_ALL=C.UTF-8
    export LANG=C.UTF-8
    
    # Detect if output is TTY (terminal) or piped
    if [ -t 1 ]; then
        # TTY: use colors and pagination
        if [ $QUICK_MODE -eq 1 ] && [ -f "$FORMATTER" ]; then
            # Use quick formatter (Python)
            python3 "$FORMATTER" "$HELP_FILE"
        elif [ -f "$FORMATTER" ] && [ -x "$FORMATTER" ]; then
            # Use custom formatter with colors (bash script)
            if command -v less >/dev/null 2>&1; then
                "$FORMATTER" "$HELP_FILE" | less -R
            else
                "$FORMATTER" "$HELP_FILE"
            fi
        else
            # Fallback: try to use less with colors
            if command -v less >/dev/null 2>&1; then
                cat "$HELP_FILE" | less -R
            else
                cat "$HELP_FILE"
            fi
        fi
    else
        # Piped/redirected: no colors, no pagination
        if [ $QUICK_MODE -eq 1 ] && [ -f "$FORMATTER" ]; then
            python3 "$FORMATTER" "$HELP_FILE"
        elif [ -f "$FORMATTER" ] && [ -x "$FORMATTER" ]; then
            "$FORMATTER" "$HELP_FILE"
        else
            cat "$HELP_FILE"
        fi
    fi
    
    # Always return exit code 0 for help
    exit 0
else
    echo "Help topic '$TOPIC' not found. Available topics:"
    echo "  overview, hierarchy, workflows, filters, args, flags"
    echo "  reports, contexts, recurrence, udas, aliases, blocks, metrics"
    echo ""
    echo "Use: th <topic>"
    exit 1
fi
