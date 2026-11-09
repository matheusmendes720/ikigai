# AGENTS.md — `src/transport/`

**Score 7 (3 modules, 100% code, ~560 LOC, 6 tools) — created: distinct domain (the only surface a client speaks).** MCP over the service layer, and the websocket beside it.

## OVERVIEW
Exactly six tools, each expressing one domain intent. A tool that exposed a table would be a database RPC with a nicer name. The transport holds **no persistence logic and no queries of its own** — it turns intent into a service call and turns the service's typed errors back into something the agent can act on. The harness is external (ADR-037 D7): this module is the tool surface, not a framework around an agent.

**The websocket (ADR-039) is a second surface, not a second set of tools.** It
exposes the SAME six, built from the MCP server itself, and it carries the
changes the store announces. The MCP transport is untouched.

## WHERE TO LOOK
| Item | Where |
|---|---|
| The six tools | `mcp_server.py` — `search_artifacts`, `get_artifact`, `upsert_artifact`, `delete_artifact`, `list_relations`, `embed_text` |
| The server instance | `mcp = FastMCP("ikigai-data", host=transport_host(), port=transport_port())` |
| Wiring | `Services` dataclass, `build_services()`, `get_services()`, `set_services()` |
| Transport selection | `resolve_transport()` — reads `IKIGAI_MCP_TRANSPORT` (ADR-011) |
| Entry point | `main()` → `mcp.run(transport=...)` |
| The websocket | `ws_server.py` — `Router`, `build_app()`; `WS /sync` and `GET /healthz` |
| The websocket's tool registry | built FROM the MCP server — `Router.load_tools()` |
| The healthcheck | `healthcheck.py` — the data plane, for any transport (`--host`/`--port`) |

## CONVENTIONS
- **The surface is exactly six tools and it is drift-guarded.** The transport test asserts the set of registered tool names and asserts that every tool carries a description.
- **A tool must contain no SQL.** The test greps `mcp_server.py` for `select|insert|update|delete` and fails on any hit — the surface is the services, not the database.
- **Typed domain errors cross the boundary as a `RuntimeError` whose message starts with the error code.** `_translate_errors` wraps every tool; `_tool_error` renders `"<code>: <message> (<detail>)"` from `DataLayerError.to_dict()`. The four codes — `conflict`, `validation`, `forbidden`, `not_found` — must stay distinguishable: a conflict means reread, a validation failure means fix the payload, a forbidden means stop, a missing artifact means check the UID.
- **Tool docstrings are PT-BR and are part of the contract** — they are what the calling model reads to decide which tool to reach for.
- **`get_services()` builds the wiring once per process and caches it; `set_services()` replaces it.** Tests, and any bootstrap that injects a client, use `set_services`.
- **The transport is selected by env, not by code.** `stdio` (local), `http` → `streamable-http`, `sse`.
- **The bind address is resolved HERE, not by FastMCP.** FastMCP takes the host as a constructor argument and reads nothing from the environment — `mcp.run()` accepts only the transport, and the default host is the loopback. `transport_host()` and `transport_port()` read `FASTMCP_HOST` / `FASTMCP_PORT` and are handed to the constructor, so the server and the healthcheck cannot drift apart. A container that set the env and trusted the library would get a server no other container can reach.

## ANTI-PATTERNS
- **Never add a seventh tool without updating the drift test.** The expected set lives in `src/ikigai/tests/transport/test_mcp_tools.py`; a new tool is a contract change, not a convenience.
- **Never let a tool reach past the service.** No `DataClient`, no `ArtifactRepository`, no SQL in a tool body.
- **Never let the transport decide domain policy.** Validation, versioning and idempotency belong to `src/services/`; the transport translates.
- **Never drop the error translation.** A raw `DataLayerError` reaching the client collapses conflict / validation / forbidden / not-found into one behaviour — exactly what `src/contracts/errors.py` exists to prevent.
- **Never put credentials in this module.** The store DSN comes from the environment (`IKIGAI_STORE_DSN`).
- **Never give the websocket its own tool list.** Its registry is built from the MCP server (`Router.load_tools()`), and the test holds the two equal. A second list is a list that drifts.
- **Never let the websocket write without the token.** `IKIGAI_WS_TOKEN` is required; without it the server refuses to start. A write channel with no secret is a public write channel.
- **Never put SQL in the websocket.** The store's announcements arrive through `src/services/changes.py`; the transport forwards them.

## COMMANDS
```bash
python -m src.transport.mcp_server                          # stdio by default
IKIGAI_MCP_TRANSPORT=http python -m src.transport.mcp_server
FASTMCP_HOST=0.0.0.0 FASTMCP_PORT=8000 IKIGAI_MCP_TRANSPORT=http \
  python -m src.transport.mcp_server                        # what a container runs

IKIGAI_WS_HOST=0.0.0.0 IKIGAI_WS_PORT=8001 IKIGAI_WS_TOKEN=… \
  python -m src.transport.ws_server                         # the sync channel
```

## ANTI-PATTERNS (the bind address)
- **Never let the server bind the loopback in a deployment.** `FASTMCP_HOST=0.0.0.0` is what the compose sets; the default is the loopback because a service must not be exposed by accident.
- **Never make the healthcheck dial the bind host.** A server bound to `127.0.0.1` also answers a connection to `0.0.0.0` — the kernel resolves it to the loopback — so the check would pass on a service no client can reach. The healthcheck dials the address a client uses.

## NOTES
- `src/services/` is the only layer clients reach (ADR-037 §6 rule 2); this module is its only caller.
- The wiring chain is `DataClient` → `ArtifactRepository` → `ArtifactService` / `RelationService` / `EmbeddingService`.
