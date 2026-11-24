---
name: store-read
description: Use when the agent must find artifacts, read one, or follow the relation graph. Searches with kinds, quarter, status, a date window and cursor, then reads the prose with get_artifact and walks the edges with list_relations.
---

# Store read

Finds and reads artifacts through the MCP transport. Read-only: it writes no artifact, no relation and no file.

## Contract

Trigger:    The agent must find artifacts, read one, or follow the graph.
Inputs:     A kind filter, a quarter, a status, a parent uid, a text, a window of dates, or a uid.
Outputs:   The artifacts found, the artifact read with its relations and neighbours, or the edges at a node. When nothing matches, the report says what was searched for.
Steps:
1. Narrow with `search_artifacts` before fetching anything. The query carries `text`, `kinds`, `quarter`, `status`, `parent_uid`, `since`, `until`, `semantic`, `limit` and `cursor`. The limit goes from 1 to 200 and defaults to 20. `since` and `until` bound a window on `updated_at` and are ISO 8601 timestamps that carry an offset: `2026-06-01T00:00:00+00:00` and `2026-06-30T23:59:59+00:00` are the month of June. The window is CLOSED on both ends, so an artifact touched exactly at a bound is inside it; `since` alone means from then on, `until` alone means up to then, and neither means the whole store. The result is the IDENTITY of each hit — uid, kind, title, quarter, status, parent, revision, the path it came from — and NOT its prose (ADR-046).
2. Page with the cursor. The cursor is opaque: take `next_cursor` from the result and pass it back verbatim. Never construct one. A windowed search pages with the window and the cursor TOGETHER: the cursor says where the last page stopped on `updated_at`, and only `since` and `until` say where it was allowed to stop.
3. Read one artifact with `get_artifact` and the depth you need. Depth 1 returns the artifact, its relations and its immediate neighbours; depth 0 returns the artifact and its edges without expanding the neighbours. The PROSE is here and not in the search: depth 0 is the cheap read of what an artifact SAYS.
4. Walk the graph with `list_relations`. Narrow with the relation type when the edge type matters. Keep a visited set so a cycle terminates.
5. Report the fields that came from where, and name the source of each one.

Invariants:
- This skill is read-only. It writes no artifact, no relation and no file.
- **The search does not carry the body.** A report that says what an artifact says reads it with `get_artifact` first — and says which call it came from.
- **The date window is the axis the search already sorts on.** `updated_at` bounds it and pages it, so a window and a cursor cannot disagree about which rows are newer. One bound is enough; a `since` later than its `until` asks for nothing and is refused before the store is read.
- An artifact missing from one place is reported as missing. It is not reconstructed from a neighbour.
- The uid format is defined once, in `src/contracts/common.py`.
- A read that returns nothing is an answer. Say that nothing matched and what was searched for.

Done when:
- every requested field is reported with its source,
- or the report states that the uid exists nowhere, with the search that showed it.
