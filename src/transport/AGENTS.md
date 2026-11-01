# AGENTS.md — `src/transport/`

**Score 7 (2 modules, 100% code, ~215 LOC, 6 tools) — created: distinct domain (the only surface a client speaks).** MCP over the service layer.

## OVERVIEW
Exactly six tools, each expressing one domain intent. A tool that exposed a table would be a database RPC with a nicer name. The transport holds **no persistence logic and no queries of its own** — it turns intent into a service call and turns the service's typed errors back into something the agent can act on. The harness is external (ADR-037 D7): this module is the tool surface, not a framework around an agent.

## WHERE TO LOOK
| Item | Where |
|---|---|
| The six tools | `mcp_server.py` — `search_artifacts`, `get_artifact`, `upsert_artifact`, `delete_artifact`, `list_relations`, `embed_text` |
| The server instance | `mcp = FastMCP("ikigai-data")` |
| Wiring | `Services` dataclass, `build_services()`, `get_services()`, `set_services()` |
| Transport selection | `resolve_transport()` — reads `IKIGAI_MCP_TRANSPORT` (ADR-011) |
| Entry point | `main()` → `mcp.run(transport=...)` |

## CONVENTIONS
- **The surface is exactly six tools and it is drift-guarded.** The transport test asserts the set of registered tool names and asserts that every tool carries a description.
- **A tool must contain no SQL.** The test greps `mcp_server.py` for `select|insert|update|delete` and fails on any hit — the surface is the services, not the database.
- **Typed domain errors cross the boundary as a `RuntimeError` whose message starts with the error code.** `_translate_errors` wraps every tool; `_tool_error` renders `"<code>: <message> (<detail>)"` from `DataLayerError.to_dict()`. The four codes — `conflict`, `validation`, `forbidden`, `not_found` — must stay distinguishable: a conflict means reread, a validation failure means fix the payload, a forbidden means stop, a missing artifact means check the UID.
- **Tool docstrings are PT-BR and are part of the contract** — they are what the calling model reads to decide which tool to reach for.
- **`get_services()` builds the wiring once per process and caches it; `set_services()` replaces it.** Tests, and any bootstrap that injects a client, use `set_services`.
- **The transport is selected by env, not by code.** `stdio` (local), `http` → `streamable-http`, `sse`. Host and port come from FastMCP's own settings (`FASTMCP_HOST` / `FASTMCP_PORT`).

## ANTI-PATTERNS
- **Never add a seventh tool without updating the drift test.** The expected set lives in `src/ikigai/tests/transport/test_mcp_tools.py`; a new tool is a contract change, not a convenience.
- **Never let a tool reach past the service.** No `DataClient`, no `ArtifactRepository`, no SQL in a tool body.
- **Never let the transport decide domain policy.** Validation, versioning and idempotency belong to `src/services/`; the transport translates.
- **Never drop the error translation.** A raw `DataLayerError` reaching the client collapses conflict / validation / forbidden / not-found into one behaviour — exactly what `src/contracts/errors.py` exists to prevent.
- **Never put credentials in this module.** The store DSN comes from the environment (`IKIGAI_STORE_DSN`).

## COMMANDS
```bash
python -m src.transport.mcp_server                          # stdio by default
IKIGAI_MCP_TRANSPORT=http python -m src.transport.mcp_server
```

## NOTES
- `src/services/` is the only layer clients reach (ADR-037 §6 rule 2); this module is its only caller.
- The wiring chain is `DataClient` → `ArtifactRepository` → `ArtifactService` / `RelationService` / `EmbeddingService`.
