# Phase B4 — Review Queue Worker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire existing `queue.py` + `agent_consumer.py` + `agent_propagator.py` into a real supervisor process that drains `data/review_queue/` with pidfile-based liveness.

**Architecture:** Long-running worker reads pending TaskChange events from filesystem queue, runs PAE validation, propagates approved events to fork adapters, acks results. Mirrors B3.4 mcp_gateway pattern: pidfile + cross-platform PID-alive probe + BACKEND_PROCESSES wire-up + CI contract gate.

**Tech Stack:** Python stdlib (queue polling), existing `src/mesh/{queue,agent_consumer,agent_propagator}.py`, reuse `interfaces/cli/mcp_gateway_probe._is_pid_alive` for cross-platform probe.

## Global Constraints

- Pydantic v2 strict (`frozen=True`, `extra="forbid"`)
- Append-only invariant on `data/review_queue/` (never delete events; only ack status)
- Cross-platform (Windows + POSIX) — reuse `_is_pid_alive` pattern from `mcp_gateway_probe.py`
- NO new dependencies; stdlib only
- `BACKEND_PROCESSES["review_queue_worker"]` already exists in `interfaces/cli/server.py` (line 101) — extend it
- start/stop commands in server.py remain STUBs (consistent with mcp_gateway B3.4); only probe + worker module needed for B4
- All worktrees/commit messaging: NO `Co-Authored-By` trailer
- Test command: `PYTHONPATH=. /c/Python314/Scripts/pytest.exe interfaces/cli/tests/ -v`
- Pre-flight blockers (verify from `C:\Users\mathe\.claude\projects\C--Users-mathe-code-space-life-oss-life\memory\MEMORY.md`): no poetry, no langgraph dev, no src/operational/ zero-byte reads, no Co-Authored-By

---

## Task B4.1: Review Queue Worker Module

**Files:**
- Create: `src/mesh/review_queue_worker.py`
- Create: `tests/mesh/test_review_queue_worker.py` (or `interfaces/cli/tests/test_review_queue_worker.py` — pick whichever fits existing test layout)

**Interfaces (consumed by later tasks):**
- `run_once(adapters: list[ForkAdapter]) -> RunResult` — drain all pending events, return counts
- `start_worker(adapters, pidfile_path, poll_interval=1.0)` — write pidfile, run loop until SIGTERM/KeyboardInterrupt
- `stop_worker(pidfile_path) -> bool` — read pidfile, kill PID, remove pidfile; return True if killed
- `worker_status(pidfile_path) -> dict` — same shape as `probe_mcp_gateway()` returns: `{running, pid, started_at}`

**Plan:** build minimal, single-pass functional core first (`run_once`), then wrap with pidfile daemon (`start_worker`/`stop_worker`). Tests use a temp queue dir with synthetic TaskChange events.

---

## Task B4.2: Wire BACKEND_PROCESSES to worker probe

**Files:**
- Modify: `interfaces/cli/server.py` (lines 100-118 `BACKEND_PROCESSES` + `backend_status()`)

**Interfaces:**
- `worker_status(pidfile_path)` from B4.1 imported in `backend_status()`
- Add `pidfile_path: Path` to `BACKEND_PROCESSES["review_queue_worker"]`
- `backend_status()` calls probe for review_queue_worker (same shape as mcp_gateway branch)

**Plan:** minimal change — copy the mcp_gateway probe branch, swap name + function.

---

## Task B4.3: CI Gate for Review Queue Worker

**Files:**
- Modify: `.github/workflows/ci.yml` (add new job `review-queue-worker-contract`)

**Plan:** mirror B3.6 job exactly. New job runs ubuntu-latest, needs quality-gates, runs `PYTHONPATH=. pytest interfaces/cli/tests/test_review_queue_worker.py -v`.

---

## Task B4.4: Memory Persistence

**Files:**
- Create: `C:\Users\mathe\.claude\projects\C--Users-mathe-code-space-life-oss-life\memory\phase-b4-review-queue-worker-complete-2026-08-29.md`

**Plan:** capture lessons from B4.1-B4.3 (e.g., pidfile path conventions, cross-platform probe reuse).

---

## What's Out of Scope (B5+)

- Agent consumer wiring to LangGraph (B5)
- Agent propagator wiring to multi-adapter supervisor (B5)
- Vault sync protocol (B6)
- Real daemon supervisor (systemd / Windows service) — B4 worker is a normal Python process started manually
- update/delete/done actions on queue (v1 mesh scope = create only)
