# Example: M0 Bootstrap — Initialize Loop Infrastructure

Demonstrates how to bootstrap a minimal loop-engineering infrastructure from scratch. Shows the 9 file artifacts that the loop depends on.

## The 9 file artifacts

A canonical "M0 Bootstrap" milestone creates:

1. `.claude/loop/roadmap.md` — milestone list + acceptance criteria
2. `.claude/loop/tasks.md` — derived atomic tasks
3. `.claude/loop/progress.md` — append-only tick audit log
4. `.claude/loop/constitution.md` — invariant principles (correctness > speed, etc.)
5. `.claude/agents/loop/orchestrator.md` — picks next task
6. `.claude/agents/loop/worker.md` — implements 1 task
7. `.claude/agents/loop/verifier.md` — scores the worker's output
8. `.claude/loop/loop-tick.sh` — orchestrator entrypoint
9. `.claude/skills/loop-engineering/SKILL.md` — the meta-skill description

After these 9 files exist, you can run `bash .claude/loop/loop-tick.sh` and the loop is operational.

## How to run this example

```bash
cd examples/m0-bootstrap

# Option A: Read the artifacts only (no execution)
ls -la .claude/loop/ .claude/agents/loop/ .claude/skills/loop-engineering/
cat .claude/loop/roadmap.md
cat .claude/loop/constitution.md

# Option B: Run the loop tick (requires real loop infra)
bash .claude/loop/loop-tick.sh
# Expect: orchestrator reads state, picks T-0.1 "Verify infrastructure
# files exist" → spawns worker → spawns verifier → appends to progress.md
```

## Key takeaway

The loop is just state + agents + scripts. No external daemon required for a manual cycle. The claude-flow daemon is OPTIONAL infrastructure for cron-driven ticks.
