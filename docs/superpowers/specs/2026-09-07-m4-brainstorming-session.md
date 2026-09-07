# Brainstorming Session — M4 (LangGraph Integration) Next-Loop Sequence

**Date:** 2026-09-07
**Session ID:** b68ccbb3-90ce-43cf-99b1-7bf9d64c7c49
**Trigger:** User prompt — "lets scaffold next sequence loop .. to steps remaining to build... preciso dessa aplicacao pronta apra uso??"

## Strategic question resolved

User asked simultaneously:
1. "scaffold next sequence loop .. to steps remaining to build" → continue M4–M9
2. "preciso dessa aplicação pronta pra uso??" → do I actually need this app ready for use?

Resolution (user verbatim): *"eu quero continuar desenvolvendo a aplicacao ... use o loop de desenvolvimento para continuar a sessao continua"* → continue development, use the dev loop, keep session continuous.

Implication: M4–M9 stays on the roadmap; loop-tick stays as the orchestrator; no pivot to "stop building" or "audit what exists".

## Approach picked

**Option A — Execute M4 to completion** (T-4.1..T-4.5 as the next continuous loop).

Rejected:
- **B (skip M4, jump to M5)** — loses `--graph` flag deliverable that M9 depends on; abandons already-committed SPEC at `acb22e8`.
- **C (bundle M4+M5+M6)** — violates YAGNI; harder rollback if any one fails.

## Design recap

Full design lives at [`specs/M4-langgraph-integration/SPEC.md`](../../../../specs/M4-langgraph-integration/SPEC.md) (committed at `acb22e8`). Summary of 5 sections approved by user this session:

1. **Architecture** — 3 graphs as orchestrator sub-tools + cron entrypoint via `--graph` flag, sharing `.swarm/langgraph_checkpoint.db`.
2. **Components** — orchestrator prompt refactor + loop-tick.sh flag + SqliteSaver shared path + 5/5 integration tests + closeout state-machine.
3. **Data flow** — cron path bypasses orchestrator LLM; orchestrator path uses same factory + checkpoint DB; thread_id per-tick.
4. **Error handling** — graph factory raise → non-zero exit; checkpoint lock → retry; drift regression → caught by tests; orchestrator confused → additive tools preserve existing surface.
5. **Testing** — 5/5 M4 tests + 11/11 loop-infra + 33/33 canonical_scope + drift green + 68/68 interfaces.

## Out-of-scope (deferred per SPEC)

- v2 node MCP wiring (Phase 8.2)
- PAE math revival (PAV archived per ADR-013, drift invariant Wave h enforces non-regression)
- Rebuilding the 4 missing graphs (`quarterly_replan` / `correction_protocol` / `dream_falsification` / `test_de_fogo_rollup`)

## Next step

Invoke `superpowers:writing-plans` to create the implementation plan at `specs/M4-langgraph-integration/PLAN.md`, then loop-tick executes T-4.1..T-4.5.
