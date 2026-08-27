# Session Handoff — IKIGAi Persona Vault Init — 2026-07-03

> **Purpose.** Self-contained summary to paste into a fresh chat after context wipe. Contains: where we are, what was decided, what is pending, and the exact commands to resume. Designed for one-shot reinjection — no other files need to be read first.
>
> **Origin session.** `f67a9ee4-9b75-4d85-bfaf-62a16f25573b` — Chat compacted twice; this handoff captured at the third request.

---

## 1. Contexto e objetivo

**Tarefa atual.** Criar uma pasta de dataset **production-bound** com a persona do **Matheus Mendes** diretamente em `life-ops/ikigai/data/matheus/`. O código em `src/ikigai/` (Pydantic v2) vai ler essa pasta quando wirado — após 5+ SONHOs manuais. A pasta `.omo/ikigai/mock-datasets/` (Marina Souza) permanece como **meta-model** read-only.

**Verbatim do user (PT-BR):**
> *"vamos criar uma pasta de dataset com a minha persona direto em @life-ops\ikigai onde vamos codar o sistema depois que vai interagir com esses dados ja pensando em producao! pois vamos deixar .omo/ikigai/mock-datasets/ como um meta modelo onde vamos explorar estruturacao de templates, etc.."*

**Localização escolhida:**
> *"just /data versionado e auditavel.. nao me importo em expor"*

→ Path: `life-ops/ikigai/data/matheus/` — versionado em git, **sem** gitignore, **sem** exfiltração.

**Estado atual (2026-07-03):**
- Plano completo em `C:\Users\mathe\.claude\plans\logical-gliding-church.md` (~385 linhas).
- Plan mode **ativo** (não executado ainda).
- **0 arquivos criados** em `data/matheus/`.
- **0 commits** (working-tree only — padrão da sessão).
- Plan file tem pequenas stale annotations sobre Option Y vs Z (não-bloqueantes; usar Option Z).

---

## 2. Decisões já tomadas (não reabrir)

### 2.1 Socratic Q1–Q4 (pré-compaction)

| # | Pergunta | Resposta verbatim |
|---|----------|-------------------|
| **Q1** | Quando mexer no código? | *"ainda nao vamos mexer em nada tecnicamente.. vamos nos manter no data-first por enquanto... pois o codigo deve sempre emergir apartir dos dados!"* |
| **Q2** | Nicho / vetor de mercado? | **Generalista pipeline** — Data/Analytics/BI consulting + AI/LLM tooling + Dev tools. *"como um grande pipeline de dados que me da municao suficiente para construir artefatos de software, como diferencial de arbitragem em ampla concorrecia, e ancoregem para negociar salarios e contratos... (precificacao por assimetria de informacao)"* |
| **Q3** | Modalidade + stack + salário? | **100% remoto primary** (Salvador híbrido fallback), **Python/Polars stack**, intl-friendly TZ, salary floor *"tanto faz para primeira vaga"*, *"foco maximo para remoto!"* |
| **Q4** | Weekly budget + roles? | **Variável** (definir na SEMANA, não no SONHO); **40+ h/semana**; **6 target roles**: Data Engineer, Analytics Engineer, BI Analyst, Data Analyst, ML/AI Engineer, Solutions Consultant, Fullstack, Backend |

### 2.2 3 Resolved Decisions (via AskUserQuestion)

| ID | Decisão | Implicação |
|----|---------|-----------|
| **R1** | SONHO horizon = **Option Z** | Editar `dream.py:17` Literal set para incluir `547`. 1 line code edit. |
| **R2** | Layout = **Flat** | `dreams/vaga-remota-2026.md` (não subpasta). Compatível com `MarkdownDB.path_for()` que gera `<subdir>/<slug>.md`. |
| **R3** | ONDA inicial status = **`draft`** | Diferido de `planned` para evitar claim spurio de execução. |

### 2.3 Vector weights policy (Option C deferral)

- **Pesos iguais** (P=S=M=R=C=0.20) em SONHO e todos os níveis inferiores até **5+ SONHOs logs manuais**.
- Se SONHO assimétrico (ex: R=0.40, S=0.25...), adicionar campo informal `_intent_vector: revenue` em `custom:`. **NÃO** mexer no schema.
- Migration paths A/B (Option A = `principal_vector` field; Option B = asymmetric weights Σ=1.0) documentados em `.omo/ikigai/meta/perspective-log-2026-07-03.md`.
- **Revisit trigger:** após 5+ SONHOs logs com reflexão explícita do user.

### 2.4 Friction log deferrals (NÃO resolver agora)

| ID | Issue | Status |
|----|-------|--------|
| **N01** | 5 vs 4 IKIGAi vectors (README vs templates vs code) | Defer — precisa decisão do user |
| **A02** | RECOVER trigger (3 thresholds distintos: 0.30/0.60/sleep_debt/consecutive_misses) | Defer |
| **D02** | SCALAR path `life/vibe-ops/src/` vs `life-ops/operational/` (viola Standalone invariant) | Defer — doc fix only |
| **M01** | Append-only status of `_templates_periodos_v2/` | Defer — pode requerer Refactor Protocol |

Todas ficam no `algorithm-issues-registry.md` até 5+ SONHOs reais.

---

## 3. Arquivos — onde estão, o que fazer

### 3.1 Plan file (Edit-Only-In-Plan-Mode)
**`C:\Users\mathe\.claude\plans\logical-gliding-church.md`** (~385 linhas)

Status: escrito pré-compaction; substance correto mas com stale annotations menores (linhas 27, 313-318, 332, 382-385 mencionam "Option Y" em vez de "Option Z"). Tratar como no-op — usar Option Z conforme R1.

Estrutura: Context → Constraints → Folder Layout (flat) → Files to Create (5) → Files NOT to Create → UEID Strategy → Verification → Out of Scope → Critical Files → Reused Patterns → Decision Pending.

### 3.2 Code path que será editado (1 linha)
**`C:\Users\mathe\code_space\life-oss\life\life-ops\ikigai\src\ikigai\entities\plan\dream.py:17`**

```python
# ANTES:
horizon_days: Literal[1825, 2190, 2555, 2920, 3285, 3650]

# DEPOIS (Option Z, decisão R1):
horizon_days: Literal[547, 1825, 2190, 2555, 2920, 3285, 3650]
```

Por quê: `DreamEntity` usa `Literal` set fechado. SONHO 2026-07-06 → 2027-12-31 = 547 dias corridos (≈ 18 meses). Sem a edição, `PlanEntity.model_validate()` rejeita a YAML.

### 3.3 Schema-critical references (READ-ONLY, não modificar)
| Path | Linha | Função |
|------|-------|--------|
| `life-ops/ikigai/src/ikigai/entities/base.py` | 128-156 | `PlanEntity.from_frontmatter_dict()` — polymorphic base, UUID/slug/status/horizon_days/custom/tags |
| `life-ops/ikigai/src/ikigai/propagation/markdown_db.py` | 36-58 | `_dir_for()` — authoritative layout (`dreams/`, `objectives/`, `projects/`, `ikigai_state/`, `meta/`) |
| `life-ops/ikigai/src/ikigai/propagation/markdown_db.py` | 72-77 | `path_for()` — gera `<subdir>/<slug>.md` |
| `life-ops/ikigai/src/ikigai/propagation/markdown_db.py` | 86-115 | `write()` — atomic (`.tmp` → rename) |
| `life-ops/ikigai/src/ikigai/propagation/frontmatter.py` | 1-183 | `serialize_to_markdown`, `parse_from_markdown`, enum coercion |
| `life-ops/ikigai/src/ikigai/types.py` | 77-104 | `UEID.generate(namespace, entity_type, slug, content)` |
| `life-ops/ikigai/src/ikigai/enums.py` | 1-238 | VectorType, Phase, RegimeType, StatusType, IKIGAiVector literal sets |

### 3.4 Marina — meta-model reference (READ-ONLY)
**`.omo/ikigai/mock-datasets/00-sonho_example.md`** (208 linhas)
- Usar como template estrutural de body sections (Hipótese, Kill Conditions, Refactor Triggers, KPIs Macro).
- **NÃO** copiar valores (hipótese da Marina é "tech-lead em climate-tech", salário R$28k, etc.).
- **NÃO** copiar `sonho_id: marina.climate-tech-lead.2027` (UEID é per-persona).

### 3.5 5 arquivos de dados a CRIAR (post-plan-approval)

Layout flat em `life-ops/ikigai/data/matheus/`:

| Path | entity_type | horizon_days | status | regime |
|------|-------------|:---:|:---:|:---:|
| `README.md` | — (persona header) | — | — | — |
| `dreams/vaga-remota-2026.md` | dream (SONHO) | **547** | **seed** | maintain |
| `objectives/q3-2026-primeira-vaga.md` | objective (TRIMESTRE) | 90 | planned | push |
| `projects/onda-q3-1-pipeline-bi-cold-outreach.md` | project (ONDA) | 15 | **draft** (per R3) | push |
| `ikigai_state/profile-2026-07-03.json` | profile (snapshot) | 547 | active | — |

**UEID pattern:** `ikigai:<entity_type>:<slug>:<8-hex uuid>:<8-hex content_hash>` — placeholders OK no fill inicial.

**`custom` block para colar em DREAM/OBJECTIVE/PROJECT:**
```yaml
custom:
  _intent_vector: revenue              # informal annotation per Option C (NOT schema)
  _horizon_rationale: "18m horizonte sonhoreal (2026-07-06 → 2027-12-31); 547d = literal set extended via Option Z"
  verticals: [data-analytics, ai-llm-tooling, dev-tools]
  pricing_lever: info-asymmetry
  target_roles: [data-engineer, analytics-engineer, bi-analyst, data-analyst, ml-ai-engineer, solutions-consultant, fullstack, backend]
  non_negotiables:
    - "100% remoto primary (Salvador híbrido fallback)"
    - "Python/Polars stack"
    - "Intl-friendly timezone"
    - "Salary floor: 'tanto faz para primeira vaga'"
    - "Weekly budget: 40+ h/semana (definir na SEMANA)"
```

---

## 4. Próximos passos (sequência exata, copy-paste ready)

### Step 1 — `ExitPlanMode` (sai do plan mode)

```python
ExitPlanMode(allowedPrompts=[
    {"tool": "Bash", "prompt": "edit src/ikigai/entities/plan/dream.py literal set (1 line)"},
    {"tool": "Bash", "prompt": "create persona files under life-ops/ikigai/data/matheus/"},
    {"tool": "Bash", "prompt": "verify YAML frontmatter round-trips (no raise)"},
    {"tool": "Bash", "prompt": "check git working-tree status (no commits)"}
])
```

### Step 2 — Edit `dream.py:17`

```python
horizon_days: Literal[547, 1825, 2190, 2555, 2920, 3285, 3650]
```

### Step 3 — Criar diretórios

```bash
mkdir -p life-ops/ikigai/data/matheus/{dreams,objectives,projects,ikigai_state,meta}
```

### Step 4 — Criar 5 arquivos (Use Write tool com absolute paths)

1. **`life-ops/ikigai/data/matheus/README.md`** (~80 linhas) — persona header + link meta-model
2. **`life-ops/ikigai/data/matheus/dreams/vaga-remota-2026.md`** (~120 linhas) — DREAM
3. **`life-ops/ikigai/data/matheus/objectives/q3-2026-primeira-vaga.md`** — OBJECTIVE
4. **`life-ops/ikigai/data/matheus/projects/onda-q3-1-pipeline-bi-cold-outreach.md`** — PROJECT
5. **`life-ops/ikigai/data/matheus/ikigai_state/profile-2026-07-03.json`** — vector snapshot

### Step 5 — YAML round-trip verify

```bash
python -c "
import yaml
from pathlib import Path
files = [
    'life-ops/ikigai/data/matheus/dreams/vaga-remota-2026.md',
    'life-ops/ikigai/data/matheus/objectives/q3-2026-primeira-vaga.md',
    'life-ops/ikigai/data/matheus/projects/onda-q3-1-pipeline-bi-cold-outreach.md',
]
for f in files:
    fm = yaml.safe_load(Path(f).read_text().split('---')[1])
    ok = bool(fm.get('ueid') and fm.get('entity_type'))
    print(f, '→', 'OK' if ok else 'MISSING_FIELDS')
"
```

### Step 6 — Pydantic validate (opcional, se Poetry env ativo)

```bash
cd life-ops/ikigai
poetry run python -c "
from ikigai.entities.plan.dream import DreamEntity
from ikigai.entities.plan.objective import ObjectiveEntity
from ikigai.entities.plan.project import ProjectEntity
import yaml
from pathlib import Path

for entity_cls, path in [
    (DreamEntity, 'data/matheus/dreams/vaga-remota-2026.md'),
    (ObjectiveEntity, 'data/matheus/objectives/q3-2026-primeira-vaga.md'),
    (ProjectEntity, 'data/matheus/projects/onda-q3-1-pipeline-bi-cold-outreach.md'),
]:
    fm = yaml.safe_load(Path(path).read_text().split('---')[1])
    obj = entity_cls.model_validate(fm)
    print(obj.entity_type, obj.slug, '→', obj.title, 'OK')
"
```

### Step 7 — Confirmar working-tree (NO commit)

```bash
git status --short life-ops/ikigai/
```

Esperado: 1 modified (`src/ikigai/entities/plan/dream.py`) + 5 untracked (`data/matheus/*`).

### Step 8 — PARAR aqui

**Não fazer commit** — user controla timing. Working-tree changes only.

---

## 5. Constraints & invariants (NÃO violar)

### 5.1 De `CLAUDE.md` (project root) — load-bearing

| Regra | Onde aplica | Proíbe |
|-------|-------------|--------|
| **Standalone** | `life-ops/operational/` e `life-ops/ikigai/` | Imports de root `life/` ou `vibe-ops/` |
| **Append-only** | `vibe-ops/`, `strategics/`, cluster docs, `.omo/` | Deletar/podar/reescrever conteúdo existente |
| **Zero LLM** | Daily/weekly pipelines | NLP/LLM no hot path |
| **`--json` everywhere** | Todos novos CLI | Subcommand sem output machine-readable |
| **Pydantic v2 strict** | Todos schemas | `frozen=True`, `extra="forbid"`, strict mode |
| **Idempotent pipelines** | Sync/index/persist | Writes não-determinísticos — keys por `upstream_id`/`ueid` |
| **Fully local** | Repo inteiro | Cloud deps, API keys, OAuth |
| **PT-BR ↔ EN split** | Prose vs code | Prosa estratégica PT; código/paths/AI specs EN |
| **Error collection** | Todos handlers | Short-circuit em falha parcial |
| **Typer over argparse** | Novos CLI em `life/` | argparse no root CLI |

### 5.2 De `C:\Users\mathe\CLAUDE.md` (global pessoal)

- "Do what has been asked; nothing more, nothing less."
- "ALWAYS read a file before editing it."
- "NEVER commit secrets, credentials, or `.env` files."
- "NEVER add a `Co-Authored-By` trailer to commits."
- "Keep files under 500 lines; split when they grow."
- "Validate input at system boundaries (Zod, JSON Schema, or similar)."
- **OVERRIDES ativos nesta sessão:**
  - User autorizou criar arquivos em `life-ops/ikigai/data/` (override do "NEVER create files unless absolutely necessary")
  - User autorizou criar 1 README de persona (override do "NEVER proactively create documentation")
  - Path `life-ops/ikigai/data/` aprovado (override do "NEVER save to project root")

### 5.3 Data-first methodology (ADR-007)

- **Threshold: 5+ SONHOs logs manuais** antes de qualquer trabalho de código em `src/ikigai/`.
- **Única exceção ativa**: o 1-line Literal extension em `dream.py:17` (já pré-aprovado via Option Z, decisão R1).
- User verbatim: *"pois o codigo deve sempre emergir apartir dos dados!"*

### 5.4 Refactor Protocol (para vibe-ops e append-only)

1. **Stop** — não começar a editar
2. **Propose Action Plan** — listar arquivos, strings a preservar, migration path
3. **Wait for Approval Gate** — explícito user "go"
4. **Only then mutate** — verificar byte-for-byte

**NÃO se aplica** ao `dream.py:17` (add-only trivial, pré-aprovado).

### 5.5 Sessão pattern (working-tree only)

- **0 commits** nesta sessão.
- User controla quando commitar.
- Mudanças ficam em working-tree até user pedir.

---

## 6. Memory files (contexto carregado automaticamente em nova sessão)

| Memory | Path | Conteúdo |
|--------|------|----------|
| Data-first methodology | `data-first-methodology.md` | ADR-007, 5+ SONHO threshold |
| Algorithm Issues Registry | `algorithm-issues-registry.md` | 31 inconsistências; gates N01/A02/D02 |
| IKIGAi weight deferral | `ikigai-weight-mechanism-defer.md` | Option C, vector weights |
| Parallel execution trigger | `parallel-execution-trigger.md` | 5-10 agents in one msg when "ok go ahead" |

**Nota:** MEMORY.md index fica em `C:\Users\mathe\.claude\projects\C--Users-mathe-code-space-life-oss-life\memory\MEMORY.md` — atualizar quando novos memories surgirem.

---

## 7. Reinject command (cola isto na nova sessão)

> Continuar o plano `C:\Users\mathe\.claude\plans\logical-gliding-church.md`. Estamos em plan mode; R1/R2/R3 já decididos (Option Z / flat / draft). Handoff completo em `.omo/ikigai/meta/session-handoff-2026-07-03.md` — ler primeiro. Próximos passos: (1) ExitPlanMode com allowedPrompts para Bash+Write em `life-ops/ikigai/`, (2) edit `dream.py:17` Literal set adicionando 547, (3) criar 5 arquivos em `life-ops/ikigai/data/matheus/` (README + 1 DREAM + 1 OBJECTIVE + 1 PROJECT + 1 profile JSON), (4) YAML round-trip verify, (5) confirmar git working-tree, (6) **NÃO commitar**. Não resolver N01/A02/D02 nem mexer em código fora do Literal extension.

---

## 8. Conversation trace (verbatim user messages)

1. **Inicial:** *"vamos criar uma pasta de dataset com a minha persona direto em @life-ops\ikigai onde vamos codar o sistema depois que vai interagir com esses dados ja pensando em producao! pois vamos deixar .omo/ikigai/mock-datasets/ como um meta modelo onde vamos explorar estruturacao de templates, etc.."*

2. **Local:** *"just /data versionado e auditavel.. nao me importo em expor"*

3. **Socratic Q1 (data-first):** *"ainda nao vamos mexer em nada tecnicamente.. vamos loggar tambem essa questao em perpectiva & append os trade offs, vantagens de cada uma dessas opcoes na sessao dos backlogs de codigos que temos referente a esse aspecto do sistema.... vamos nos manter no data-first por enquanto... essa eh maior questao que preciso estruturar o quanto antes.. por enquanto esses detalhes algorimos nao faz tanta diferenca enquanto nao tivermos o nosso dataset pronto com todos os templates de operacao.... pois o codigo deve sempre emergir apartir dos dados!"*

4. **Socratic Q2 (nicho):** *"Data/Analytics / BI consulting, AI/LLM tooling / Developer tools, por enquanto nao tenho uma estrategia de nicho definida!... quero fazer um sistema generalista para operar em qualquer industria, como um grande pipeline de dados que me da municao suficiente para construir artefatos de software, como diferencial de arbitragem em ampla concorrecia, e ancoregem para negociar salarios e contratos... (precificacao por assimetria de informacao)"*

5. **Socratic Q3 (modalidade):** *"Salário mínimo X BRL/USD, 100% remoto (sem exceção), Time internacional ou BR-remoto-para-exterior, Stack tech alinhada (Python/Polars/...), pode ser hibrido ou presencial tambem aqui em salvador... foco maximo para remoto!"*

6. **Socratic Q4 (weekly budget + roles):** *"Variável (definir na Semana, não no SONHO)"*; salary floor: *"tanto faz para minha primeira vaga... nao da pra escolher muito nao"*

7. **Target roles (verbatim):** *"Data Engineer / Analytics Engineer, BI Analyst / Data Analyst, ML/AI Engineer (LLM tooling), Solutions/Analytics Consultant, dev fullstack, backend"*

8. **Weekly budget:** *"40+ h/semana (full-time-ish)"*

9. **Handoff request:** *"chegamos ao limite desse chat!.. por favor preciso de um resumo de handoff com: objetivo atual, decisões já tomadas, arquivos/trechos importantes, próximos passos."*

10. **Save summary request (atual):** *"vamos salvar um resumo completo! antes de limpar pra reinjetar esse resumo depois"*

---

## 9. TL;DR — 5 bullets

1. **Re-Read** o plan file na nova sessão (`C:\Users\mathe\.claude\plans\logical-gliding-church.md`) — tracking Edit-Only-In-Plan-Mode estará fresh.
2. **`ExitPlanMode`** com allowedPrompts para Bash+Write em `life-ops/ikigai/`.
3. **Edit 1 linha:** `dream.py:17` Literal set adicionando `547`.
4. **Criar 5 arquivos** em `life-ops/ikigai/data/matheus/` (README + DREAM + OBJECTIVE + PROJECT + profile JSON).
5. **Validar YAML round-trip** + `git status` — **NÃO commitar**.

**NÃO fazer:** ADR-008, resolver N01/A02/D02, criar templates SEMANA/DIA, mexer em ATIVIDADES/CÓDIGO layer, commitar, adicionar `Co-Authored-By`.

---

## 10. Files created this session

| Path | Action | Status |
|------|--------|--------|
| `C:\Users\mathe\.claude\plans\logical-gliding-church.md` | CREATED | ~385 linhas, plan mode only |
| `.omo/ikigai/meta/session-handoff-2026-07-03.md` | CREATED (este arquivo) | self-contained reinject |

**Modificações:** nenhuma ainda (plan mode). Pós-aprovação: 1 file edit (`dream.py:17`) + 5 file creates (`data/matheus/*`).

**Commits:** 0. Working-tree only.

---

*Handoff v1 · 2026-07-03 · IKIGAi Sys-01 · Cluster PLAN · Persona: Matheus Mendes · data-first phase, no code beyond Literal extension, scaffold plano completo, ~1h execução sequencial restante.*

*Reinjection checklist (verify antes de executar):*
- [ ] Plan file re-read
- [ ] `dream.py:17` current state confirmed (Literal set tem 6 valores atualmente?)
- [ ] `data/matheus/` directory não existe ainda
- [ ] `.omo/ikigai/meta/session-handoff-2026-07-03.md` accessible
- [ ] Memories re-loaded: data-first-methodology, ikigai-weight-defer, algorithm-registry, parallel-trigger