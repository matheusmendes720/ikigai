# ADR-021 — Default-Deny External Folder Access

> **Status:** Accepted
> **Promoted from:** Plan B: `docs/superpowers/plans/2026-09-03-external-folder-access-plan-b.md` (SHIPPED 2026-09-03)
> **Deciders:** matheus (project owner)
> **Drift invariant:** `test_canonical_scope.py::check_external_access_bounds` (invariant i)

---

## Context

The Deep Agent v2 must be able to ingest pre-form investigation data — CSVs, raw research notes, logs — from outside the `vault/` directory without gaining arbitrary filesystem access. The agent layer sits at a security boundary: it reads from configured external roots but must never escape into unrelated filesystem locations. A path-traversal vulnerability in this ingestion path would allow data exfiltration from arbitrary filesystem locations.

Three alternatives were considered:

1. **Default-allow with audit** — read from any folder, log every access. Rejected because it provides no preventive guard; data exfiltration is only discovered after the fact.
2. **No external access at all** — restrict the agent entirely to `vault/`. Rejected because it prevents ingestion of legitimate pre-form data (investigation files, raw research, third-party CSVs) that lives outside the vault.
3. **Default-deny with explicit allowlist** — the chosen path. The agent can only read from explicitly configured roots; all other paths are rejected by construction.

---

## Decision

- **Default = deny.** `external_roots.yaml` starts empty; no external folder is accessible without explicit configuration.
- **Configuration:** `ExternalRootsConfig` — a Pydantic v2 frozen schema stored in `config/external_roots.yaml`. Users must edit this file to add allowed roots.
- **Path traversal guard:** `path_traversal_guard()` (in `src/ikigai/src/ikigai/security/path_traversal_guard.py`) enforces 4 attack vectors:
  1. `../` — parent directory escape
  2. Absolute paths outside allowlist
  3. Symlink chains pointing outside allowlist
  4. Null byte injection in paths
- **Single MCP surface:** `external_folder_read()` is the only public external-folder interface. It validates the path against `path_traversal_guard` before any disk access.
- **Read-only:** `external_folder_read` never writes to external files. `ExternalRoot.read_only=True` is frozen in the schema; opting out requires explicit override.
- **Audit log:** every call appends to `.external_audit.log` at the root folder with `actor=X folder=Y pattern=Z limit=N result_count=K`.
- **Drift invariant (i):** `test_canonical_scope.py::check_external_access_bounds` enforces that `external_roots.yaml` parses as valid YAML, configured roots exist on disk, and the audit log is well-formed. This prevents configuration drift from silently disabling the guard.
- **No symlink chains outside allowlist:** even if a path resolves within an allowed root, a symlink whose target escapes the root is rejected (`SymlinkEscapeError`).

---

## Consequences

### Positive

- **Security boundary enforced by construction:** default-deny means the system is secure by default, not by audit-after-the-fact.
- **Configurable:** users explicitly opt in to each external root; no accidental exposure.
- **Auditable:** every read is logged with actor, path, pattern, and result count.
- **Drift-resistant:** invariant (i) blocks config corruption from silently weakening the guard.

### Negative

- **Onboarding friction:** to read from a new external folder, users must edit `config/external_roots.yaml` — no dynamic registration.
- **Config file required:** `config/external_roots.yaml` must exist (even if empty); the tool raises `EmptyAllowListError` on use when no roots are configured.
- **Audit log freshness not enforced:** stale audit logs (>24h) are advisory only; the invariant does not hard-fail on them.

---

## Attack Vectors Rejected

The following 4 attack vectors are rejected verbatim per Plan B §Path Traversal Guard:

1. `../` — parent directory escape
2. Absolute paths outside allowlist
3. Symlink chains pointing outside allowlist
4. Null byte injection in paths

---

## Cross-References

- Plan B spec: `docs/superpowers/plans/2026-09-03-external-folder-access-plan-b.md`
- Plan B review: `.git/sdd/plan-b-external-folder-access-final-review.md`
- Drift invariant (i): `test_canonical_scope.py::check_external_access_bounds`
- ADR-013 (planner-only scope): `code-docs/adr/ADR-013-canonical-scope-discipline.md`
- Path traversal guard implementation: `src/ikigai/src/ikigai/security/path_traversal_guard.py`
- MCP tool: `src/ikigai/src/mcp_server/external_folder_read.py`
- Config schema: `src/contracts/external_roots_config.py`
