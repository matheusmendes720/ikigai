# Examples — Loop Engineering in Practice

Three self-contained demonstrations of how the IKIGAI loop-engineering infrastructure works in practice. Each example directory is standalone (doesn't require the full repo state to make sense).

## Available examples

| Example | What it shows |
|---|---|
| [M0 Bootstrap](m0-bootstrap/) | The 9 file artifacts needed to init a minimal loop |
| [M1 Cron Tick](m1-cron-tick/) | Registering loop-tick.sh as a daemon schedule |
| [M5 MCP Integration](m5-mcp-integration/) | TDD pattern for adding MCP tools + drift net |

## How to use

```bash
cd examples/<X>
cat README.md
```

Each example is standalone — copy it into your own project as a starting template.

## Related docs

- `.claude/loop/CURATED-TECHNIQUES.md` — full curation of loop-engineering references
- `.claude/loop/IMPLEMENTATION-GUIDE.md` — deep dive on implementation details
- `.claude/skills/loop-engineering/SKILL.md` — the meta-skill
