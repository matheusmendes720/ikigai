# TESTS/GATEWAY/CLIENTS

## OVERVIEW

Exercises fork MCP servers through real subprocesses and hand-rolled JSON-RPC framing.
Covers calendar and tuiboard tool payloads plus the boundary that keeps forks out of vault I/O.

**Role:** fork MCP E2E — a real server subprocess plus hand-rolled JSON-RPC against the `solverforge_calendar` and `tuiboard` fork servers (7 tools total).

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| JSON-RPC framing helpers | `test_solverforge_calendar_init.py` | `_send_request` / `_read_response` — imported by 7 sibling modules |
| Calendar fork tools | `test_sf_availability.py`, `test_sf_schedule.py`, `test_sf_replan.py` | `sf_availability`, `sf_schedule`, `sf_replan` |
| Tuiboard fork tools | `test_tuiboard_init.py`, `_aggregate.py`, `_render.py`, `_snapshot.py`, `_diff.py` | `tuiboard_aggregate/render/snapshot/diff` |
| Fork vault-write conformance | `test_vault_write_conformance.py` | forks must not reference `vault` at all |
| Subprocess harness | `conftest.py` | `server_process_factory` + `skip_if_no_module` |

## CONVENTIONS

- **Real subprocess, hand-rolled JSON-RPC** (spec §10, "B5.B pattern"). The server is `python -m <module>` with `PYTHONPATH=<repo>:<repo>/src:<repo>/src/ikigai/src`; the transport is never mocked — the wire protocol is the thing under test.
- **`bufsize=0` on `Popen` is mandatory** — buffered pipes break the header/body framing on Windows.
- **`Content-Length`-framed, not newline-delimited.** `_send_request` writes `Content-Length: N\r\n\r\n` + the JSON body; `_read_response` parses headers, then reads exactly N bytes. A newline-JSON assumption fails here.
- **The helper pair is shared, so edits ripple.** `_send_request` / `_read_response` live in `test_solverforge_calendar_init.py` and are imported by `test_sf_availability`, `test_sf_replan`, `test_sf_schedule`, `test_tuiboard_render`, `test_tuiboard_snapshot`, `test_tuiboard_diff` and `test_tuiboard_init`; `test_tuiboard_aggregate` imports them from `test_tuiboard_init` instead.
- **This directory is a package** (`__init__.py` present), so sibling imports use the dotted `tests.gateway.clients.<module>` path.
- **MCP absence is a skip, not a failure.** `skip_if_no_module` plus `pytest.skip` on `ImportError` / `ModuleNotFoundError` / `EOFError` / `OSError` / `TimeoutError`.
- **Tool payloads are asserted, not just the handshake** — `sf_availability` returns `free_slots` / `busy_intervals`, `tuiboard_aggregate` returns `task_count` and per-source counts, `tuiboard_diff` returns `affected_ueids`.

## ANTI-PATTERNS

- **Forks must never touch `vault/` directly.** `test_vault_write_conformance.py` scans `src/solverforge_calendar` and `src/tuiboard` for `from ...vault import`, `import ...vault`, `"vault/` and `vault_read|vault_write`. `vault_write` (the Layer-1 MCP) is the only writer.
- **Never assert-fail because a fork server is missing** — skip, after the CLI wiring and parse/diff checks pass.
- **Never swap the real subprocess for a mock transport** — that would delete the coverage this suite exists for.
- **Never leak the server process.** `server_process_factory` terminates on exit (2 s grace, then kill); a leaked server holds the stdio pipe.
- **Never send a network request** — the fork servers are local subprocesses; the notification channel is stubbed via `PATH` in the sibling shell suite.

## COMMANDS
```bash
pytest tests/gateway/clients/ -v
pytest tests/gateway/clients/test_vault_write_conformance.py -v
```
