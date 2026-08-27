# Spec: End-to-End Integration Smoke Test

**Status:** Proposed
**Date:** 2026-08-27
**Owner:** IKIGAI
**Related work:** Tasks 1, 2, 4, 5 (the full observability stack)

## Goal

A single command (e.g. `pav smoke observability`) that:

1. Boots IKIGAI MCP server + the 3 external MCP servers (tuiboard, taskdog, solverforge-calendar) with `OTEL_ENABLED=true`
2. Invokes a representative tool from each interface
3. Verifies spans appear in **both LangSmith and Langfuse** for all 4 interfaces
4. Reports PASS/FAIL with span counts per backend

## Background

We have:
- ✅ All 4 servers emit spans when `OTEL_ENABLED=true`
- ✅ Dual export wired (LangSmith + Langfuse) in all 3 externals (verified by Task 1a fix `2c39867`, Task 1b `5a8b1bb2`, Task 1c `064b8c9`)
- ✅ IKIGAI server-side tracing (Task 5, `0e528d0`)
- ❌ No integration test that proves the spans actually reach the backends

Without this spec, "OTel is working" is a code-side claim, not an observed fact.

## Proposed approach

A Python test script that orchestrates the 4 servers and queries LangSmith + Langfuse APIs to verify span receipt.

### Components

1. **Process manager** — `smoke/observability/process_manager.py`
   - Boots each server as a subprocess with `OTEL_ENABLED=true` + a unique `LANGSMITH_PROJECT=smoke-<run_id>` so spans are easy to query
   - Waits for each server's `initialize` handshake to complete
   - Captures stdout/stderr for diagnostics

2. **Tool invocation** — `smoke/observability/invoker.py`
   - For each interface, invoke 1 read tool + 1 write tool:
     - IKIGAI: `ikigai_score(thread_id=smoke-test)` (read), `ikigai_checkpoint(action="get", thread_id=smoke-test)` (read)
     - tuiboard: `board.list` (read), `board.tasks.get` (read)
     - taskdog: `task_query.list` (read), `task_crud.create` (write — but with idempotency_key)
     - solverforge-calendar: `events_list` (read), `events_create` (write — with idempotency_key)
   - Captures response time + tool.name + duration_ms for assertion

3. **Backend verification** — `smoke/observability/verifier.py`
   - Polls LangSmith API (`/v1/projects/{name}/runs`) for new spans in the last 60s
   - Polls Langfuse API (`/api/public/traces`) similarly
   - Asserts: ≥ 1 span per interface per backend, ≥ 1 span has the expected `tool.name` attribute

4. **Reporter** — `smoke/observability/reporter.py`
   - Prints a table: server | LangSmith spans | Langfuse spans | PASS/FAIL
   - Saves JSON to `logs/smoke-observability-<run_id>.json` for trend tracking

### Run modes

| Mode | Command | Use case |
|---|---|---|
| Full | `pav smoke observability` | CI gate (every PR) |
| Fast | `pav smoke observability --fast` | Local dev (skip LangSmith poll, check Langfuse only) |
| Dry | `pav smoke observability --dry` | Local dev (boot servers, don't query backends) |

### Acceptance criteria

1. `pav smoke observability` exits 0 when both backends receive spans
2. Output is a clean ASCII table (no JSON unless `--json`)
3. Runs in ≤ 90 seconds (full mode) and ≤ 30 seconds (fast mode)
4. Cleanup: subprocesses terminated, no zombie processes, no leaked SQLite DBs
5. Detects common failures: missing API keys, server crash on boot, network timeout to backend, span attribute mismatches

### Out of scope

- Load testing (separate spec)
- Span shape validation (separate spec — relies on a JSON schema registry)
- Cost attribution (which tool costs the most in LangSmith traces)
- CI integration (separate spec — needs GitHub Actions wiring)

## Risks

1. **API rate limits** — LangSmith free tier: 100 traces/day. Mitigation: gate smoke test on `LANGSMITH_API_KEY` set; otherwise skip LangSmith check.
2. **Latency** — polling adds ~5s to verify. Mitigation: poll with 2s backoff, fail-fast at 60s.
3. **Flakiness** — external APIs can be flaky. Mitigation: retry the verify step up to 3 times with 10s gaps.
4. **Cross-platform** — process management differs between Windows + Linux. Mitigation: use `subprocess.Popen` with portable flags; CI runs on Linux, local on Windows.

## Open questions

1. Should the smoke test write to a shared `smoke-test` project in LangSmith, or create a new project per run?
2. Should the smoke test be a Typer command under `pav`, or a standalone script under `scripts/`?
3. Should it support `--record` mode that saves a video of the run for debugging flakes?

## Implementation order

1. **Phase 1**: process manager + invoker (1 day)
2. **Phase 2**: backend verifier (1 day)
3. **Phase 3**: reporter + Typer command (0.5 day)
4. **Phase 4**: CI wiring (1 day, depends on .github/workflows/ setup)

Estimated effort: ~3.5 days.

---

*Spec generated 2026-08-27 as part of the observability follow-up work.*
