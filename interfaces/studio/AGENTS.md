# interfaces/studio/ — Browser Dashboard

**Score:** 9 (7 files, 71% code, 53 module-level symbols, 40 exports)
**Role:** the only browser-facing surface — FastAPI backend + vanilla-JS SPA.

## OVERVIEW

`server.py` builds a single FastAPI app on top of the existing
`TaskdogAdapter` (`src.mesh.adapters.taskdog`), HTTP-first with a SQLite
fallback. The frontend is `index.html` + `styles.css`: no build step, no
framework, no bundler.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| App factory | `server.py::create_app` | builds the app; `app` is the module-level instance |
| Request bodies | `server.py::CreateTaskBody`, `ChatBody` | local strict Pydantic, not in `src/contracts/` |
| Static assets | `index.html`, `styles.css` | served by `GET /` and `GET /static/{path}` |
| Tests | `tests/test_studio.py` | FastAPI `TestClient` through the `client` fixture |

## ENDPOINTS

```
GET  /                        static index.html
GET  /api/tasks               list tasks via TaskdogAdapter
POST /api/tasks               create task (apply_change)
POST /api/tasks/{ueid}/done   mark done (TaskAction.DONE)
POST /api/chat                proxy to the LangGraph API
GET  /api/metrics             drift-net snapshot + daemon status (best effort)
```

## CONVENTIONS

- `create_app()` is a factory, not a module global: the `client` fixture builds
  a fresh app per test. `main()` runs uvicorn programmatically.
- Chat is best-effort: when the LangGraph API is unreachable the endpoint
  returns 503 with a structured error instead of raising.
- The drift-net block reads the heartbeat JSON when present and otherwise
  synthesises `{"drift_pass": true, "skipped": true}`, so tests need no
  running daemon.
- The `sys.path` bootstrap (repo root + `src`) happens at module import,
  before the `src.mesh...` imports, with `# noqa: E402`.
- Env knobs: `STUDIO_HOST` (127.0.0.1), `STUDIO_PORT` (8765),
  `STUDIO_LANGGRAPH_API` (http://127.0.0.1:2027), `STUDIO_CHAT_TIMEOUT` (30),
  `STUDIO_HEARTBEAT`.

## ANTI-PATTERNS

- Never write `vault/` from Studio. State changes go through the mesh
  adapters and `apply_change` only.
- Never add a task schema to `src/contracts/` from here; use the local models.
- Never let a missing dependency raise at import time. Studio exits with an
  install hint when FastAPI is absent; every other endpoint failure degrades
  to a structured payload.

## TESTS

`tests/conftest.py` provides `tmp_data_dir` (patches `TASKDOG_DB` and sets
`TASKDOG_HTTP_ENABLED=0` to force the SQLite path) and `client`.

## COMMANDS

```bash
python -m interfaces.studio.server        # http://127.0.0.1:8765
pytest interfaces/studio/tests -v
```
