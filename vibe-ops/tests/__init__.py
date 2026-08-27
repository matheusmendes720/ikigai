"""Vibe-ops test suite.

Contains:
- Unit tests for entities (period_report, pae_state, pae_nodes, etc.)
- Integration tests for SQLite-backed sync + PAE graph orchestration.
- Property tests for invariants (Hypothesis-driven).
- E2E tests for full pipeline execution against synthetic fixtures.
"""