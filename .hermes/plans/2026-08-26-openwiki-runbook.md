# OpenWiki RUNBOOK — execute the docs restructure

**Status (2026-08-26):** All scaffolding is in place. The actual `openwiki --init`
LLM run is blocked on real API keys — you have to provide them, I can't paste
them into chat (security boundary).

**What this runbook does:** walk you through the 4 commands needed to actually
generate the wiki, and what to commit afterwards.

---

## 0. What's already in the repo

Verified by `ls` and `cat` on the working tree:

```
openwiki/
├── INSTRUCTIONS.md         ✅ user-authored brief (scope + append-only rules)
└── .langsmith.json         ✅ LangSmith project list (us region, projects: ikigai, algorithmic-life-os-openwiki)

.openwiki/
└── README.md               ✅ env-var template with REPLACE_ME markers

.github/workflows/
└── openwiki-update.yml     ✅ daily 08:00 UTC cron + manual dispatch, MiniMax + LangSmith

docs/
└── openwiki-visualizer/    ✅ static scaffold (5 files from `openwiki visualize --export`)
                              graph.json is empty (will populate on first --init)

.gitignore                  ✅ excludes .openwiki/ + openwiki/.run.json + .last-update.json.tmp
                              (the generated wiki itself stays tracked)
```

**Not yet committed.** All of the above is in the working tree. You can `git
status` and see it.

---

## 1. Set the secrets locally

You need three real values:

1. `ANTHROPIC_API_KEY` (or `MINIMAX_API_KEY` — same key, both names accepted)
   — the MiniMax API key that the existing `deepagents_harness.py` already
   uses.
2. `LANGSMITH_API_KEY` — from `https://smith.langchain.com/settings/api-keys`.
   **Security note**: per `life-ops/ikigai/.env.example`, a previous key
   (`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`) leaked in
   `~/.claude/history.jsonl:2497` — rotate it at the LangSmith URL above
   before using it in CI.

In your terminal (Windows PowerShell or git-bash):

```bash
# git-bash / MSYS:
cat > ~/.openwiki/.env << 'ENVEOF'
OPENWIKI_PROVIDER=anthropic
ANTHROPIC_BASE_URL=https://api.minimax.io/anthropic
OPENWIKI_MODEL_ID=MiniMax-M2.7-highspeed
ANTHROPIC_API_KEY=<your real MiniMax key here>
LANGSMITH_API_KEY=<your real LangSmith key here>
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=algorithmic-life-os-openwiki
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=algorithmic-life-os-openwiki
OPENWIKI_TELEMETRY_DISABLED=1
ENVEOF

chmod 600 ~/.openwiki/.env
```

```powershell
# Windows PowerShell:
@'
OPENWIKI_PROVIDER=anthropic
ANTHROPIC_BASE_URL=https://api.minimax.io/anthropic
OPENWIKI_MODEL_ID=MiniMax-M2.7-highspeed
ANTHROPIC_API_KEY=<your real MiniMax key here>
LANGSMITH_API_KEY=<your real LangSmith key here>
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=algorithmic-life-os-openwiki
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=algorithmic-life-os-openwiki
OPENWIKI_TELEMETRY_DISABLED=1
'@ | Set-Content -Path "$HOME\.openwiki\.env" -Encoding UTF8
```

`OPENWIKI_TELEMETRY_DISABLED=1` keeps anonymous telemetry off — the README
says it sends reliability telemetry from CI runs by default.

---

## 2. Probe the MiniMax endpoint (30 seconds)

Before spending inference budget on a full repo walk, verify the gateway
responds:

```bash
curl -sL --max-time 10 -X POST "https://api.minimax.io/anthropic/v1/messages" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"MiniMax-M2.7-highspeed","max_tokens":16,"messages":[{"role":"user","content":"ping"}]}'
```

Expected: a JSON response with `"type": "message"`, `"stop_reason": "end_turn"`,
and 1–2 sentences of model output. If you get an auth error, double-check the
key. If you get a model-not-found error, run a list-models call against the
gateway to find the right model id.

If `x-api-key` is rejected, try `X-Api-Key` — MiniMax's error response
("Please carry the API secret key in the 'X-Api-Key' field") suggests
capital-X may be the right header. OpenWiki's anthropic provider uses the
standard Anthropic header (`x-api-key`); if the gateway insists on the
capital-X variant, you'll need to set `OPENWIKI_PROVIDER=openai-compatible`
and use MiniMax's OpenAI-compatible endpoint instead. **At that point, ping
me — I'll switch the workflow + .openwiki/README.md to the OpenAI-compatible
provider path with the correct base URL.**

---

## 3. Run the first-pass generation (10–30 min)

```bash
cd "C:\Users\mathe\code_space\life-oss\life"

# One-shot, exits on success, prints final output:
openwiki code --init --print
```

**What happens:**
- OpenWiki reads `openwiki/INSTRUCTIONS.md` for scope.
- Walks the repo, plans the page queue.
- For each page: runs the planning agent, then the per-page worker agent
  (MCP-mediated), writes the page + Claims sidecar.
- Finalizes `openwiki/index.md` + `openwiki/.last-update.json`.
- Auto-rewrites the `<!-- OPENWIKI:START -->…<!-- OPENWIKI:END -->` block in
  `AGENTS.md` and `CLAUDE.md`.

**Budget expectation:** $2–10 of inference depending on MiniMax pricing,
10–30 minutes wall time.

**Failure recovery:** if it fails mid-run, `openwiki --init` again will
resume the durable page queue (per the README's "resumable page-job
architecture"). `.openwiki/.run.json` (gitignored) tracks in-progress state.

---

## 4. Verify the output

```bash
ls openwiki/                         # should show index.md + quickstart.md + buckets
ls openwiki/architecture/            # system-map.md, etc.
cat openwiki/quickstart.md | head -50
grep -c "OPENWIKI:START" AGENTS.md   # should be 1
grep -c "OPENWIKI:START" CLAUDE.md   # should be 1
```

The `OPENWIKI:START/END` block in `AGENTS.md` and `CLAUDE.md` should look
like:

```markdown
<!-- OPENWIKI:START -->
The full agent-readable documentation lives at `./openwiki/` (OKF v0.2,
Grounded Claims). Start at `openwiki/index.md` → `openwiki/quickstart.md`.
This block is auto-rewritten by `openwiki --update`; do not edit by hand.
<!-- OPENWIKI:END -->
```

**If it didn't write those blocks**, run `openwiki code --update --print`
once more — the first `--init` may have skipped them if it crashed before
finalization.

---

## 5. Re-export the visualizer

```bash
cd "C:\Users\mathe\code_space\life-oss\life"
rm -rf docs/openwiki-visualizer/*
openwiki visualize openwiki --export docs/openwiki-visualizer
git add docs/openwiki-visualizer/
```

This re-populates `docs/openwiki-visualizer/graph.json` with the real node +
edge list, so GitHub Pages can serve a working visualizer.

---

## 6. Commit the bootstrap

```bash
cd "C:\Users\mathe\code_space\life-oss\life"

git add \
  openwiki/INSTRUCTIONS.md \
  openwiki/.langsmith.json \
  openwiki/index.md \
  openwiki/quickstart.md \
  openwiki/architecture/ \
  openwiki/concepts/ \
  openwiki/integrations/ \
  openwiki/operations/ \
  openwiki/testing/ \
  openwiki/workflows/ \
  openwiki/.claims/ \
  openwiki/.last-update.json \
  AGENTS.md \
  CLAUDE.md \
  docs/openwiki-visualizer/ \
  .github/workflows/openwiki-update.yml \
  .gitignore \
  .openwiki/README.md \
  .hermes/plans/2026-08-26-openwiki-docs-restructure.md

git commit -m "feat(docs): bootstrap OpenWiki + pointer blocks in AGENTS.md / CLAUDE.md

- openwiki/INSTRUCTIONS.md — user-authored brief
- openwiki/.langsmith.json — LangSmith project list
- openwiki/architecture, concepts, integrations, operations, testing, workflows
- AGENTS.md + CLAUDE.md: OPENWIKI:START/END pointer block (auto-managed)
- .github/workflows/openwiki-update.yml — daily 08:00 UTC bot, MiniMax + LangSmith
- docs/openwiki-visualizer/ — static Pages export
- .gitignore — exclude .openwiki/ + openwiki/.run.json"
```

---

## 7. Add the CI secrets

For the daily cron bot to work, set two repo secrets at
`https://github.com/matheusmendes720/ikigai/settings/secrets/actions`:

| Secret name | Value |
|---|---|
| `MINIMAX_API_KEY` | Your real MiniMax key (same as `ANTHROPIC_API_KEY` locally) |
| `LANGSMITH_API_KEY` | Your real LangSmith key (after rotating the leaked one) |

`.github/workflows/openwiki-update.yml` references both. Without them, the
bot fails fast with an auth error on the `openwiki code --update` step.

---

## 8. Verify the bot end-to-end

After committing + pushing + setting secrets:

1. Go to `https://github.com/matheusmendes720/ikigai/actions/workflows/openwiki-update.yml`
2. Click "Run workflow" → "Run workflow" (manual dispatch).
3. Wait ~5–15 minutes. Watch the logs.
4. The bot opens a PR titled `docs: update OpenWiki`. Diff = (a) regenerated
   wiki pages, (b) any new Claims, (c) refreshed visualizer export.
5. **Verify nothing in `vibe-ops/`, `strategics/`, cluster docs, or
   `*.SPEC.md` files was touched.** The brief forbids it, but check.
6. Merge. Pages picks up the new visualizer on the next deploy.

---

## 9. Future updates

After the bootstrap, you don't need to run `--init` again — `--update` is
incremental. The daily cron bot handles it.

To force a regeneration outside the cron: `openwiki code --update --print`.

To re-export the visualizer: `openwiki visualize openwiki --export docs/openwiki-visualizer`.

---

## 10. Troubleshooting quickref

| Symptom | Cause | Fix |
|---|---|---|
| `openwiki --init` exits with auth error | `ANTHROPIC_API_KEY` missing or wrong | Re-check `~/.openwiki/.env`; verify `curl` probe (§2) |
| "model not found" | MiniMax doesn't recognize `MiniMax-M2.7-highspeed` | Run a list-models probe; update `OPENWIKI_MODEL_ID` |
| Wiki generated but `AGENTS.md` not updated | OpenWiki failed before finalization step | Run `openwiki code --update --print` once more |
| Bot PR modifies `vibe-ops/` or `strategics/` | **Bug in INSTRUCTIONS.md or OpenWiki brief adherence** | Reject PR, fix `openwiki/INSTRUCTIONS.md`, rerun |
| LangSmith traces don't appear in dashboard | Wrong region or key | Check `LANGSMITH_OTEL_ENDPOINT`; for EU/APAC, override with `https://eu.api.smith.langchain.com/...` or `https://apac.api.smith.langchain.com/...` |
| Visualizer shows no nodes after Pages deploy | `docs/openwiki-visualizer/graph.json` was the pre-init empty scaffold | Re-run `openwiki visualize openwiki --export docs/openwiki-visualizer` locally, commit, push |
| `OPENWIKI_PROVIDER=openai-compatible` is needed | MiniMax's anthropic gateway rejects `x-api-key` (uses `X-Api-Key` instead) | Switch to `OPENAI_COMPATIBLE_BASE_URL` + `OPENAI_COMPATIBLE_API_KEY` env vars; update `.openwiki/README.md` + `.github/workflows/openwiki-update.yml` |

---

## What you do NOT need to do

- **Don't run `openwiki --init` again** after the first successful run — `--update` handles future drift.
- **Don't commit `~/.openwiki/.env`** — it's in `.gitignore`.
- **Don't edit `AGENTS.md` / `CLAUDE.md` between `OPENWIKI:START/END` markers** — OpenWiki owns that block. Everything outside the markers is yours.
- **Don't move files in `vibe-ops/`, `strategics/`, or cluster docs.** The wiki cites them; the wiki never relocates them.

---

## What I'm waiting on from you

After §1 (secrets set) + §2 (probe ok) + §3 (init succeeds):

Tell me "wiki is generated" and I'll:
1. Spot-check the first 5 generated pages against the actual `src/` code.
2. Wire `uv run pytest tests/unit/cli` into the CI bot as a precondition so
   the broken-CLI drift we identified gets caught as a stale Claim.
3. Open the first PR myself.
4. Set up the GitHub Pages deploy for the visualizer (one workflow file).

If §2 or §3 fails, tell me what the error says — I'll diagnose.
