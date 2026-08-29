# 18 — Pattern: 3-Layer System Prompt (Constitutional → IKIGAI → PAV)

> **Categoria:** PATTERN (Layer 3 — Patterns catalog, posição #18)
> **Anchor canônico:** `src/ikigai/src/agents/deepagents_harness.py:45-245` (`_SYSTEM_PROMPT` constante de módulo)
> **Público:** Eu mesmo + agentes futuros
> **Idioma:** PT-BR prose + EN technical terms (system prompt, HITL, interrupt_on, regex, append-only, fork, regime, FSM, MCP, checkpoint, JsonLogic, ID)

---

## §1 — Intuição

O **3-layer system prompt** é o pattern que organiza o prompt do Deep Agent (`create_deep_agent`) em três camadas semanticamente separadas e formalmente delimitadas por banners Unicode `━━` no `_SYSTEM_PROMPT` string: **Layer 1 — CONSTITUTIONAL** (`strategics/`, read-only, immutable, base filosófica — tensão→comportamento→solução + 5 tensões + 4 regimes), **Layer 2 — IKIGAI STRATEGIC** (5 vetores, 5 fases, 4 regimes com histerese assimétrica, time horizons SONHO/PHASE/TRIMESTRE/ONDA/CYCLE/WEEKLY, fórmula Q_HE, heurísticas H1-H6), e **Layer 3 — PAV OPERATIONAL** (substrate que produz `QHEMetrics`, `PolicyDecision`, `PolicySetpoints`, `HabitState` — IKIGAi consome esses outputs para calcular os 5 vetores). A separação é load-bearing porque cada camada tem **contrato de mutabilidade distinto**: Layer 1 nunca muda (constitutional), Layer 2 muda quando o projeto evolve (project conventions), Layer 3 muda diariamente (operational telemetry) — colapsar as três em um único prompt monolitíco destruiria essa invariante temporal e forçaria re-load do contexto completo a cada policy transition. O pattern também ganha extensibilidade per-fork via **barrel `IKIGAI_TOOLS`** em `tools.py:930-953`: cada fork-pronta (tuiboard = 4 tools, taskdog = 3 tools, solverforge-calendar = 2 tools) adiciona suas tools sem tocar o `_SYSTEM_PROMPT` — o prompt só conhece os tools via nome + docstring, e `deepagents` lib cuida do roteamento. O **HITL `interrupt_on={"write_file": True}`** (linha 282) pausa o LangGraph runtime antes de qualquer `write_file` no `FilesystemBackend`, dando ao operador humano aprovação/rejeição granular em cada escrita de vault markdown — defense-in-depth contra o agent gerar ciclo log corrompido ou notas duplicadas.

---

## §2 — Enunciado Formal

### 2.1 Definição verbatim do anchor

**Localização:** `src/ikigai/src/agents/deepagents_harness.py:45-67` (Layer 1 — CONSTITUTIONAL) + `:71-131` (Layer 2 — IKIGAI STRATEGIC) + `:134-150` (Layer 3 — PAV OPERATIONAL)

O prompt é um único string literal `_SYSTEM_PROMPT` de ~200 linhas, estruturado como:

```text
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 1 — CONSTITUTIONAL (strategics/ — read-only reference)   │
│    - Tensão → Comportamento → Solução                            │
│    - 5 tensões (tensions)                                        │
│    - 4 regimes                                                   │
│    - Invariante: "Never contradict or rewrite strategics/"       │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 2 — IKIGAI STRATEGIC                                      │
│    - 5 VECTORS (passion, skill, market, revenue, course)        │
│    - 5 PHASES (FUNDAÇÃO, BUSCA, HACKATHON, RECUPERAÇÃO, OVERCLOCK) │
│    - 4 REGIMES com histerese assimétrica                         │
│    - TIME HORIZONS (SONHO=547d, PHASE=180d, TRIMESTRE=90d, ...)  │
│    - Q_HE FORMULA (H + E + S_bonus)                              │
│    - H1-H6 HEURISTIC SIGNALS                                     │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 3 — PAV OPERATIONAL                                       │
│    - What PAV produces: QHEMetrics, PolicyDecision, HabitState   │
│    - What IKIGAI reads from PAV: q_he_score, regime_state, ...   │
└──────────────────────────────────────────────────────────────────┘
```

**Snippet verbatim do anchor (linhas 57-68 — Layer 1):**

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LAYER 1 — CONSTITUTIONAL (strategics/ — read-only reference)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The strategics/ directory is the constitutional layer: it NEVER changes and is the
foundation for all decisions. Key concepts:
- Tensão → Comportamento → Solução: tension drives behavior drives solution
- 5 tensões (tensions) that shape strategy
- 4 regimes that govern workload envelopes

When reasoning about strategic decisions, ground them in these constitutional principles.
Never contradict or rewrite strategics/ content.
```

**Snippet verbatim (linhas 86-91 — Layer 2 phase weights):**

```text
Phase weights (vector distribution per phase):
  FUNDAÇÃO:    passion=0.35, skill=0.30, market=0.15, revenue=0.10, course=0.10
  BUSCA:       passion=0.25, skill=0.25, market=0.25, revenue=0.15, course=0.10
  HACKATHON:   passion=0.20, skill=0.15, market=0.20, revenue=0.30, course=0.15
  RECUPERAÇÃO: passion=0.30, skill=0.30, market=0.15, revenue=0.10, course=0.15
  OVERCLOCK:   passion=0.25, skill=0.15, market=0.15, revenue=0.30, course=0.15
```

**Snippet verbatim (linhas 99-104 — Layer 2 regime hysteresis):**

```text
Hysteresis rules (asymmetric — down is faster than up):
  Upgrade to PUSH:      3 consecutive days at Q_HE ≥ 0.85
  Downgrade to RECOVER:  2 consecutive days at Q_HE < 0.60
  RECOVER → REDUCE:      3 consecutive days at Q_HE ≥ 0.60
  Emergency RECOVER:     Q_HE < 0.30 OR infractions ≥ 3 (immediate, no hysteresis)
  PUSH early warning:    infractions ≥ 2 → drops to REDUCE immediately
```

**Invariante load-bearing da Layer 1:** o conteúdo de `strategics/` é **constitucional** — o prompt declara explicitamente "Never contradict or rewrite strategics/ content" (linha 68). Se um tool retornar metadata que contradiz a tensão filosófica, o LLM é instruído a preferir o strategics. Defense-in-depth contra prompt injection via fork-pronta.

### 2.2 Layer 3 (PAV OPERATIONAL) — substrate contract

**Localização:** `src/ikigai/src/agents/deepagents_harness.py:137-150`

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LAYER 3 — PAV OPERATIONAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PAV (Operational Layer) measures habit consistency, energy, and policy decisions.
IKIGAI consumes PAV outputs as substrate for the 5-vector scores.

What PAV produces:
  QHEMetrics      — daily habit quality composite (H_avg, consistency, streak_bonus, energy_ratio)
  PolicyDecision   — regime assignment + workload envelope for the day
  PolicySetpoints  — hardwork_budget, pause_min, sleep_target, Q_HE target
  HabitState       — per-habit daily records (streak, effort_minutes, completed)

What IKIGAI reads from PAV:
  q_he_score      — QHE composite from most recent QHEMetrics
  regime_state    — PUSH | MAINTAIN | REDUCE | RECOVER from PolicyDecision
  days_in_regime  — consecutive days in current regime
  corrections      — H1–H6 heuristic signals (ikigai_corrections tool)
```

**Invariante load-bearing:** Layer 3 é **read-only do ponto de vista do IKIGAi**. O agent consome `QHEMetrics` via `ikigai_score`, `ikigai_regime`, `ikigai_phase`, `ikigai_corrections` (8 IKIGAi tools em `tools.py:96-352`), mas nunca escreve de volta no PAV. Writes vão via `ikigai_sync_vault` para vault markdown, não para o SQLite do PAV (`~/.ikigai/ikigai_checkpoints.db`). Separação unidirecional — IKIGAi → vault → humano → PAV (se necessário).

### 2.3 Extensibilidade per-fork via barrel `IKIGAI_TOOLS`

**Localização:** `src/ikigai/src/agents/tools.py:930-953` (lista canônica exportada)

```python
IKIGAI_TOOLS = [
    # IKIGAi internal tools
    ikigai_score,
    ikigai_regime,
    ikigai_phase,
    ikigai_corrections,
    ikigai_decompose,
    ikigai_plan_cycle,
    ikigai_sync_vault,
    ikigai_checkpoint,
    # Solverforge Calendar
    solverforge_list_events,
    solverforge_create_event,
    # Tuiboard kanban
    tuiboard_list_boards,
    tuiboard_get_tasks,
    tuiboard_update_task,
    tuiboard_create_task,
    # Taskdog task management
    taskdog_list_tasks,
    taskdog_create_task,
    taskdog_complete_task,
    taskdog_get_task,
]
```

**Mecânica load-bearing:** cada nova fork-pronta (futuro: `pomodoro`, `calendar-google`, `notion`, `linear`) adiciona seu bloco de tools ao barrel `IKIGAI_TOOLS` em `tools.py` **sem modificar o `_SYSTEM_PROMPT`** em `deepagents_harness.py`. O prompt tem 18 tools documentados em uma seção `TOOLS` (linhas 173-206) que é sincronizada manualmente, mas a **verdade runtime** é o barrel Python. Extensibilidade vem da separação prompt/docs (manuais) vs barrel/registry (executável). Adicionar `pomodoro_*` tools requer:

1. Criar `@tool` decorators em `tools.py`
2. Append ao barrel `IKIGAI_TOOLS`
3. Atualizar a seção TOOLS do `_SYSTEM_PROMPT` (manual, append-only)

Pela invariante append-only (`docs/CLAUDE.md` §"Global Conventions"), não se remove tools — apenas se adiciona.

### 2.4 HITL — `interrupt_on={"write_file": True}`

**Localização:** `src/ikigai/src/agents/deepagents_harness.py:279-282`

```python
    # Human-in-the-loop: pause before any tool that writes
    interrupt_on = None
    if human_in_the_loop:
        interrupt_on = {"write_file": True}
```

A flag `human_in_the_loop` é opt-in via CLI flag `--human-in-the-loop` (linhas 332-335 do argparse). Quando ativada, `deepagents` library configura o LangGraph runtime para fazer `interrupt()` antes de invocar qualquer tool que escreva — em particular, o `write_file` do `FilesystemBackend` (linha 285-288). O operador humano recebe um prompt com o conteúdo que seria escrito e aprova/rejeita antes da execução. **Importante:** o `interrupt_on` é declarativo em dict (`{"write_file": True}`), não um callback Python — `deepagents` lib traduz essa declaração em `BeforeToolCall` hook no LangGraph runtime. Defense-in-depth contra:

- LLM gerar conteúdo que sobrescreve notas críticas do vault
- Loop infinito de write_file que preenche o disco
- Tool injection via fork-pronta (tuiboard/taskdog) que tenta escrever fora do escopo declarado

### 2.5 Vault hierarchy + UEID (cross-layer integration)

**Localização:** `src/ikigai/src/agents/deepagents_harness.py:153-167`

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VAULT HIERARCHY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Vault root: data/matheus/
  dreams/           — SONHOS root objectives (547d horizon)
  objectives/       — TRIMESTRE goals (90d)
  projects/         — ONDA deliverables (30d)
  deliverables/     — CYCLE outputs (7d)
  ikigai_state/     — cycle logs, profile snapshots

UEID format: ikigai:<entity_type>:<slug>:<8-hex-uuid>:<8-hex-content-hash>
  entity_type: dream | objective | project | deliverable | profile | cycle

Use ikigai_decompose(ueid) to walk the hierarchy:
  ikigai_decompose("ikigai:dream:vaga-remota-2026:...")
  → returns full tree: dream → objectives → projects → tasks
```

**Conexão com Pattern #10 (UEID tri-key):** a regex UEID para IKIGAi é `ikigai:<entity_type>:<slug>:<uuid>:<hash>` — divergente da regex genérica `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` (ver `docs/design-system/10-pattern-ueid-tri-key.md` §2.1) porque o anchor do system prompt usa prefixo `ikigai:` (6 chars) + slug + **8-hex-uuid** (não 36-char UUID v4) + **8-hex-content-hash** (não 16-hex). Adaptação local — IKIGAi UEIDs são **mais curtos** que mesh UEIDs porque o vault é um filesystem, não um SQLite UNIQUE column.

### 2.6 Invariantes load-bearing (resumo verificável)

| # | Invariante | Verificação (path:line) |
|:-:|:-----------|:------------------------|
| 1 | 3 layers delimitadas por banners `━━` em `_SYSTEM_PROMPT` | `deepagents_harness.py:57-58, 70-71, 133-134` |
| 2 | Layer 1 declara "Never contradict or rewrite strategics/ content" | `deepagents_harness.py:68` |
| 3 | Layer 2 lista 5 phases com weights Σ=1.0 (per-line) | `deepagents_harness.py:87-91` (5 linhas, cada Σ=1.00) |
| 4 | Layer 3 declara IKIGAi como read-only de PAV | `deepagents_harness.py:137-150` |
| 5 | `interrupt_on={"write_file": True}` quando `human_in_the_loop=True` | `deepagents_harness.py:279-282` |
| 6 | Barrel `IKIGAI_TOOLS` é o registry runtime de extensibilidade | `tools.py:930-953` |
| 7 | `FilesystemBackend(root_dir=Path.home(), virtual_mode=False)` para acesso irrestrito | `deepagents_harness.py:285-288` |
| 8 | Idioma PT-BR mandatory no final do prompt (linhas 239-245) | `deepagents_harness.py:239-245` |

---

## §3 — Justificativa

### 3.1 Razões técnicas

**Por que 3 layers (em vez de flat prompt)?**
O prompt tem ~200 linhas. Flat prompt seria ilegível e impossibilitaria versionamento independente — uma mudança em `phase_weights` (Layer 2) exigiria diff/review de todo o bloco, contaminando revisões de Layer 1 (philosophical) ou Layer 3 (operational). A separação em 3 layers permite:

1. **Diff minimization**: edit Layer 2 weight de uma fase toca 1 linha (`deepagents_harness.py:90`), sem cruzar com Layer 1 (read-only) ou Layer 3 (operational telemetry).
2. **Cognitive load no LLM**: o LLM consegue parsear 3 seções nomeadas com banners explícitos mais rápido do que 200 linhas de prosa contínua. O banner `━━` é um `section delimiter` que ajuda o attention mechanism a segmentar o contexto.
3. **Audit trail por camada**: PR que altera Layer 1 é filosófico (rastreável via commit message "constitutional: ..."). PR que altera Layer 2 é algorítmico. PR que altera Layer 3 é telemetry. Reviewer sabe imediatamente o **tipo de mudança** pelo layer tocado.

**Por que Layer 1 é read-only (constitutional)?**
`strategics/` é a documentação PT-BR fundacional do sistema (`strategics/Hierarquia de Objetivos.md`, `Planejamento (Estratégico e Tático).md`, etc.) que foi escrita **antes** do código IKIGAi existir. Ela carrega a visão: "tensão → comportamento → solução" — o framework filosófico que justifica **por que** existem 5 vetores e 4 regimes. Se o IKIGAi contradissesse essa visão, o sistema perderia sua coerência narrativa (cite-se [[legacy-pav-ui-era-2026-08-28]] — eras passadas já perderam coerência ao divergir de strategics). A invariante "Never contradict or rewrite strategics/ content" é **ontológica**, não técnica.

**Por que Layer 3 é read-only do IKIGAi (mas write do PAV)?**
PAV mede hábito real (H_avg, streak, energy_ratio). IKIGAi **interpreta** essas medidas para gerar regime/phase/corrections. Se IKIGAi escrevesse de volta no PAV, teríamos **circular dependency**: IKIGAi decide regime baseado em PAV → escreve de volta no PAV → PAV muda → IKIGAi re-decide → loop. A separação unidirecional (PAV → IKIGAi → vault → humano → PAV se necessário) preserva a causalidade.

**Por que HITL só em `write_file` (não em todos os tools)?**
Os 18 tools incluem `read_file`, `ls`, `grep` (read-only — sem side effects), `ikigai_score`/`regime`/`phase`/`corrections` (lê checkpoint DB — idempotente), `tuiboard_list_boards` (read-only), etc. Pausar HITL em tools read-only seria **friction sem benefício**: o operador humano aprova 100% das leituras, fadiga decisória. `write_file` é o único tool com side-effect irreversível (filesystem write); portanto é o único onde HITL agrega valor. O dict `interrupt_on={"write_file": True}` é uma **whitelist explícita** — fácil auditar quais tools pausam.

### 3.2 Alternativas consideradas (e por que perderam)

| Alternativa                | Prós                                | Contras                                                                  | Veredito |
|:---------------------------|:------------------------------------|:-------------------------------------------------------------------------|:---------|
| Flat 200-line prompt       | Simples                             | Inlegível; diff cru; sem cognitive segmentation; impossível auditar       | Rejeitado |
| 2 layers (IKIGAI + PAV)    | Menos ceremony                      | Sem constitutional anchor; IKIGAi prompts podem contradizer strategics   | Insuficiente |
| Hierarchical agents (sub-agent per layer) | Modular | Custo de orquestração; state propagation complexa; LangGraph overhead | Rejeitado |
| YAML/JSON system prompt (machine-parsed) | Structured | LLM perde nuance da prosa; regex-brittle; revisão de prose é mais clara | Insuficiente |
| **3 layers em string literal com banners Unicode** | Legível + diffable + auditável | Manual sync entre prompt (prose) e barrel `IKIGAI_TOOLS` (code) | **Aceito** |

A alternativa rejeitada mais importante: **hierarchical sub-agents**. Cada layer como sub-agente LangGraph com seu próprio prompt + state. Pro: modularidade real (cada agent é testável isoladamente). Contra: orquestração custa 2-3× tokens por turno (sub-agent prompts carregados separadamente), state propagation entre agents é não-trivial (channels, reducers), e a profundidade do context window limita quantas layers você pode ter (3 é o teto prático). Para apenas 3 layers de policy/strategy/operation, **string-literal com banners** é mais simples e suficiente.

### 3.3 Por que este padrão vence

1. **Composabilidade via barrel**: nova fork (ex.: `pomodoro`, `notion`) adiciona tools sem tocar o `_SYSTEM_PROMPT`. O pattern é **open for extension, closed for modification** (princípio Open/Closed).

2. **HITL granular**: operador aprova apenas writes (não reads), reduzindo fadiga decisória. Whitelist explícita (`{"write_file": True}`) torna auditável quais tools pausam.

3. **PT-BR mandatory**: idioma do agente é fixado no final do prompt (linhas 239-245: "Idioma — Você DEVE responder SEMPRE em português brasileiro"). Não há "code-switching" — o agente nunca responde em inglês mesmo quando a pergunta é em inglês, preservando a identidade cultural do produto (cite-se `[[value-factory-portfolio-intent]]`).

4. **Append-only do prompt**: nenhuma das 3 layers foi **removida** desde o primeiro commit (`IKIGAiDeepAgent = None  # removed — use create_deep_agent via _make_agent` na linha 665). Mudanças são sempre aditivas (novos tools ao barrel, novas seções `━━` ao prompt). Compatível com a invariante global append-only do workspace (cite-se `[[docs-superseded-trailer-2026-08-28]]`).

5. **FilesystemBackend irrestrito**: `root_dir=Path.home()` (linha 286) dá ao agente acesso a TODO o filesystem. Combinado com HITL, isso permite que o usuário peça "check the vibe-ops project" e o agent faça `ls ~/code_space/life-oss/vibe-ops/` sem pré-configuração. Trade-off aceito: segurança compensada por HITL.

### 3.4 Limitações conhecidas (honest rigor — citação de doc 09)

**Análise crítica:** `docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md` — múltiplos findings afetam o conteúdo das 3 layers.

| Limitação | Severidade | Implicação para o system prompt |
|:----------|:----------:|:---------------------------------|
| **C7** — `compute_meta_vector` filters out v=0 vectors silenciosamente | MEDIUM | Layer 2 declara "5 vetores" mas o código exclui vetores com v=0 antes do cálculo. O prompt deveria explicitar: "compute_meta_vector pode emitir menos de 5 scores se vetor for 0.0; trate v=0 como 'ainda não medido'". Doc 09 §3.5 recomenda `inclusive_zero` mode. |
| **A5** — worked example em `22-meta-ikigai-meta-vector.md §3` claims ≈51 mas code retorna ≈25.4% | HIGH | O exemplo numérico em Layer 2 sobre `meta_vector_score` está errado. Se o LLM usar esse exemplo para calibrar, vai gerar respostas inconsistentes. Doc 09 §3.5 recomenda reescrever worked examples com 3 cenários canônicos. |
| **B5** — Hybrid 0.6/0.4 (geo + harm) é unjustified | MEDIUM | Layer 2 não documenta **por que** 60/40 e não 70/30 ou 50/50. Constante arbitrária; gate de 5 SONHO logs ([[data-first-methodology]]) para re-fit. |
| **F5** — pomodoro fork not wired (silent failure) | HIGH | O prompt lista 18 tools, mas o "pomodoro fork" prometido em `24-integration-mesh-ueid-propagation.md §4` **não existe**. Operator que peça pomodoro tracking via IKIGAi recebe "⚠️ tool não encontrado" — feature ausente sem trailer no prompt. |
| **E6 / E9 / E10** — funções referenciadas em docs mas ausentes no código (`compute_cognitive_debt`, `ucb_recalibrator`, `decision_flow`) | HIGH | Layer 2 menciona H4-H6 como "heuristic signals" mas 3 das 6 functions não existem no código. O prompt é **aspiracional**, não executável — gate de 5 SONHO logs para implementar ou remover. |
| **C5/C6** — policy FSM (Layer 2) tem 3 inconsistências doc↔code (REDUCE threshold 0.70 missing; PUSH→RECOVER diret prohibition bypassed by emergency) | MEDIUM | Layer 2 declara "PUSH→RECOVER direto proibido" mas emergency check (Q_HE<0.30) bypassa. Operador pode ser surpreendido por transição inesperada. Doc 09 §3.4 propõe `policy_thresholds.py` como single source of truth. |
| **B1/B2** — λ=0.093 (Lally 2010) derivation gap | MEDIUM | Layer 2 fórmula `H(t) = 1 − e^(−λ·streak)` usa constante que é **escolha**, não medição. Constante muda com `HABIT_LAMBDA` env var mas Layer 2 não menciona. |
| **HITL não aplicado a `tuiboard_update_task`, `taskdog_create_task`** | HIGH | O prompt configura `interrupt_on={"write_file": True}` mas os 18 tools incluem `tuiboard_update_task`, `taskdog_create_task`, `taskdog_complete_task`, `solverforge_create_event` — **todos escrevem**, mas só `write_file` é pausado. Bug latente: se o LLM chamar `taskdog_create_task` (não `write_file`), o HITL **não dispara**. Workaround atual: HITL só protege writes via `FilesystemBackend`, não via subprocess writes dos forks. |

### 3.5 Quando NÃO usar 3-layer system prompt

- **Agentes single-domain sem strategics** (ex.: pure task agent, code reviewer): constitutional layer é overhead. Use single-layer prompt focado em tools + persona.
- **Sub-agents hierárquicos** (researcher → writer → reviewer): cada sub-agente tem seu próprio context window; 3-layer prompt aqui consome 50%+ do context. Use sub-agents com prompt minimal + tool calling.
- **LLM com context window <8k tokens**: 200 linhas × ~50 tokens/linha = ~10k tokens só de system prompt. Modelos pequenos (gpt-3.5-turbo, haiku) saturam. Use model Sonnet/Opus ou comprima para 2 layers.
- **Casos onde o conteúdo de Layer 1 muda frequentemente**: se strategics/ é WIP (constantemente evolving), a invariante "Never contradict" se torna impossível de manter. Nesse caso, Layer 1 deveria ser **runtime-injected** (não baked into system prompt).

---

## §4 — Cross-references

### 4.1 Design-system docs (Layer 2 + Layer 3)

- **`docs/design-system/00-INDEX.md`** §3 — mapa de dependências posiciona 3-layer system prompt como Pattern #18 do Layer 3 (Patterns catalog), segundo da série 14-19 (Idempotency, Hysteresis, Meta-vector, Reliability, Prompt, Scaffold). Confirma Layer 1 (Topology) → Layer 2 (Canvases) → Layer 3 (Patterns) hierarquia.
- **`docs/design-system/04-canvas-mesh-architecture.md`** §3.3 — tabela de Adapter storage topology mostra como fork-prontas (tuiboard, taskdog, solverforge-calendar) ganham extensibilidade via ForkAdapter Protocol. Pattern #18 herda essa extensibilidade — cada fork adiciona tools ao barrel `IKIGAI_TOOLS` em `tools.py:930-953`.
- **`docs/design-system/05-canvas-contracts-architecture.md`** §3 — invariante verbatim "All models are `frozen=True, extra="forbid"`". Layer 2 do system prompt descreve contratos QHEMetrics, PolicyDecision, etc. — todos Pydantic strict.
- **`docs/design-system/06-canvas-agents-architecture.md`** §3 — doc canônico para Deep Agent factory; cita `interrupt_on={"write_file": True}` (§3, linha 50 deste doc anchor). Pattern #18 detalha a mecânica do HITL que o canvas resume.
- **`docs/design-system/07-canvas-sync-architecture.md`** §4 — bidirectional sync vault ↔ forks. Layer 3 do prompt declara IKIGAi como read-only do PAV; sync é via vault markdown (`ikigai_sync_vault` tool).
- **`docs/design-system/08-canvas-cybernetic-loop.md`** — Target→Sensor→Adjuster→Persist→Sync→Index loop. Layer 3 do prompt **é o sensor output** (QHEMetrics, PolicyDecision).
- **`docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md`** §3 — limitações conhecidas (C7, A5, F5, B5) citadas em §3.4 deste doc. Pattern #18 é afetado por essas inconsistências.
- **`docs/design-system/10-modelo-unificado-auto-feedback-estocastico.md`** §3 — modelo unificado. Layer 2 do prompt operacionaliza o 5-vector scoring + Q_HE formula.

### 4.2 auto-performance-os docs (PT-BR, 27 docs)

- **`docs/auto-performance-os/09-postulado-ikigai-5-vetores.md`** — doc canônico para os 5 vetores (passion, skill, market, revenue, course) que aparecem em Layer 2 do prompt.
- **`docs/auto-performance-os/14-engine-policy-engine-fsm.md`** — FSM de 4 regimes (PUSH/MAINTAIN/REDUCE/RECOVER) com histerese. Layer 2 do prompt documenta o mesmo FSM verbatim; cite-se limitação C5/C6 do doc 09 sobre drift doc↔code.
- **`docs/auto-performance-os/22-meta-ikigai-meta-vector.md`** §3 — meta-vector formula `meta = 0.6·geo + 0.4·harm` que Layer 2 do prompt menciona implicitamente. Worked example errado (A5) é citado em §3.4 deste doc.
- **`docs/auto-performance-os/21-meta-qhe-policy-mapping.md`** §2 — mapping QHE → regime. Layer 2 do prompt declara thresholds (0.85 PUSH, 0.70 MAINTAIN, 0.60 RECOVER); limitação C4 do doc 09 nota que `QHE_REDUCE_THRESHOLD = 0.70` é documentado mas **não existe** no código.
- **`docs/auto-performance-os/25-integration-deep-agent-sync.md`** — doc canônico para sync flow IKIGAi ↔ vault ↔ forks. Layer 3 do prompt operacionaliza esse sync.

### 4.3 Memory cross-refs

- **`[[interfaces-architecture-2026-08-27]]`** — dual-layer architecture (forks = user views; cli/tui = operator backend). Pattern #18 vive na camada "operator backend" — IKIGAi é o backend que escreve vault; forks são read-only views via tools no barrel `IKIGAI_TOOLS`.
- **`[[data-first-methodology]]`** — ADR-007 gate de **5 SONHO logs manuais** antes de qualquer algorithm polish. Limitações F5/E6/E9/E10 do doc 09 (features que o prompt promete mas código não implementa) estão gated por este critério — não escrever adapter novo até 5+ logs.
- **`[[master-branch-carro-chefe-2026-08-28]]`** — master = deep-agent bidirecionalmente sincronizando forks-prontas. Pattern #18 é o **system prompt** desse deep-agent — o pattern operacionaliza a narrativa canônica.
- **`[[algorithm-issues-registry]]`** — 31 inconsistências catalogadas. Pattern #18 é afetado por C7 (meta-vector filter), A5 (worked example), F5 (pomodoro fork), B5 (hybrid 0.6/0.4 unjustified), B1/B2 (λ derivation).
- **`[[ikigai-chat-harness-decisions]]`** — 8 ADRs aceitos em 2026-07-09 (UEID+Pydantic, 5 read-only skills, gh CLI subprocess, etc.). Pattern #18 é a implementação concreta dessas decisões: read-only skills viraram "5 IKIGAi internal tools"; UEID virou Layer 2 contrato.

### 4.4 Code anchors (verificados)

| Path | LOC / Conteúdo | Pattern |
|:-----|:---------------|:-------|
| `src/ikigai/src/agents/deepagents_harness.py:45-245` | `_SYSTEM_PROMPT` string de ~200 linhas com 3 layers | 3-layer prompt |
| `src/ikigai/src/agents/deepagents_harness.py:57-68` | Layer 1 (CONSTITUTIONAL) banner + content | Constitutional anchor |
| `src/ikigai/src/agents/deepagents_harness.py:74-131` | Layer 2 (IKIGAI) — 5 vectors, 5 phases, 4 regimes, time horizons, Q_HE, H1-H6 | IKIGAI conventions |
| `src/ikigai/src/agents/deepagents_harness.py:137-150` | Layer 3 (PAV) — read-only contract | Operational substrate |
| `src/ikigai/src/agents/deepagents_harness.py:155-167` | Vault hierarchy + UEID format | Cross-layer integration |
| `src/ikigai/src/agents/deepagents_harness.py:282` | `interrupt_on = {"write_file": True}` | HITL gate |
| `src/ikigai/src/agents/deepagents_harness.py:285-288` | `FilesystemBackend(root_dir=Path.home(), virtual_mode=False)` | Filesystem access |
| `src/ikigai/src/agents/deepagents_harness.py:305-317` | `create_deep_agent(...)` invocation | Agent factory |
| `src/ikigai/src/agents/tools.py:930-953` | `IKIGAI_TOOLS` barrel — 18 tools em 4 grupos | Fork extensibility |
| `src/ikigai/src/agents/tools.py:96-352` | 8 IKIGAi internal tools (`@tool` decorators) | Layer 2 → Layer 3 bridge |

---

## §5 — Fontes

### Code (verificado via Read tool)
- `src/ikigai/src/agents/deepagents_harness.py` — anchor primário (3-layer system prompt + HITL)
- `src/ikigai/src/agents/tools.py` — anchor secundário (18 tools barrel + IKIGAi internal tools)
- `src/ikigai/src/agents/reliability.py` — decorators `@retry_with_backoff`, `@circuit_breaker` (cross-ref Pattern #17)
- `src/ikigai/src/agents/ikigai_maintainer/state.py` — `IKIGAiStateDict`, `compute_meta_vector` (cross-ref Pattern #18 limitações C7, A5)
- `src/contracts/common.py` — UEID regex (cross-ref Pattern #10)
- `src/mesh/adapters/base.py` — `ForkAdapter` Protocol (cross-ref Pattern #13)

### Docs design-system
- `docs/design-system/00-INDEX.md` — mapa de dependências Layer 3
- `docs/design-system/04-canvas-mesh-architecture.md` §3.3 — fork extensibility via ForkAdapter
- `docs/design-system/05-canvas-contracts-architecture.md` §3, §4.1 — Pydantic strict; QHE contracts
- `docs/design-system/06-canvas-agents-architecture.md` §3 — Deep Agent factory; HITL `interrupt_on={"write_file": True}`
- `docs/design-system/07-canvas-sync-architecture.md` §4 — bidirectional sync vault ↔ forks
- `docs/design-system/08-canvas-cybernetic-loop.md` — Target→Sensor→Adjuster→Persist→Sync→Index
- `docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md` §3 — limitações C7, A5, F5, B5, C5/C6 (citadas em §3.4 deste doc)
- `docs/design-system/10-modelo-unificado-auto-feedback-estocastico.md` §3 — modelo unificado
- `docs/design-system/10-pattern-ueid-tri-key.md` §2.1 — UEID regex (cross-layer integration)

### Docs auto-performance-os (PT-BR)
- `docs/auto-performance-os/09-postulado-ikigai-5-vetores.md` — 5 vetores canônicos
- `docs/auto-performance-os/14-engine-policy-engine-fsm.md` — FSM 4 regimes com histerese
- `docs/auto-performance-os/21-meta-qhe-policy-mapping.md` §2 — QHE → regime mapping (limitação C4 do doc 09)
- `docs/auto-performance-os/22-meta-ikigai-meta-vector.md` §3 — meta-vector formula (limitação A5 do doc 09)
- `docs/auto-performance-os/25-integration-deep-agent-sync.md` — sync flow IKIGAi ↔ vault ↔ forks

### Memory cross-refs
- `[[interfaces-architecture-2026-08-27]]` — dual-layer architecture (forks user views, cli/tui operator backend)
- `[[data-first-methodology]]` — ADR-007 5 SONHO logs gate (gating F5/E6/E9/E10 fixes)
- `[[master-branch-carro-chefe-2026-08-28]]` — master = deep-agent bidirecional sync
- `[[algorithm-issues-registry]]` — 31 issues (cite-se C7, A5, F5, B5, B1/B2, C5/C6)
- `[[ikigai-chat-harness-decisions]]` — 8 ADRs aceitos 2026-07-09

### Padrões relacionados (este docset)
- **Pattern #10** — UEID tri-key (cross-layer integration via vault hierarchy)
- **Pattern #11** — Frozen Pydantic strict mode (Layer 2 contratos QHEMetrics, PolicyDecision)
- **Pattern #12** — Append-only queue (`ikigai_sync_vault` tool + `data/review_queue/`)
- **Pattern #13** — ForkAdapter Protocol (extensibilidade per-fork que Pattern #18 herda)
- **Pattern #14** — Idempotent UPSERT (UEID UNIQUE constraint habilita HITL-safe replays)
- **Pattern #15** — Hysteresis FSM (Layer 2 do prompt operacionaliza o FSM 4-state)
- **Pattern #17** — Reliability decorator stack (`@retry_with_backoff` + `@circuit_breaker` em tools)

---

> **Próxima ação recomendada:** após 5 SONHO logs ([[data-first-methodology]] gate), revisar o bug latente do HITL — `interrupt_on={"write_file": True}` não pausa `tuiboard_update_task`/`taskdog_create_task`/`solverforge_create_event` (apenas `write_file` do `FilesystemBackend`). Sugestão: estender o dict para `{"write_file": True, "tuiboard_update_task": True, "taskdog_create_task": True, "solverforge_create_event": True}` ou implementar `BeforeToolCall` hook genérico que pausa qualquer tool com `write` no nome.
