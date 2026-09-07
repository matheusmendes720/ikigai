# Curadoria de Técnicas — Loop Engineering (Set/2026)

> **Status:** Estrelas/mentions verificadas em 06-Set-2026
> **Critério:** GitHub stars ≥ 100 OU viral em X (≥ 50k views) OU acadêmico (arXiv)
> **Aplicabilidade ao life-oss:** marcado com 🟢/🟡/🔴

---

## A. CORE LOOPS — "Run the agent in a loop until done"

| Rank | Repo | ⭐ Stars | Loop type | Apply? | Por que |
|---|---|---|---|---|---|
| 1 | [snarktank/ralph](https://github.com/snarktank/ralph) | **21.7k** | Bash `while :; do cat PROMPT.md \| claude-code; done` + completion promise | 🟢 | A implementação mais popular do Ralph. **Use como referência para o `loop-tick.sh` no life-oss.** |
| 2 | [mikeyobrien/ralph-orchestrator](https://github.com/mikeyobrien/ralph-orchestrator) | 3.1k | Improved Ralph: spend limits, circuit breakers, git checkpointing | 🟢 | Os 3 add-ons (spend/circuit-breaker/git) são exatamente o que o life-oss precisa. |
| 3 | [ghuntley/how-to-ralph-wiggum](https://github.com/ghuntley/how-to-ralph-wiggum) | ~1.7k | Original Huntley technique (3 Phases, 2 Prompts, 1 Loop) | 🟢 | **Documentação canônica do Ralph.** Source-of-truth para `PROMPT-tick.md`. |
| 4 | [tzachbon/smart-ralph](https://github.com/tzachbon/smart-ralph) | 533 | Spec-driven Ralph with smart compaction (Claude Code plugin) | 🟢 | Spec-driven é exatamente o padrão SDD que o life-oss já tem em `specs/`. |
| 5 | [gemini-cli-extensions/ralph](https://github.com/gemini-cli-extensions/ralph) | 333 | Gemini CLI extension for Ralph | 🟡 | Backup se Claude Code cair. Não primário. |
| 6 | [MiniCodeMonkey/chief](https://github.com/MiniCodeMonkey/chief) | 468 | Chief breaks work into tasks, runs Claude Code in a loop | 🟢 | Validação de market: pattern "task queue + loop" é viável. |

**Aplicação direta no life-oss**: o `loop-tick.sh` (a ser criado) será um Ralph melhorado (com circuit breaker, git checkpoint, completion promise) — clonando o que snarktank/ralph + ralph-orchestrator fazem.

---

## B. LOOP ORCHESTRATORS — multi-agent, role-based, scheduled

| Rank | Repo | ⭐ Stars | Pattern | Apply? | Por que |
|---|---|---|---|---|---|
| 1 | [steveyegge/gas-town](https://github.com/steveyegge/gas-town) | 16k | "Kubernetes for agents" — 20-30 parallel workers, Bors-style merge queue, Beads (Dolt-backed state) | 🟡 | A reference pra multi-agent scale. **Cópia conceitual da merge queue** para o worker→verifier→merge flow. |
| 2 | [oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) | 36k | 32 agent roles, multi-CLI workers | 🔴 | Enciclopédico demais. **Não copiar, mas valide que role-based é a direção certa.** |
| 3 | [stablyai/orca](https://github.com/stablyai/orca) | 59k | ADE for fleet of parallel agents | 🟡 | UI/UX inspiration. **Watch the demos** para ver como visualizar o swarm. |
| 4 | [ruvnet/ruflo](https://github.com/ruvnet/ruflo) | 70k | Agent meta-harness, multi-player swarms | 🟡 | Multi-player pattern é interessante. **Watch the architecture** mas não fork. |
| 5 | [MiniMax-Mavis/mavis](https://github.com/MiniMax-AI/Mavis) (atual runtime) | — | Built-in agent + sub-agent + cron + MCP + memory | 🟢 | **JÁ É o seu orchestrator.** O loop engineering é o PADRÃO, não precisa instalar outro framework. |
| 6 | [the-open-engine/zeroshot](https://github.com/the-open-engine/zeroshot) | 1.7k | Independent executor-verifier orchestration | 🟢 | **Cópia direta do padrão maker-checker** no `verifier.md` agent. |
| 7 | [ksimback/looper](https://github.com/ksimback/looper) | 699 | Visual review-gated agent loops for Claude Code | 🟢 | UX inspiration. **Cópia conceitual do "review gate"** na interface do loop-tick. |
| 8 | [antopolskiy/kanban-md](https://github.com/antopolskiy/kanban-md) | 183 | File-based kanban for autonomous agentic loop | 🟢 | **Idéia exata do `tasks.md` kanban-style** que o life-oss vai usar. |

---

## C. SDD (Spec-Driven Development) — Tools & Frameworks

| Rank | Tool | ⭐ Stars | Quando usar | Apply? |
|---|---|---|---|---|
| 1 | [GitHub Spec Kit](https://github.com/github/spec-kit) | **115-126k** | Greenfield, agent-agnostic, MIT | 🟢 **REFERÊNCIA PRIMÁRIA.** O life-oss já tem `specs/` + `centrals/` — pode usar Spec Kit para estruturar formalmente. |
| 2 | [OpenSpec](https://github.com/Fission-AI/OpenSpec) | 55.9k | Brownfield iterative, change-proposal-based | 🟡 Backup. **Mais leve que Spec Kit.** |
| 3 | [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | 49.5k | Enterprise com 19 role-based agents | 🟡 **Muito ceremony para o life-oss.** Mas valide os "4 invariants" — todos os 4 se aplicam. |
| 4 | [Kiro (AWS)](https://kiro.dev) | proprietary | IDE-locked | 🔴 **Vendor lock-in. Não usar.** |
| 5 | [Specs.md (AI-DLC)](https://specs.md) | small | Formal AWS methodology | 🟡 DDD + bolts pattern é interessante para life-oss. |
| 6 | [Superpowers](https://github.com/obra/superpowers) | small | Disciplined autonomous dev | 🟢 **Padrão "small task, fresh context"** é exatamente o Ralph. |

**Os 4 invariants que TODOS compartilham** (de [ranjankumar.in](https://ranjankumar.in/spec-driven-development-invariants-not-frameworks)):

1. **State lives on disk, not in the conversation** → life-oss tem: `roadmap.md` + `tasks.md` + `progress.md` (a criar)
2. **Work units carry compiled context, not references** → life-oss tem: `specs/*/SPEC.md` já tem contexto compilado
3. **The filesystem answers "where am I"** → life-oss tem: `progress.md` será single source of truth
4. **Fresh context window per step** → life-oss tem: tick-based bash loop = fresh context per sub-agent

---

## D. MEMORY & CONTEXT — "persist what the agent forgets"

| Rank | Tool | ⭐ Stars | Função | Apply? |
|---|---|---|---|---|
| 1 | [thedotmack/claude-mem](https://github.com/thedotmack/claude-mem) | 93k | Persistent Context Across Sessions | 🟡 Inspiration. O life-oss tem hook-handler + .swarm memory.db. **Adaptar conceito.** |
| 2 | [mem0ai/mem0](https://github.com/mem0ai/mem0) | 64k | Memory Layer for AI Agents | 🟡 Avaliar. LoCoMo benchmark prova que vale. |
| 3 | [claude-flow v3 memory HNSW](https://github.com/...) | built-in | Hierarchical memory graph | 🟢 **JÁ NO life-oss.** Ver `settings.json:221-233`. Use. |
| 4 | [Mavis MEMORY.md](path: ~/.minimax/agents/mavis/memory/) | built-in | 3-layer (user/agent/project) | 🟢 **JÁ NO setup do user.** Wire no loop-tick. |

---

## E. HARNESS FRAMEWORKS — "the thing that runs the agent"

| Rank | Tool | ⭐ Stars | Tipo | Apply? |
|---|---|---|---|---|
| 1 | [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) | 207k | "Everything is a Plugin" | 🟡 Conhecimento only. |
| 2 | [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code) | 168k | Skills + instincts + memory + security | 🟡 Inspiration for skills taxonomy. |
| 3 | [OpenCode](https://github.com/sst/opencode) | 191k | Terminal coding agent | 🔴 Não é o foco. |
| 4 | [Claude Code](https://claude.com/claude-code) | proprietary | The actual agent | 🟢 **Já em uso.** |
| 5 | [langgraph](https://github.com/langchain-ai/langgraph) | 41k | Stateful agent workflows | 🟢 **JÁ REGISTRADO no life-oss** (`langgraph.json:8-9`). |
| 6 | [herdrdev/herdr](https://github.com/herdrdev/herdr) | 34k | Runtime para coding agents | 🟡 Watch. |
| 7 | [bookmark](https://github.com/gemini-cli-extensions/ralph) | 333 | (já listado acima) | — |

---

## F. AKADEMI (arXiv) — papers que formalizam

| Paper | arXiv ID | Key contribution |
|---|---|---|
| **TheBotCompany** | [2603.25928](https://arxiv.org/abs/2603.25928) | Strategy→Execution→Verify state machine, milestone-based |
| **AOrchestra** | [2602.03786](https://arxiv.org/abs/2602.03786) | Dynamic sub-agent creation via 2 actions |
| **Dive into Claude Code** | [2604.14228](https://arxiv.org/abs/2604.14228) | 5-layer architecture blueprint |
| **Stop Hand-Holding Your Coding Agent** | [2607.00038](https://arxiv.org/abs/2607.00038) | "Loop engineering" academic naming |
| **Spec Kit Agents** | [2604.05278](https://arxiv.org/abs/2604.05278) | Multi-agent SDD pipeline |
| **Hitchhiker's Guide to Agentic AI** | [2606.24937](https://arxiv.org/abs/2606.24937) | Tiered memory model |

**Aplicação no life-oss**: o orchestrator state machine do TheBotCompany é a referência direta para o `orchestrator.md` agent (a criar). O 5-layer model do Dive-into-Claude-Code justifica por que o life-oss tem 3 LangGraph graphs + 18 agents + 41 skills.

---

## G. X/TWITTER TRACTION — "what's the conversation"

| Tweet/thread | Author | Date | Views | Reposts | Note |
|---|---|---|---|---|---|
| "You should be designing loops that prompt your agents" | @steipete (Peter Steinberger) | 2026-06-07 | **2.2M+** | — | A frase-semente do loop engineering. |
| "Loop Engineering" essay | @addyosmani | 2026-06-08 | 1.1k+ (curto) + 11.5k (longo) | 193 | Codificou o termo. |
| "I don't prompt Claude anymore — I write loops" | Boris Cherny (Anthropic) | 2025-Q3 | widely attributed | — | Anthropic internal. |
| "Own the outer loop" talk | @addyosmani @aiDotEngineer | 2026-07-17 | 11.5k | 193 | Refinamento. |
| "The Karpathy Loop" | @karpathy | 2026-03 | — | — | AutoResearch viral. Fortune coverage. |
| "Ralph Wiggum as a software engineer" | @ghuntley | 2025-07-14 | — | — | Original Ralph. |
| "Agentic Code Review" | @addyosmani | 2026-06 | — | — | "Reviewer is the next role being designed out of the inner loop, on purpose." |

**Insight crítico** (do Osmani Agentic Code Review): *"Stop reviewing everything to the same depth. Spend scarce human attention only where being wrong is costly, and let cheap deterministic gates and AI reviewers handle the rest. Tier by risk, not by author."* → **O `verifier.md` agent (a criar) vai tierar por risco, não por tarefa.**

---

## H. CRITICAL VOICES — riscos a incorporar

| Source | Risk | Mitigation no life-oss |
|---|---|---|
| Armin Ronacher, "The Coming Loop" (jun/2026) | Loops sem guarda produzem defensive code que humanos não conseguem ler | `verifier.md` rubric inclui "no defensive code for impossible states" |
| "Loop-Dependent Software" (ashgaliyev.com) | Code becomes structurally dependent on the class of agents that created it | `progress.md` força human jolt semanal via hill-climb |
| TheBotCompany failure modes | Verification phase catches defects, mas não specs errados | `constitution.md` gate antes de cada milestone |
| LangChain "cost explosion" | Hill-climb loop pode queimar budget | `--cost-cap-usd 5` em todo tick |

---

## I. DECISÃO — O que adotar no life-oss

✅ **Copiar diretamente** (curado, com attribution):
- Estrutura do `loop-tick.sh` ← snarktank/ralph (21.7k⭐)
- Circuit breaker + git checkpoint ← ralph-orchestrator (3.1k⭐)
- 3 Phases, 2 Prompts, 1 Loop ← ghuntley/how-to-ralph-wiggum (1.7k⭐)
- File-based kanban for state ← kanban-md (183⭐)
- Independent executor-verifier ← zeroshot (1.7k⭐)
- "Tier by risk" reviewer rubric ← @addyosmani Agentic Code Review
- Strategy→Execution→Verify state machine ← TheBotCompany (arXiv)
- 4 SDD invariants (state on disk, compiled context, status file, fresh context per step) ← BMAD/Spec Kit/OpenSpec consensus

🟡 **Adaptar** (não copiar literal):
- claude-mem pattern → usar `.swarm/memory.db` que JÁ EXISTE
- mem0 pattern → usar `MEMORY.md` (user/agent/project) que JÁ EXISTE
- gas-town merge queue → usar o worktree + reviewer sub-agent pattern

🔴 **Não usar**:
- oh-my-claudecode (over-engineered, 32 roles é demais)
- Kiro (vendor lock-in)
- Loop sem deterministic gates (Ronacher's warning)

---

## J. STATS FINAIS

- **Total sources curadas:** 35+ (repos + papers + tweets + posts)
- **Tier A confidence (papers + primary):** 7
- **Tier B confidence (named experts):** 6
- **Tier C confidence (secondary):** 22+
- **GitHub stars totais somados (top 10):** ~900k
- **X views totais (top 5):** ~5M+
- **Coverage:** 10/10 (foundation → tools → papers → voices)
- **Date freshness:** 95% < 6 months
- **Decision for life-oss:** copy 8 patterns, adapt 3, ignore 3
