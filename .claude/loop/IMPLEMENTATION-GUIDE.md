# Loop Engineering — Deep Implementation Guide (life-oss)

> **Audience:** Você (Matheus) ou qualquer agent que for operar o loop depois de mim.
> **Objetivo:** Explicar, abstração por abstração, COMO e POR QUE cada peça do loop foi desenhada — e dar instruções executáveis.

---

## 0. Mapa Mental (comece aqui)

Imagine o loop como **4 camadas concêntricas**, cada uma envolvendo a anterior. Você não precisa entender as 4 de uma vez. Comece da mais interna e suba:

```
┌────────────────────────────────────────────────────────────────────┐
│ CAMADA 4 — HILL-CLIMB (semanal, lê traces, melhora a si mesmo)    │
│   → arquivo: .claude/loop/hill-climb.sh                            │
│   → quando: domingo 02:00, daemon schedule                          │
│   → o que faz: lê progress.md, identifica padrões, abre PR         │
│                                                                      │
│   ┌──────────────────────────────────────────────────────────────┐ │
│   │ CAMADA 3 — EVENT-DRIVEN (cron dispara o tick)                │ │
│   │   → arquivo: .claude/loop/loop-tick.sh + loop-tick.bat       │ │
│   │   → quando: a cada 60min, claude-flow daemon schedule        │ │
│   │   → o que faz: invoca o orchestrator com prompt+state        │ │
│   │                                                              │ │
│   │   ┌────────────────────────────────────────────────────────┐ │ │
│   │   │ CAMADA 2 — VERIFICATION (sub-agent julga)               │ │ │
│   │   │   → arquivo: .claude/agents/loop/verifier.md            │ │ │
│   │   │   → modelo: haiku (≠ worker)                           │ │ │
│   │   │   → quando: depois de cada worker terminar             │ │ │
│   │   │   → o que faz: roda pytest+ruff+mypy, score 1-5 × 5     │ │ │
│   │   │                                                        │ │ │
│   │   │   ┌──────────────────────────────────────────────────┐ │ │ │
│   │   │   │ CAMADA 1 — AGENT (ReAct, faz o trabalho)         │ │ │ │
│   │   │   │   → arquivo: .claude/agents/loop/worker.md       │ │ │ │
│   │   │   │   → modelo: sonnet (≠ verifier)                  │ │ │ │
│   │   │   │   → quando: dentro de worktree isolado           │ │ │ │
│   │   │   │   → o que faz: implementa + testa + commit       │ │ │ │
│   │   │   └──────────────────────────────────────────────────┘ │ │ │
│   │   └────────────────────────────────────────────────────────┘ │ │
│   └──────────────────────────────────────────────────────────────┘ │
│                                                                      │
└────────────────────────────────────────────────────────────────────┘
         ▲
         │  quem orquestra tudo: ORCHESTRATOR (opus)
         │  arquivo: .claude/agents/loop/orchestrator.md
         │  estado lido: constitution, roadmap, tasks, progress, AGENTS.md
```

**A primeira leitura é essa. Acabou. Releia o diagrama se travar.**

---

## 1. As 5 Abstrações Fundamentais

Cada arquivo do loop implementa UMA abstração. Memorize as 5:

### Abstração 1: STATE = arquivos em disco

| Arquivo | O que é | Quem escreve | Quem lê |
|---|---|---|---|
| `roadmap.md` | Sequência de milestones (M0, M1, ...) | Humano + Orchestrator | Orchestrator |
| `tasks.md` | Tarefas atômicas por milestone (T-0.1, T-0.2, ...) | Orchestrator (auto-gen) | Orchestrator + Worker |
| `progress.md` | Log append-only, 1 linha por tick | Todos (append only) | Orchestrator + Hill-climb |
| `constitution.md` | Princípios + anti-patterns | Humano (raro) | Verifier (gates every milestone) |
| `specs/M{n}-*/SPEC.md` | Acceptance criteria por milestone | Humano (1× por milestone) | Worker + Verifier |

**Regra de ouro:** Se a informação não está em um desses arquivos, ela não existe. **O agent não "lembra"** entre sessões. Cada tick começa lendo o estado do zero.

### Abstração 2: ROLE = agent file

| Role | Arquivo | Modelo | Personalidade |
|---|---|---|---|
| Orchestrator | `.claude/agents/loop/orchestrator.md` | opus (mais forte) | Estrategista. Lê muito, escreve pouco. Delega. |
| Worker | `.claude/agents/loop/worker.md` | sonnet (médio) | Executor. Foca, faz, sai. Não planeja além do escopo. |
| Verifier | `.claude/agents/loop/verifier.md` | haiku (mais barato) | Juiz. Não propõe fix, só identifica problema. |

**Por que 3 modelos diferentes?** Princípio de Addy Osmani: *"o model é um corretor generoso da própria lição de casa"*. Se worker=sonnet e verifier=sonnet, o verifier tenderia a aprovar o que ele mesmo produziria. Haiku é diferente o suficiente pra ser honesto.

### Abstração 3: VERDICT = JSON estruturado

Toda execução termina com um JSON parseável. Schema (do verifier):

```json
{
  "verdict": "PASS | FAIL | NEEDS_FIX",
  "scores": {"correctness": N, "minimality": N, "coherence": N, "safety": N, "reversibility": N},
  "deterministic_gates": {"tests": "pass|fail", "lint": "pass|fail", "types": "pass|fail"},
  "notes": "string ≤500 chars",
  "blockers": ["string", ...]
}
```

**Regra:** `PASS` exige (a) todos os 3 gates pass + (b) score médio ≥ 4.0 + (c) nenhum score < 3. Se qualquer um falhar → `FAIL` ou `NEEDS_FIX`.

### Abstração 4: COST = budget por tick

Cada tick tem 3 limites hard (configuráveis):

| Limite | Default | Configurável | Onde enforced |
|---|---|---|---|
| Cost | $5 USD | `--cost-cap N` | `loop-tick.sh:38` (bash) + orchestrator prompt |
| Wall time | 30min | `--max-runtime N` | `loop-tick.sh:115` (timeout) + `progress.md` se overruns |
| Sub-agents | 4 worker + 4 verifier | hardcoded | orchestrator prompt |

**Regra de gasto diário:** `loop-tick.sh:50-55` recusa rodar se o dia já gastou > 80% do cap diário (default 10× o cap por tick = $50/dia).

### Abstração 5: LOOP = bash + claude-code subprocess

O tick é literalmente:

```bash
# loop-tick.sh
claude-code \
  --agent "$PROJECT_ROOT/.claude/agents/loop/orchestrator.md" \
  --prompt "..." \
  --model claude-opus-4-8 \
  --max-cost "$COST_CAP_USD" \
  | tee "$LOG_FILE"
```

**O claude-code é um subprocess que termina.** Quando termina, o tick acabou. O próximo tick é outro subprocess. Fresh context window. Fresh memory. Mas a mesma leitura de disco (state).

---

## 2. Ciclo de Vida Completo de UM Tick

Aqui está, com timestamps aproximados, o que acontece em UM tick:

```
T+0:00  cron fires  →  loop-tick.sh invocado
T+0:01  bash  →  pre-check (daily spend, existing logs dir)
T+0:01  bash  →  timeout 30min começa
T+0:02  claude-code  →  carrega orchestrator.md
T+0:02  orchestrator  →  LÊ constitution.md
T+0:02  orchestrator  →  LÊ roadmap.md
T+0:02  orchestrator  →  LÊ tasks.md
T+0:02  orchestrator  →  LÊ progress.md (10 últimas linhas)
T+0:02  orchestrator  →  LÊ AGENTS.md
T+0:03  orchestrator  →  DECIDE: tarefa pendente? (T-0.1)
T+0:03  orchestrator  →  invoca scripts/worktree-helper.sh create m-0.1
T+0:04  worktree criado em .worktrees/m-0.1/ (branch loop/m-0.1)
T+0:04  orchestrator  →  spawna worker (sonnet) com prompt:
                       "Implement T-0.1. See SPEC.md, AGENTS.md, worktree=.worktrees/m-0.1/"
T+0:04  worker  →  LÊ SPEC.md
T+0:04  worker  →  LÊ constitution.md (anti-patterns!)
T+0:05  worker  →  LÊ AGENTS.md
T+0:05  worker  →  EXPLORA repo (ls, grep)
T+0:06  worker  →  IMPLEMENTA o que precisa
T+0:08  worker  →  uv run pytest -x
T+0:10  worker  →  uv run ruff check src/
T+0:11  worker  →  uv run mypy src/
T+0:11  worker  →  git add . && git commit -m "..."
T+0:12  worker  →  retorna JSON {status: success, commit_sha: abc1234, ...}
T+0:12  orchestrator  →  spawna verifier (haiku) com prompt:
                       "Review commit abc1234. Run gates. Score 1-5 × 5."
T+0:12  verifier  →  cd .worktrees/m-0.1
T+0:13  verifier  →  uv run pytest -x  (GATE 1)
T+0:14  verifier  →  uv run ruff check src/  (GATE 2)
T+0:15  verifier  →  uv run mypy src/  (GATE 3)
T+0:15  verifier  →  ANALISA diff (git diff main..HEAD)
T+0:16  verifier  →  ANALISA constitution (anti-patterns presentes?)
T+0:16  verifier  →  SCORE: correctness=5, minimality=4, coherence=5, safety=5, reversibility=5
T+0:17  verifier  →  retorna JSON {verdict: PASS, scores: {...}, gates: all pass}
T+0:17  orchestrator  →  LÊ verdict
T+0:17  orchestrator  →  APPEND em progress.md:
                       "## 2026-09-06T21:53:11Z | T-0.1 | PASS
                        - commit: abc1234
                        - cost_usd: 0.85
                        - duration_min: 16
                        - model: opus/sonnet/haiku
                        - attempt: 1/2
                        - notes: All files exist, agent registered, deterministic gates passed.
                        - next_action: advance"
T+0:18  orchestrator  →  EDITA tasks.md: T-0.1.status = done; cria T-0.2
T+0:18  orchestrator  →  EDITA roadmap.md se milestone inteiro DONE
T+0:19  orchestrator  →  exit ADVANCED
T+0:19  bash  →  timeout termina
T+0:19  bash  →  exit 0
        ▲
        └─── TICK COMPLETO. Próximo em 60min (ou amanhã se você desligar)
```

**O tick inteiro é fresh-context.** O próximo tick não sabe NADA do que aconteceu neste. A não ser que esteja escrito em `progress.md` ou `tasks.md`.

---

## 3. Procedimentos Executáveis (PASSO-A-PASSO)

### 3.1 Setup inicial (uma vez)

```bash
cd C:\Users\mathe\code_space\life-oss\life

# 1. Validar que todos os files estão lá
powershell -ExecutionPolicy Bypass -File .claude\loop\install.ps1

# 2. Confirmar o skill está visível para o Claude Code
# (o skill está em .claude/skills/loop-engineering/SKILL.md — auto-detected)
```

### 3.2 Primeiro tick manual (HUMAN-IN-THE-LOOP)

```bash
cd C:\Users\mathe\code_space\life-oss\life

# Dry run — vê o que seria invocado sem rodar o claude-code de verdade
bash .claude/loop/loop-tick.sh --dry-run

# Real run — INVOCA o orchestrator de verdade
bash .claude/loop/loop-tick.sh

# OU no Windows direto:
.claude\loop\loop-tick.bat
```

**O que observar:**
- Log vai pra `.claude/loop/logs/tick-YYYYMMDD-HHMMSS.log`
- Final da execução: `progress.md` tem 1 linha nova
- Custo típico do primeiro tick: $0.50 - $2.00

### 3.3 Inspecionar o que aconteceu

```bash
# Ver últimas 20 linhas do progress
tail -20 .claude/loop/progress.md

# OU no PowerShell:
Get-Content .claude\loop\progress.md -Tail 20

# Ver log completo do último tick
ls -t .claude/loop/logs/ | head -1
cat .claude/loop/logs/tick-*.log | head -50
```

### 3.4 Iterar nos prompts (após 2-3 ticks)

Se o orchestrator falha consistentemente, edite o prompt em:
- `.claude/agents/loop/orchestrator.md` (estratégia)
- `.claude/agents/loop/worker.md` (execução)
- `.claude/agents/loop/verifier.md` (julgamento)

**NÃO edite `constitution.md` ou `AGENTS.md` (esses são read-only para o agent).**

### 3.5 Quando estiver estável (3-5 ticks OK): agendar

```bash
# Adiciona ao claude-flow daemon (que já tem audit 4h + optimize 2h)
bash .claude/helpers/daemon-manager.sh add \
  --name "loop-tick" \
  --interval "60m" \
  --command "bash $REPO/.claude/loop/loop-tick.sh" \
  --cost-cap-usd 5

# Confirma
bash .claude/helpers/daemon-manager.sh list
```

### 3.6 Quando chegar em M3: ligar hill-climb semanal

```bash
# Adiciona schedule semanal (domingo 02:00)
bash .claude/helpers/daemon-manager.sh add \
  --name "hill-climb" \
  --schedule "0 2 * * 0" \
  --command "bash $REPO/.claude/loop/hill-climb.sh" \
  --cost-cap-usd 2

# Manualmente
bash .claude/loop/hill-climb.sh
# Lê a proposta em .claude/loop/logs/hill-climb-YYYYMMDD.md
# Edita AGENTS.md se concordar
# Commita
```

### 3.7 Cancelar o loop (emergência)

```bash
# Para o daemon
bash .claude/helpers/daemon-manager.sh stop loop-tick

# OU mata o processo direto
# PowerShell:
Get-Process | Where-Object {$_.CommandLine -match "loop-tick"} | Stop-Process
```

---

## 4. Decisões Arquiteturais (Por que fiz assim?)

### Por que opus no orchestrator e haiku no verifier?

- **Orchestrator:** decisão estratégica, leitura longa, precisa de nuance → opus (mais capaz)
- **Worker:** execução focada, escopo pequeno, sonnet basta
- **Verifier:** julgamento binário (PASS/FAIL), rubrica estruturada → haiku (mais barato, ~3× menos que sonnet)

**Trade-off:** opus é 5-10× mais caro que haiku. Mas o orchestrator só roda 1× por tick. Worker/verifier rodam 1-3× cada. Manter opus no orchestrator e haiku no verifier é a melhor relação custo/qualidade.

### Por que arquivo .md para state em vez de SQLite/Postgres?

- **Git-friendly** (diff, blame, revert)
- **Legível por humanos** (você pode ler `progress.md` no Obsidian, no VS Code, no Notepad)
- **Sem dependência** (não precisa de DB rodando)
- **Já é o padrão do projeto** (`AGENTS.md`, `CLAUDE.md`, `centrals/*` são todos markdown)

**Trade-off:** Não dá pra query SQL. Mas o volume de dados é baixo (≤ 1 tick = 1 linha = ~300 bytes). Em 1 ano = ~50KB. Git vai bem com isso.

### Por que worktree por sub-agent em vez de branch só?

- **Isolamento de filesystem** (não só de git ref)
- **Deps separadas** (`uv sync` por worktree = independência total)
- **Cleanup trivial** (`worktree-helper.sh cleanup m-0.1`)

**Trade-off:** Disco extra (~500MB por worktree = Python deps). Mas você tem 1 TB, então é fine.

### Por que shell bash como tick (e não Python nativo)?

- **Ralph Wiggum canon** (`while :; do cat PROMPT.md | claude-code; done`)
- **Composabilidade** (combina com `cron`, `systemd`, `Task Scheduler`)
- **Debugabilidade** (`bash -x` mostra cada step)
- **Já está no seu toolkit** (Git Bash no Windows)

**Trade-off:** Bash + WSL no Windows às vezes dá path issues. Por isso o `.bat` wrapper + o `install.ps1` em PowerShell.

### Por que progress.md é append-only?

- **Imutabilidade** (qualquer agente pode escrever, ninguém conflita)
- **Audit trail** (git log mostra cada tick)
- **Anti-anti-pattern** (não dá pra "reescrever a história")

**Trade-off:** Se você errar, tem que append uma `## AMEND` entrada. Mas é isso que você quer.

### Por que constitution.md separado de AGENTS.md?

- **AGENTS.md:** regras operacionais, pode crescer, agent pode ler mas não editar
- **constitution.md:** princípios imutáveis, gates todo milestone, human-only

**Por que separar?** Porque constitution é LOAD-BEARING (se quebrar, todo o loop falha). AGENTS é operational. Mixar = agente pode tocar em algo que devia ser imutável.

---

## 5. Mapa de Arquivos (Referência Rápida)

```
.claude/loop/                              # Tudo do loop vive aqui
├── README.md                              # Quick start (5min read)
├── CURATED-TECHNIQUES.md                  # 35+ técnicas com stars/mentions
├── IMPLEMENTATION-GUIDE.md                # ESTE ARQUIVO (deep dive)
├── constitution.md                        # 7 princípios + 4 anti-patterns
├── roadmap.md                             # M0 → M9 milestones
├── tasks.md                               # T-0.1, T-0.2, ... atomic tasks
├── progress.md                            # Append-only tick log
├── loop-tick.sh                           # Bash Ralph-style tick
├── loop-tick.bat                          # Windows wrapper
├── hill-climb.sh                          # Weekly self-improvement
├── install.ps1                            # PowerShell verification
└── logs/                                  # tick-*.log, hill-climb-*.md

.claude/agents/loop/                       # 3 agent definitions
├── orchestrator.md                        # opus, state machine
├── worker.md                              # sonnet, maker
└── verifier.md                            # haiku, checker

.claude/skills/loop-engineering/           # 1 skill (auto-invocável)
└── SKILL.md                               # Pattern documentation

scripts/                                   # 1 helper
└── worktree-helper.sh                     # Git worktree CRUD
```

---

## 6. Glossário (use em qualquer conversa sobre o loop)

- **Tick:** 1 iteração completa do loop = 1 invocação do orchestrator + 0-N sub-agents + 1 linha no progress.md
- **Milestone:** unidade de roadmap (M0, M1, ..., M9). Concretiza um goal.
- **Task:** unidade atômica (T-0.1, T-0.2, ...). Concretiza um milestone.
- **Verdict:** output do verifier = {PASS, FAIL, NEEDS_FIX}
- **Worktree:** git worktree isolado por sub-agent. Cleanup post-merge.
- **Deterministic gate:** pytest/ruff/mypy. Deve passar ANTES do LLM judge.
- **Constitution gate:** `constitution.md` anti-patterns. Verifier checa.
- **Hill-climb:** loop 4, semanal. Lê traces, propõe PR. NÃO auto-merge.
- **Cost cap:** USD máximo por tick. Hard kill se exceder.
- **Completion promise:** string única que o agent outputa pra indicar "done" (padrão Ralph).

---

## 7. Comandos Úteis (cheat sheet)

```bash
# Estado
cat .claude/loop/progress.md | tail -10          # últimas 10 ticks
cat .claude/loop/roadmap.md | head -50            # milestones
cat .claude/loop/tasks.md | grep "status:"        # status de todas as tasks
cat .claude/loop/constitution.md                  # princípios

# Controle
bash .claude/loop/loop-tick.sh                    # rodar tick
bash .claude/loop/loop-tick.sh --dry-run          # sem executar
bash .claude/loop/hill-climb.sh                   # análise semanal
bash .claude/helpers/daemon-manager.sh list        # schedules ativos
bash .claude/helpers/daemon-manager.sh stop loop-tick  # parar

# Inspeção
ls .claude/loop/logs/                             # logs por tick
git -C .worktrees/m-0.1/ log --oneline          # commits do worktree
git worktree list                                  # todos os worktrees

# Manutenção
bash scripts/worktree-helper.sh cleanup-all        # limpar todos os worktrees
```

---

## 8. Quando o Loop Falha (Troubleshooting)

| Sintoma | Causa provável | Fix |
|---|---|---|
| Tick não roda | Bash não encontrado no PATH | `where bash` no PowerShell; instalar Git for Windows |
| Tick sai em 5min sem nada no progress | Claude-code não instalado | Verificar Claude Code CLI |
| `progress.md` tem FAIL × 5 consecutivos | Constitution muito rígida OU prompt worker confuso | Editar `constitution.md` (human!) ou `.claude/agents/loop/worker.md` |
| `cost_usd: $5.00` toda tick | Worker gasta muito | Reduzir escopo da task OU usar opus só em tasks críticas |
| `OVERRUN: tick exceeded 30min` | Loop preso em retry loop | Kill; inspecionar `tasks.md`; talvez reescrever prompt |
| `## BLOCKED` no progress.md | Constitution violation OR spec ambíguo | Ler `notes:` no BLOCKED; editar SPEC.md ou constitution |
| Worker edita AGENTS.md | Prompt permite; precisa ser proibido explicitamente | Adicionar em `worker.md` na seção HARD RULES |
| Hill-climb cria PR lixo | Pattern analysis muito genérico | Adicionar `human_only_topics` em `hill-climb.sh` |

---

## 9. Filosofia (o que NÃO fazer)

> **DON'T** tentar fazer o loop ser mais esperto. Mais simples = mais confiável.
>
> **DON'T** adicionar features sem passar pelo gate da constitution.
>
> **DON'T** editar `constitution.md`, `AGENTS.md`, `CLAUDE.md` automaticamente.
>
> **DON'T** pular deterministic gates pra "ir mais rápido".
>
> **DON'T** usar o mesmo modelo pra worker e verifier.
>
> **DON'T** aceitar PASS sem verificar constitution anti-patterns.
>
> **DON'T** deixar `progress.md` virar novela. 1 linha por tick. ≤500 chars notes.

> **DO** ler `progress.md` antes de cada tick (10 últimas linhas).
>
> **DO** iterar nos prompts baseado em falhas observadas.
>
> **DO** rodar manual primeiro, agendar só depois.
>
> **DO** manter o worktree limpo (cleanup após merge).
>
> **DO** deixar o hill-climb SEMPRE sob revisão humana.
>
> **DO** expandir `constitution.md` se anti-patterns novos emergirem.
