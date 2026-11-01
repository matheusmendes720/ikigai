const fs = require('node:fs/promises');

const ROOT = 'C:/Users/mathe/code_space/life-oss/life';
const MAX_NODES = 64;

async function main() {
  const { chunks, groups } = JSON.parse(await fs.readFile(`${ROOT}/.omo-initdeep-chunks.json`, 'utf8'));
  const { kept } = JSON.parse(await fs.readFile(`${ROOT}/.omo-initdeep-kept.json`, 'utf8'));

  const scannerPrompt = (c) => `TASK: Extract knowledge-base facts for chunk ${c.id} of C:/Users/mathe/code_space/life-oss/life.
Steps, in order:
1. Read the scope file C:/Users/mathe/code_space/life-oss/life/.omo/init-deep/scope/${c.id}.json first. It lists the ONLY paths you may read: ${c.dirs.length ? 'dirs ' + c.dirs.join(', ') : '(no directories, files only)'} and ${c.files.length} files.
2. Inventory each directory in scope: file count, LOC, languages, entry files.
3. Public exports/symbols other code imports - use lsp_symbols and ast-grep import/call shapes, never file-name guesses.
4. Conventions that DEVIATE from stack defaults (configs, naming, layout).
5. Anti-patterns: DO NOT / NEVER / ALWAYS / DEPRECATED comments, forbidden patterns.
6. Hotspots: files >500 lines, high-reference symbols, complexity concentrations.
7. Build/test/dev commands touching these dirs.
DELIVERABLE: EXACTLY ONE file C:/Users/mathe/code_space/life-oss/life/.omo/init-deep/reports/${c.id}.md, <=5k tokens, sections \`# CHUNK ${c.id}\` / \`## INVENTORY\` / \`## EXPORTS\` / \`## CONVENTIONS\` / \`## ANTI-PATTERNS\` / \`## HOTSPOTS\` / \`## COMMANDS\`; an empty section says \`none\`.
SCOPE: read only the paths listed in the scope file ${c.id}.json; write only your report file .omo/init-deep/reports/${c.id}.md. Do not write AGENTS.md. If an AGENTS.md exists in scope, quote its still-true claims into the matching sections.
VERIFY: the report file exists and every section header is present.
STOP WHEN: the report is written and verified.`;

  const nodes = [];
  for (const c of chunks) {
    nodes.push({
      id: `scan-${c.id}`,
      category: 'quick',
      prompt: scannerPrompt(c),
      task_summary: `Scan chunk ${c.id} (${c.label}) into a bounded report`,
    });
  }

  const GROUP_RULES = {
    g1: `subtree src/ (src/contracts, src/mesh, src/data, src/services, src/transport, src/life_tatics, src/planner, and the reduced src/ikigai that keeps only the meta-planner contracts plus the drift net). The legacy langgraph harness under src/ikigai/src/agents, src/ikigai/src/chat and src/ikigai/src/mcp_server was RETIRED by ADR-037 (serverless pivot, 2026-11-01) and is no longer published - do not write AGENTS.md for it, and say so in your digest. The DATA LAYER (src/data -> src/services -> src/transport, with src/contracts/dom.py and src/contracts/store.py as the canonical contracts) is the ACTIVE line: give it the deepest treatment. DO NOT write inside src/ikigai/tests (pytest fixtures) - report them only.`,
    g2: `subtree vibe-ops/ (src/cybernetics, src/vibe_cli.py, vibeops-tui Rust crate, base/ docs). Rust crate src/ lives under vibe-ops/vibeops-tui/src/.`,
    g3: `subtree tests/ (root integration tests + conftest.py). tests/conftest.py is the dual-tree identity resolver - document it.`,
    g4: `subtree interfaces/ and sys_ikigai/ (the Typer CLI surface under interfaces/cli - the Textual TUI under interfaces/tui was RETIRED by ADR-037 - plus entities/gateway/state_machines/vault/security/adapters under sys_ikigai/).`,
    g5: `subtree tools/ scripts/ taskwarrior/ life/ examples/ bin/ .github/ (tooling, build scripts, taskwarrior adapter, meta-package, CI workflows). The PaperclipAI plugin tree under plugins/ and the .hermes/.atlas/.claude-flow probe trees are no longer published - skip them if you only find them on disk.`,
    g6: `subtree docs/ (design-system, superpowers specs and plans, dated engineering docs). The ADRs and the data-layer specs live in code-docs/ and specs/, not here.`,
    g7: `subtree code-docs/ (adr, prd, brd, ard, diagnostic) and specs/ (feature specs, data-layer/TECH.md). ADR-037-data-layer-canonical-turn.md (2026-11-01) decides the current mode of the repo: data layer first, TUI on standby. The root file must be able to find it, so put ADR-037 and specs/data-layer/TECH.md in your digest as cross-subtree facts.`,
    g8: `subtree .claude/ (loop/ with constitution.md, roadmap.md, tasks.md; commands/, skills/, agents/, helpers/) and .agents/skills/ (project skills). This is the harness meta tooling a cloud agent must find: the hill-climb loop, the roadmap and the conventions. Surface the exact paths (.claude/loop/constitution.md, .claude/loop/roadmap.md, .claude/loop/tasks.md, .claude/commands/, .agents/skills/) in your digest as cross-subtree facts.`,
    g9: `subtree reports/ notes/ openwiki/ diagrams/ strategics/ (auxiliary knowledge: generated reports, notes, wiki, diagrams, and the PT-BR strategic prose which is read-only).`,
    g10: `subtree vault/ (the Obsidian-style markdown source of truth: ikigai/ with closing-2026, cycles, decisions, meta, reflections, runtime, templates; plus drafts, evidence, plans, projetos). The vault is APPEND-ONLY prose, not code: DO NOT create or modify any AGENTS.md inside vault/ and DO NOT touch any file there. Your only deliverable is the digest .omo/init-deep/digests/vault.md describing what the vault contains and which decision notes a cloud agent must read (ADR-037 and the serverless pivot note).`,
  };

  const writerPrompt = (g) => `TASK: Own subtree ${GROUP_RULES[g.gid]} Produce the AGENTS.md files for that subtree in the C:/Users/mathe/code_space/life-oss/life knowledge base.
Steps, in order:
1. Read your chunk reports: ${g.chunkIds.map((x) => `.omo/init-deep/reports/${x}.md`).join(', ')}. Reports are claims, not truth - spot-check real code wherever they conflict or look thin.
2. Score each directory with the init-deep Scoring Matrix; pick locations with the Decision Rules (both are in the init-deep skill content loaded with this task). Depth limit: do not create AGENTS.md deeper than 3 directory levels below the repo root.
3. Write each AGENTS.md per the templates and the File Writing Rule. 30-80 lines, never repeating parent content.
4. Write .omo/init-deep/digests/${g.slug}.md, <=2k tokens: every location written (score, one-line role) plus cross-subtree facts the root file must know.
DELIVERABLE: the AGENTS.md files you selected plus .omo/init-deep/digests/${g.slug}.md.
SCOPE: write only inside ${g.scopePaths} plus your digest file. Root AGENTS.md is OUT of scope.
VERIFY: every location chosen in step 2 exists on disk within line limits; digest exists.
STOP WHEN: files and digest are written and verified.`;

  const GROUP_META = {
    g1: { slug: 'src', scopePaths: 'src/' },
    g2: { slug: 'vibe-ops', scopePaths: 'vibe-ops/' },
    g3: { slug: 'tests', scopePaths: 'tests/' },
    g4: { slug: 'interfaces-sys-ikigai', scopePaths: 'interfaces/ and sys_ikigai/' },
    g5: { slug: 'tooling-meta', scopePaths: 'tools/, scripts/, taskwarrior/, life/, plugins/, examples/, bin/, .github/' },
    g6: { slug: 'docs', scopePaths: 'docs/' },
    g7: { slug: 'adr-specs', scopePaths: 'code-docs/ and specs/' },
    g8: { slug: 'harness-meta', scopePaths: '.claude/ and .agents/' },
    g9: { slug: 'docs-aux', scopePaths: 'reports/, notes/, openwiki/, diagrams/, strategics/' },
    g10: { slug: 'vault', scopePaths: 'vault/' },
  };

  const vaultDigestPrompt = (chunkIds) => `TASK: Describe the vault subtree for the init-deep knowledge base.
Steps, in order:
1. Read your chunk reports: ${chunkIds.map((x) => `.omo/init-deep/reports/${x}.md`).join(', ')}. Reports are claims, not truth - spot-check the real files when they look thin.
2. Inventory vault/: top-level directories, the ikigai/ sub-structure, the template files and the daily-report folders. Note the append-only rule and the writer rule (only the Deep Agent writes vault content).
3. Name the decision notes a cloud agent MUST read: code-docs/adr/ADR-037-data-layer-canonical-turn.md, the 2026-11-01 serverless decision note, and the sono-log template.
DELIVERABLE: exactly one file .omo/init-deep/digests/vault.md, <=2k tokens, with the sections \`# VAULT\`, \`## STRUCTURE\`, \`## KEY DECISIONS\`, \`## RULES\`.
SCOPE: write ONLY .omo/init-deep/digests/vault.md. Never write inside vault/.
VERIFY: the digest exists and every section header is present.
STOP WHEN: the digest is written and verified.`;

  const byGroup = new Map();
  for (const c of chunks) {
    if (!byGroup.has(c.group)) byGroup.set(c.group, []);
    byGroup.get(c.group).push(c.id);
  }

  const writerIds = [];
  for (const g of groups) {
    const ids = byGroup.get(g.gid) || [];
    if (!ids.length) continue;
    const meta = GROUP_META[g.gid];
    const writerId = `write-${g.gid}`;
    writerIds.push(writerId);
    nodes.push({
      id: writerId,
      category: 'unspecified-high',
      load_skills: ['init-deep'],
      dependsOn: ids.map((x) => `scan-${x}`),
      prompt: g.gid === 'g10' ? vaultDigestPrompt(ids) : writerPrompt({ ...g, chunkIds: ids, ...meta }),
      task_summary: `Write AGENTS.md files for ${g.label}`,
    });
  }

  const rootWriterId = 'write-root';
  nodes.push({
    id: rootWriterId,
    category: 'unspecified-high',
    load_skills: ['init-deep'],
    dependsOn: writerIds,
    prompt: `TASK: Write the ROOT AGENTS.md of C:/Users/mathe/code_space/life-oss/life from the subtree digests only.
Steps, in order:
1. Read ONLY these files: the digests C:/Users/mathe/code_space/life-oss/life/.omo/init-deep/digests/src.md, vibe-ops.md, tests.md, interfaces-sys-ikigai.md, tooling-meta.md, docs.md, adr-specs.md, harness-meta.md, docs-aux.md, vault.md and the existing root AGENTS.md at C:/Users/mathe/code_space/life-oss/life/AGENTS.md. Never read the chunk reports.
2. The existing root AGENTS.md already exists and is good - rewrite it per the init-deep root template below, keeping every still-true fact it already carries (invariants, import-path rules, Windows quirks, drift-net table, refactor protocol) and dropping anything stale. The root AGENTS.md currently violates the 50-150 line gate: bring it inside 50-150 lines.
3. Use the root template from the init-deep skill content loaded with this task: \`# PROJECT KNOWLEDGE BASE\` with Generated / Commit / Branch lines, then \`## OVERVIEW\`, \`## STRUCTURE\`, \`## WHERE TO LOOK\`, \`## CODE MAP\`, \`## CONVENTIONS\`, \`## ANTI-PATTERNS (THIS PROJECT)\`, \`## UNIQUE STYLES\`, \`## COMMANDS\`, \`## NOTES\`. Keep only deviations from standard practice; no generic advice.
4. MANDATORY current mode. The published repository is now CANONICAL SERVERLESS SCOPE: the legacy langgraph/langchain harness, the local chat REPL, the stdio MCP servers, the Textual TUI and the PaperclipAI plugin were REMOVED from the remote (ADR-037, 2026-11-01) because they are PC-only. A cloud agent cloning this repo gets the canonical multi-device code, the contracts, the mesh, the data layer and the docs - nothing else. The OVERVIEW must state this in one sentence.
5. MANDATORY current mode. The OVERVIEW must state that the canonical turn of this repo is the DATA LAYER first (ADR-037, 2026-11-01): the operational/TUI focus is on standby and the data layer (DOM -> Postgres serverless store -> services/MCP) is the active line. The WHERE TO LOOK table must have rows for exactly these verified paths: code-docs/adr/ADR-037-data-layer-canonical-turn.md, specs/data-layer/TECH.md, .claude/loop/roadmap.md, .claude/loop/tasks.md, .claude/loop/constitution.md, .claude/commands/, .agents/skills/. Add these rows even if a digest does not mention them - the paths are verified to exist in this repo.
DELIVERABLE: exactly one file C:/Users/mathe/code_space/life-oss/life/AGENTS.md, 50-150 lines.
SCOPE: read only the nine digests plus the existing root AGENTS.md; write only the root AGENTS.md.
VERIFY: the file exists, is 50-150 lines, contains every section header listed above.
STOP WHEN: the root AGENTS.md is written and verified.`,
    task_summary: 'Write root AGENTS.md from digests only',
  });

  const verifyId = 'verify';
  nodes.push({
    id: verifyId,
    category: 'quick',
    dependsOn: [rootWriterId],
    prompt: `TASK: Verify every AGENTS.md file produced by the init-deep run in C:/Users/mathe/code_space/life-oss/life.
Steps, in order:
1. Build the file list: the root AGENTS.md plus every path declared in the digests C:/Users/mathe/code_space/life-oss/life/.omo/init-deep/digests/*.md. Read those digest files to get the paths. Do NOT include pre-existing vendored files such as strategics/planning-with-files/AGENTS.md, vault/ikigai/meta/agents.md or .claude/commands/monitoring/agents.md - they are not this run's output.
2. For the root AGENTS.md: check it exists, is 50-150 lines, and has every section header OVERVIEW, STRUCTURE, WHERE TO LOOK, CODE MAP, CONVENTIONS, ANTI-PATTERNS, UNIQUE STYLES, COMMANDS, NOTES.
3. For each subdirectory AGENTS.md: check it exists, is 30-80 lines, and has the sections OVERVIEW, WHERE TO LOOK, CONVENTIONS, ANTI-PATTERNS (STRUCTURE only if the directory has more than 5 subdirectories).
4. Check no child file repeats a parent section block verbatim.
DELIVERABLE: one file C:/Users/mathe/code_space/life-oss/life/.omo/init-deep/verify/verdict.txt with exactly one line per file: \`PASS <path>\` or \`FAIL <path>: <reason>\`. Also print those same lines as your final message.
SCOPE: read only the digests and the AGENTS.md files; write only the verdict file.
VERIFY: the verdict file exists and has one line per checked file.
STOP WHEN: the verdict file is written.`,
    task_summary: 'Verify generated AGENTS.md files and write verdict',
  });

  const def = { key: 'init-deep-life-2026-11-01-serverless', name: 'init-deep knowledge base refresh for life-oss/life (pivot-aware)', nodes };
  if (nodes.length > MAX_NODES) {
    throw new Error(`node count ${nodes.length} exceeds cap ${MAX_NODES}`);
  }
  await fs.writeFile(`${ROOT}/.omo/init-deep/definition.json`, JSON.stringify(def, null, 1));
  console.log(JSON.stringify({
    nodes: nodes.length,
    scanners: chunks.length,
    writers: writerIds.length,
    rootWriter: rootWriterId,
    verify: verifyId,
    keptFiles: kept.length,
  }));
}

main();
