## Pull Request

### What does this PR do?
<!-- 1–3 sentence description -->

### Related issue
<!-- Fixes #(issue) or Relates to #(issue) -->

### Type of change
<!-- Check all that apply -->
- [ ] Bug fix
- [ ] New feature
- [ ] Refactoring
- [ ] Documentation
- [ ] Infrastructure / CI-CD

### Subsystem
<!-- Which part of the codebase. The published tree: transport → services → data. -->
- [ ] `src/contracts/` — the DOM and the versioned SQL
- [ ] `src/data/` — the store client
- [ ] `src/services/` — the domain rules
- [ ] `src/transport/` — the MCP transport and the healthcheck
- [ ] `src/bot/` — the Telegram client
- [ ] `src/ikigai/` — the package and the canonical suite
- [ ] `specs/` — the harness contract and the planning tree
- [ ] `deploy/` — the container
- [ ] `.github/` — CI and the review scripts
- [ ] documentation
- [ ] other: ___

### How to test
<!-- Step-by-step to verify this works. The ONE published environment is src/ikigai/. -->
1.
2.
3.

```bash
# The repository root has no Python project: the environment lives in src/ikigai/
cd src/ikigai && poetry install && poetry run pytest -m "not e2e"
cd src/ikigai && poetry run ruff check src/ && poetry run ruff format --check src/
cd src/ikigai && poetry run mypy -p src.ikigai.src
```

### Acceptance criteria
<!-- What defines "done"? A falsifiable PASS, not a promise. -->
- [ ]
- [ ]

### Migration notes (if any)
<!-- DB schema changes? Config changes? New env vars? -->

### Screenshots (if UI change)
<!-- Before / after -->
