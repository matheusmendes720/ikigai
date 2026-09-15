# Risk Tier Classifier

Determine the risk tier for a given commit hash based on changed files.

## Tier classification

### LOW risk
- Only `tests/` or `docs/` paths changed
- Drift net tests added/modified
- Doc-only commits
- Memory/markdown updates
- Bookkeeping commits
→ Standard 5-dim review (correctness/minimality/coherence/safety/reversibility)

### MEDIUM risk
- Single production source file changed
- No infra files touched
- Drift net preserved
→ Standard 5-dim + sanity check: "could this break existing functionality?"

### HIGH risk
- Multi-file production changes
- Infrastructure changes (loop-tick.sh, loop-tick.ts, daemon, .claude/loop/, .github/)
- Schema or contract changes
- Security-related
→ Standard 5-dim + security audit + rollback plan review

## Usage

```bash
git diff --name-only <base_sha>..HEAD
```

If any infra pattern (`.claude/loop/*.sh`, `.claude/loop/*.ts`, `.github/`, `Dockerfile*`):
→ HIGH tier
If only `tests/` or `docs/` paths:
→ LOW tier
Otherwise:
→ MEDIUM tier