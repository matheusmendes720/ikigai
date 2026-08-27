#!/usr/bin/env bash
# =============================================================================
# MCP Gateway Launcher — Orchestrates all 4 MCP interfaces
#
# Usage:
#   ./start_mcp_gateway.sh          # Interactive menu
#   ./start_mcp_gateway.sh all     # Start all interfaces
#   ./start_mcp_gateway.sh status  # Show status of all
#   ./start_mcp_gateway.sh ikigai  # Start IKIGAi only
#   ./start_mcp_gateway.sh tuiboard # Start tuiboard only
#   ./start_mcp_gateway.sh taskdog  # Start taskdog only
#   ./start_mcp_gateway.sh stop     # Stop all
#
# Architecture:
#   LangChain Deep Agent ──HTTP+SSE──► Unified MCP Gateway
#   Claude Code CLI      ──stdio──►        │
#                                               │
#                               ┌──────────────┼──────────────┐
#                               ▼              ▼              ▼
#                          tuiboard       taskdog      solverforge
#                          (stdio↔HTTP)   (stdio↔HTTP) (stdio↔HTTP)
# =============================================================================

set -e

# ─── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IKIGAI_ROOT="$SCRIPT_DIR"
TASKDOG_ROOT="/mnt/c/Users/mathe/code_space/apps/dev-tools/taskdog"
TUIBOARD_ROOT="/mnt/c/Users/mathe/code_space/apps/kanban/tuiboard"
SOLVERFORGE_ROOT="$HOME/code_space/apps/calendar/solverforge-calendar"

# ─── Runtime detection ─────────────────────────────────────────────────────
BUN="$HOME/.bun/bin/bun"
IKIGAI_PYTHON="/tmp/ikigai-test/bin/python"
TASKDOG_SERVER_PID=""

# ─── Colors ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}   $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERR]${NC}   $1"; }

# ─── Health checks ──────────────────────────────────────────────────────────
check_ikigai() {
    if [ -f "$IKIGAI_PYTHON" ]; then
        log_ok "IKIGAi Python env found"
        return 0
    else
        log_warn "IKIGAi Python env not found at $IKIGAI_PYTHON"
        return 1
    fi
}

check_bun() {
    if [ -x "$BUN" ]; then
        log_ok "Bun found: $($BUN --version)"
        return 0
    else
        log_warn "Bun not found at $BUN"
        return 1
    fi
}

check_taskdog_server() {
    if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
        log_ok "Taskdog server running on :8000"
        return 0
    else
        log_warn "Taskdog server not running on :8000"
        return 1
    fi
}

check_solverforge() {
    if [ -f "$SOLVERFORGE_ROOT/target/release/solverforge-calendar-cli" ]; then
        log_ok "Solverforge binary found"
        return 0
    elif [ -f "$SOLVERFORGE_ROOT/target/release/solverforge-calendar-cli.exe" ]; then
        log_warn "Solverforge Windows exe found (needs Linux binary)"
        return 1
    else
        log_warn "Solverforge binary not found"
        return 1
    fi
}

# ─── Start functions ────────────────────────────────────────────────────────
start_taskdog_server() {
    log_info "Starting Taskdog server..."
    cd "$TASKDOG_ROOT"
    nohup uv run taskdog-server > /tmp/taskdog-server.log 2>&1 &
    TASKDOG_SERVER_PID=$!
    sleep 2
    
    if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
        log_ok "Taskdog server started (PID: $TASKDOG_SERVER_PID)"
    else
        log_error "Failed to start Taskdog server"
        return 1
    fi
}

start_ikigai_mcp() {
    log_info "Starting IKIGAi MCP server..."
    check_ikigai || return 1
    
    # Test the server
    echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"gateway","version":"1.0"}}}' | \
        $IKIGAI_PYTHON "$IKIGAI_ROOT/run_mcp_server.py" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_ok "IKIGAi MCP server ready"
        echo "  → Run: cd $IKIGAI_ROOT && $IKIGAI_PYTHON run_mcp_server.py"
    else
        log_error "IKIGAi MCP server failed"
        return 1
    fi
}

start_tuiboard_mcp() {
    log_info "Starting tuiboard MCP server..."
    check_bun || return 1
    
    # Test the server
    echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"gateway","version":"1.0"}}}' | \
        $BUN run "$TUIBOARD_ROOT/bin/tuiboard-mcp.ts" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_ok "tuiboard MCP server ready"
        echo "  → Run: $BUN run $TUIBOARD_ROOT/bin/tuiboard-mcp.ts"
    else
        log_error "tuiboard MCP server failed"
        return 1
    fi
}

start_taskdog_mcp() {
    log_info "Starting taskdog MCP server..."
    check_taskdog_server || start_taskdog_server || return 1
    
    cd "$TASKDOG_ROOT"
    echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"gateway","version":"1.0"}}}' | \
        uv run taskdog-mcp > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_ok "taskdog MCP server ready"
        echo "  → Run: cd $TASKDOG_ROOT && uv run taskdog-mcp"
    else
        log_error "taskdog MCP server failed"
        return 1
    fi
}

# ─── Status ─────────────────────────────────────────────────────────────────
show_status() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    MCP GATEWAY STATUS                          ║"
    echo "╠══════════════════════════════════════════════════════════════╣"
    
    # Bun
    echo -n "║ Bun:                      "
    if [ -x "$BUN" ]; then
        echo -e "✅ $($BUN --version)                                     ║"
    else
        echo -e "❌ Not found                                        ║"
    fi
    
    # Taskdog server
    echo -n "║ Taskdog API Server (:8000): "
    if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
        echo -e "✅ Running                                      ║"
    else
        echo -e "⚠️  Not running                                ║"
    fi
    
    # Taskdog CLI
    echo -n "║ Taskdog CLI:              "
    if cd "$TASKDOG_ROOT" && uv run taskdog --version > /dev/null 2>&1; then
        echo -e "✅ Installed                                      ║"
    else
        echo -e "⚠️  Not installed                                ║"
    fi
    
    # IKIGAi
    echo -n "║ IKIGAi MCP deps:           "
    if [ -f "$IKIGAI_PYTHON" ]; then
        echo -e "✅ Python env ready                               ║"
    else
        echo -e "❌ Python env missing                             ║"
    fi
    
    # Solverforge
    echo -n "║ Solverforge:              "
    if [ -f "$SOLVERFORGE_ROOT/target/release/solverforge-calendar-cli" ]; then
        echo -e "✅ Binary found                                   ║"
    elif [ -f "$SOLVERFORGE_ROOT/target/release/solverforge-calendar-cli.exe" ]; then
        echo -e "⚠️  Windows exe only                              ║"
    else
        echo -e "❌ Not built                                      ║"
    fi
    
    echo "╠══════════════════════════════════════════════════════════════╣"
    echo "║ TO START:                                                   ║"
    echo "║   IKIGAi:  $IKIGAI_PYTHON run_mcp_server.py               ║"
    echo "║   tuiboard: $BUN run $TUIBOARD_ROOT/bin/tuiboard-mcp.ts   ║"
    echo "║   taskdog:  cd $TASKDOG_ROOT && uv run taskdog-mcp         ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
}

# ─── Menu ───────────────────────────────────────────────────────────────────
show_menu() {
    echo ""
    echo "╔═══════════════════════════════════════╗"
    echo "║     MCP GATEWAY - Choose option      ║"
    echo "╠═══════════════════════════════════════╣"
    echo "║  1. Start all interfaces            ║"
    echo "║  2. Start IKIGAi MCP               ║"
    echo "║  3. Start tuiboard MCP              ║"
    echo "║  4. Start taskdog server + MCP      ║"
    echo "║  5. Show status                     ║"
    echo "║  6. Test all connections            ║"
    echo "║  0. Exit                           ║"
    echo "╚═══════════════════════════════════════╝"
    echo ""
    echo -n "Choice: "
}

# ─── Test all ────────────────────────────────────────────────────────────────
test_all() {
    echo ""
    echo "Testing all MCP interfaces..."
    echo ""
    
    # Test IKIGAi
    echo "─── IKIGAi ───"
    if check_ikigai; then
        echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | \
            $IKIGAI_PYTHON "$IKIGAI_ROOT/run_mcp_server.py" 2>&1 | grep -q "ikigai-maintainer" && \
            log_ok "IKIGAi MCP responding" || log_error "IKIGAi MCP not responding"
    fi
    echo ""
    
    # Test tuiboard
    echo "─── tuiboard ───"
    if check_bun; then
        echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | \
            $BUN run "$TUIBOARD_ROOT/bin/tuiboard-mcp.ts" 2>&1 | grep -q "tuiboard" && \
            log_ok "tuiboard MCP responding" || log_error "tuiboard MCP not responding"
    fi
    echo ""
    
    # Test taskdog
    echo "─── taskdog ───"
    if check_taskdog_server; then
        cd "$TASKDOG_ROOT"
        echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | \
            uv run taskdog-mcp 2>&1 | grep -q "taskdog" && \
            log_ok "taskdog MCP responding" || log_error "taskdog MCP not responding"
    fi
    echo ""
    
    # Test solverforge
    echo "─── solverforge ───"
    check_solverforge || true
    echo ""
}

# ─── Main ───────────────────────────────────────────────────────────────────
main() {
    case "${1:-menu}" in
        all)
            log_info "Starting all MCP interfaces..."
            start_taskdog_server || true
            start_ikigai_mcp || true
            start_tuiboard_mcp || true
            start_taskdog_mcp || true
            show_status
            ;;
        ikigai)
            start_ikigai_mcp
            ;;
        tuiboard)
            start_tuiboard_mcp
            ;;
        taskdog)
            start_taskdog_server || true
            start_taskdog_mcp
            ;;
        status)
            show_status
            ;;
        test)
            test_all
            ;;
        stop)
            log_info "Stopping all servers..."
            pkill -f "taskdog-server" 2>/dev/null || true
            log_ok "Done"
            ;;
        menu|*)
            show_menu
            ;;
    esac
}

main "$@"
