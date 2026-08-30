# ADR-012 — Fork-Connection Architecture (solverforge-calendar + tuiboard)

**Status:** Accepted 2026-08-30
**Date:** 2026-08-30
**Deciders:** Matheus Mendes + Claude (assistant)
**Consulted:** `docs/superpowers/specs/2026-08-30-fork-connection-architecture.md` (spec commit `7aa02bf` + decisions `d33c71d`); `docs/superpowers/specs/2026-08-30-fork-connection-architecture-Q-expanded.md` (Q1-Q6 resolved: beta/iota/alpha/iota/gamma/I+III)
**Informed:** backend operators, future fork integrators
**Scope:** architectural pattern for connecting external forks (solverforge-calendar, tuiboard, future) to the UnifiedMCPGateway

---

## Context

Phase B7 (Agent Layer Activation) shipped and made the IKIGAi backend+data+agent layers functional. Diagnostic revealed that the solverforge-calendar and tuiboard fork factories existed at `src/ikigai/src/ikigai/gateway/clients/{solverforge_calendar,tuiboard}.py` but the MCP server modules did NOT exist (both were factory stubs). taskdog (the 3rd fork) was already wired via external repo + HTTP.

The unification question: how do we make solverforge-calendar + tuiboard reachable via the UnifiedMCPGateway like taskdog is, without breaking the existing pattern?

## Decision

Build in-repo Python MCP servers using hand-rolled JSON-RPC 2.0 over stdio:

1. **Repo layout:** Both forks in-repo (`src/solverforge_calendar/`, `src/tuiboard/`)
2. **Transport:** Hand-rolled JSON-RPC 2.0 (no FastMCP, no new dependencies)
3. **Auth:** None (localhost-only is sufficient for personal OS)
4. **Event log:** Single append-only JSONL at `data/gateway/events.jsonl`
5. **Tool versioning:** YAGNI (no version suffix in v1)
6. **vault_write conformance:** Docs + grep test (no runtime enforcement)

Plus:
- **Cross-fork storage adapter pattern:** `src/mesh/adapters/{cli,taskdog,solverforge_calendar}.py` — separate concern from MCP factory. Each adapter implements `ForkAdapter` Protocol (name/read/apply_change/supports_field). tuiboard has NO storage adapter (rendering fork only).
- **UEID canonical join key:** 5-part regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$`, UPSERT on ueid.
- **Aggregator 3-fork precedence:** taskdog > solverforge-calendar > cli (dict.update() in reverse precedence order; highest writes last, wins on collision).

## Consequences

### Positive

- Single `git clone && uv sync && pytest` for full development
- Zero new dependencies; reuses existing Pydantic v2 + stdlib
- Tests always run (no external path dependencies)
- Reversible: most decisions (especially #1, #2, #5) can be revisited without major rework
- Hand-rolled transport keeps fork surface small (~100-200 LOC per server)

### Negative

- Cross-repo refactors (e.g., extracting `solverforge_calendar` to its own repo) require `git mv` + factory update
- Hand-rolled transport means re-implementing capability negotiation if we add it later
- No auth means any local process can call the gateway (acceptable per threat model)
- Multiple Python subprocesses (one per fork) increases process count vs single-process gateway

### Neutral

- tuiboard has zero storage adapter (rendering fork only) — kept by design
- Fork connection does NOT touch any algorithm/scoring/qhe/regime code (per algorithm-gate)
- v1 scope = `create` action only (per Phase 3 v1 mesh); update/delete/done deferred to v1.2+

## Alternatives Considered

- **External repos for forks** (mirror taskdog): rejected — adds onboarding cost, CI skip-if-missing, breaks "fully local" invariant
- **FastMCP per fork**: rejected — ~30 transitive deps per fork for ~3 tools; SDK doesn't add much over hand-rolled for small surfaces
- **Auth via shared secret**: rejected — YAGNI; localhost isolation is sufficient
- **Single shared Python process for all forks**: rejected — increases coupling; subprocess isolation is the right boundary for crash isolation
- **SSE for transport** (instead of stdio): rejected per ADR-011 — stdio is sufficient for in-process subprocess spawning; SSE reserved for external HTTP clients

## References

- Spec: `docs/superpowers/specs/2026-08-30-fork-connection-architecture.md`
- Companion Q-expanded: `docs/superpowers/specs/2026-08-30-fork-connection-architecture-Q-expanded.md`
- Plan: `docs/superpowers/plans/2026-08-30-fork-connection-implementation.md`
- Diagnostic correction: `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/fork-connection-diagnostic-correction-2026-08-30.md`
- Companion ADR: `code-docs/adr/ADR-011-ikigai-mcp-http-sse-transport.md` (transport-layer decision; this ADR is fork-integration layer)
