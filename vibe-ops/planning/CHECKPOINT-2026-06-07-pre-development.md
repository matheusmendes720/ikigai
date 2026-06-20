# Checkpoint de Desenvolvimento — 2026-06-07

> **Status:** Checkpoint salvo. Desenvolvimento NÃO iniciado (por instrução do operador).
> **Escopo:** Consolidação do estado atual + plano de desenvolvimento + análise de conflito conceitual identificado.

---

## 1. Resumo do Estado Atual do Workspace

### 1.1. Métricas de Output (Sessão de Orquestração 2026-06-05/07)

| Categoria | Métrica | Valor |
|:----------|:--------|------:|
| **Docs de estratégia** | Cluster docs canônicos | 3 (PLAN, PROJ, STUDY) |
| | Master index | 1 (`ARCHITECTURE_INDEX.md`, 35K) |
| | Conceito | 2 (`CONCEPTUAL_MODEL.md`, `SYSTEMS_TOPOLOGY.md`) |
| **Docs de engenharia** | ADRs | 5 |
| | PRDs | 7 |
| | Cluster PLAN drilldowns (planning/) | 5 |
| | Cluster PLAN specs (specs/) | 3 |
| | IKIGAi planning docs | 5 |
| | Templates | 3 |
| **Diagramas** | PNGs renderizados | 6 |
| | Fontes Mermaid | 6 |
| **Infraestrutura** | Pre-commit | 0 (proposto) |
| | pyproject.toml raiz | 0 (proposto) |
| | Test suite consolidada | 0 (parcial) |

### 1.2. Estado por Sub-sistema (5 clusters)

| # | Sub-sistema | Spec | Code | Data | Docs |
|--:|:------------|:----:|:----:|:----:|:----:|
| 1 | **PLAN** (rotinas, blocos, rituais) | 🟡 | 🟡 | 🟡 | 🟢 |
| 2 | **PROJECT** (PMO↔TW) | 🟢 | 🟡 | 🟢 | 🟢 |
| 3 | **STUDIES** (PKM) | 🟢 | 🟡 | 🟢 | 🟢 |
| 4 | **IKIGAi** (meta-brain) | 🟢 | 🔴 (GAP scorer) | 🔴 | 🟢 |
| 5 | **HABIT/CYBER** (Q_HE, regime) | 🟢 | 🟢 | 🟢 | 🟢 |

### 1.3. Gaps de Código Identificados

| # | Arquivo | Tamanho | Gap |
|--:|:--------|--------:|:----|
| 1 | `vibe-ops/src/pipeline/ikigai_scorer.py` | 1.7K | **Diverge do spec** — 4 campos `{study, dev, health, global}` ao invés de 5 vetores `{passion, skill, market, revenue, course}` |
| 2 | `vibe-ops/src/models/ikigai_entities.py` | 362B | **Subdimensionado** — 4 floats, deveria ter IKIGAiProfile + 5 vetores + SkillNode + OpportunitySignal |
| 3 | `vibe-ops/src/__init__.py` | 0B | Vazio |
| 4 | `vibe-ops/CHANGELOG.md` | 0B | Histórico perdido |
| 5 | **8 STUBS (0 bytes)** | 0B cada | `embeddings/config.py`, `integration/obsidian_parser.py`, `parsers/code_parser.py`, `pipeline/{code_review_sync,daily_consolidator,study_manager}.py`, `storage/{sqlite_store,vector_store}.py` |

### 1.4. Infraestrutura Ausente

| # | Item | Impacto |
|--:|:-----|:--------|
| 1 | Root `__init__.py` | Quebra `python -m life.cli` |
| 2 | Imports mistos (`life.config` × `life.cli.config`) | Transicional |
| 3 | Sem `pyproject.toml` na raiz | Deps não pinadas |
| 4 | Sem `requirements.txt` na raiz | `pip install -r` impossível |
| 5 | `pytest.ini` ausente | Test discovery global quebrado |
| 6 | Sem `conftest.py` global | Sem fixtures compartilhadas |
| 7 | Sem pre-commit | Validação manual |

---

## 2. Plano de Desenvolvimento (Proposto Inicialmente)

### 2.1. Definição de "110% Funcional" (Decidido)

Testes + idempotência + docs (DoD checklist):

- [ ] Pydantic models: 100% com validators + examples + type hints
- [ ] Storage: migrations aplicadas + CRUD completo
- [ ] CLI: 100% dos comandos com `--json`
- [ ] Pipelines: idempotentes (re-run = mesmo output_hash)
- [ ] Tests: unit >90% coverage, integration >80%, E2E happy path
- [ ] Mocks: in-memory + tmp_path (zero dependências externas em testes)
- [ ] Logs estruturados (json mode opcional)
- [ ] Error handling: zero `except:` genérico
- [ ] Docs: cluster doc sincronizado com código
- [ ] `verify_cluster_X.py`: smoke test standalone

### 2.2. Estratégia de Mocking (Decidida)

In-memory + tmp_path:
- `in_memory_db` fixture: SQLite `:memory:` por teste
- `tmp_vault` fixture: `tmp_path` com `.md` fixtures
- `mock_chroma` fixture: substitui ChromaDB por sqlite-vec
- `mock_tw` fixture: usa test_taskrc + tmp_path

### 2.3. CI/Pre-commit (Decidido)

Local-only com pre-commit:
- Hooks: ruff (lint) + pytest (test) + verify_mesh (sanity)
- Sem GitHub Actions (sem CI remoto)
- Documentado em `AGENTS.md`

### 2.4. Roadmap Original (PROPOSTO INICIAL — ver §4 para revisão)

```
Sprint 0 (1 sem): Fase 0 — Fundação
   - pyproject.toml, requirements.txt, pytest.ini, conftest.py
   - life/__init__.py, fix imports, .pre-commit-config.yaml

Sprint 1 (1 sem): Cluster 5 — HABIT/CYBER  (template + baseline)
Sprint 2 (1 sem): Cluster 4 — IKIGAi       (corrige GAP scorer)
Sprint 3 (1 sem): Cluster 3 — STUDIES      (RAG + knowledge tree)
Sprint 4 (1 sem): Cluster 2 — PROJECT      (TW sync + roadmap)
Sprint 5 (1 sem): Cluster 1 — PLAN         (journal log + routines)
Sprint 6 (1 sem): Cross-cluster C1-C6 contracts
Sprint 7 (1 sem): verify_all_clusters.py + DoD final
```

**Total: 8 sprints (≈ 8 semanas).**

---

## 3. Conflito Conceitual Identificado (Equivoco do Agente)

### 3.1. O Equivoco

O roadmap original propôs **Cluster 5 (HABIT/CYBER) como Sprint 1** e **Cluster 1 (PLAN) como Sprint 5**, tratando-os como **dois sub-sistemas paralelos e independentes** que poderiam ser desenvolvidos em isolamento, com base apenas no critério de "maturidade de código" (5 mais maduro → 1 menos maduro).

**Esse raciocínio estava errado** porque ambos os clusters são **derivados do mesmo documento-fonte** (`vibe-ops/base/Produtividade Algorítmica Visual.md`, 815K), e ocupam **camadas de engenharia diferentes**.

### 3.2. Análise do PAV (Fonte Unificada)

O PAV é o **contrato compartilhado** que define TANTO as constantes/variáveis aritméticas QUANTO as rotinas/blocos textuais:

| Componente do PAV | Linha no PAV | Tipo | Cluster que extrai |
|:------------------|:-------------|:-----|:-------------------|
| Constantes (`HORARIO_ACORDAR_MIN`, `POMODORO_WORK_MIN`, `SONO_OPCOES_HORAS`, `LUZ_AZUL_CORTE`) | §1 (40-78) | Numérico | **Cluster 5 (HABIT)** — telemetria |
| Variáveis (`horaAcordou`, `energiaNivel`, `focoNivel`, `pomodorosCompletos`) | §2 (79-125) | Numérico | **Cluster 5 (HABIT)** — métricas |
| Rotinas/Blocos por Período (manhã/tarde/noite) | §3 (130-160) | Textual | **Cluster 1 (PLAN)** — journal |
| Árvore de Decisão (cálculo dormir/acordar) | §4 (164-263) | Algorítmico | **Cluster 1 (PLAN)** — lógica |
| State Machine Pomodoro (IDLE→WORK→BREAK→LONG_BREAK) | §9 (661-695) | State machine | **Cluster 1 (PLAN)** — blocos |
| Cenários diários (perfect/deviated/hardcore) | §8 (484-612) | Híbrido | **Ambos** — PLAN descreve, HABIT computa regime |
| Error handling (10 error codes) | §6 (328-429) | Híbrido | **Ambos** — PLAN reporta, HABIT computa |
| Dashboard de métricas | §10 (700-739) | Híbrido | **Ambos** — PLAN textual + HABIT numérico |

### 3.3. Divisão Funcional Real

| Aspecto | Cluster 1 (PLAN) | Cluster 5 (HABIT/CYBER) |
|:--------|:-----------------|:-------------------------|
| **Tipo de dado primário** | **Strings** (journal entries, rotinas, ajustes finos) | **Floats/ints** (H(t), E(t), Q_HE, streak) |
| **Origem no PAV** | §3, §4, §9 (rotinas, decision tree, pomodoro SM) | §1, §2, §8 numérico (constantes, variáveis, radar) |
| **Camada de aplicação** | **Input/Capture Layer** (human → sistema) | **Arithmetic/Compute Layer** (sistema → decisão) |
| **CLI exemplo** | `plan journal log "Dormi 21h, acordei 4h, S1=4 rounds"` | `habit qhe --window=7d` |
| **Output exemplo** | Weekly report (markdown append com texto) | Regime (PUSH/MAINTAIN/REDUCE/RECOVER) + Q_HE score |
| **Schema canônico** | `TimeBlock`, `Routine`, `Ritual`, `JournalEntry` | `Habit`, `EnergyReading`, `HabitStreak`, `PolicyDecision` |
| **Dependência** | Independente (pode capturar journal sem HABIT) | Depende de PLAN para inputs estruturados |
| **Fonte primária** | `PAV §3 + §4 + §9` | `PAV §1 + §2 + §6 numérico` |

### 3.4. Fluxo Real (Que Eu Ignorei)

```
                         ┌─────────────────────────────────┐
                         │  PAV (815K) — FONTE UNIFICADA  │
                         │  §1 const  §2 var  §3 rotinas   │
                         │  §4 decision  §9 pomodoro SM    │
                         │  §8 cenários  §6 errors  §10 KPI│
                         └────────┬───────────────┬────────┘
                                  │               │
                  extrai numérico │               │ extrai textual
                                  ▼               ▼
                         ┌─────────────────┐  ┌─────────────────┐
                         │ Cluster 5       │  │ Cluster 1       │
                         │ (HABIT)         │  │ (PLAN)          │
                         │                 │  │                 │
                         │ H(t), E(t)      │  │ JournalEntry    │
                         │ Q_HE formula    │  │ TimeBlock       │
                         │ Regime FSM      │  │ Routine, Ritual │
                         │ PolicyDecision  │  │                 │
                         └────────┬────────┘  └────────┬────────┘
                                  │                    │
                                  │  (HABIT feedback)  │  (PLAN inputs)
                                  │◄───────────────────│
                                  │                    │
                                  ▼                    ▼
                         ┌─────────────────────────────────┐
                         │   WEEKLY REPORT (combinado)     │
                         │   - Textual (PLAN)              │
                         │   - Numérico (HABIT)            │
                         │   - Recomendações (regime)      │
                         └─────────────────────────────────┘
```

### 3.5. Implicações Para o Roadmap

1. **Não dá para desenvolver 5 → 1 em isolamento** — eles compartilham o PAV como contrato
2. **Sprint 0 (Fundação) precisa incluir:** extrair as entidades canônicas do PAV para um **schema compartilhado** `vibe-ops/src/models/pav_entities.py` (ou nome similar)
3. **Ordem revisada sugerida:** Cluster 5 e Cluster 1 precisam ser **desenhados em conjunto** (sprint compartilhado) ou sequencial com **schema PAV intermediário**
4. **A definição de "110% funcional" precisa ser por par:** PLAN+HABIT formam o **domínio operacional completo** (captura + aritmética)
5. **Cluster 4 (IKIGAi)** depende diretamente de PLAN+HABIT (consome Q_HE + regime + journal features) — então vem DEPOIS

---

## 4. Plano Revisado (Após Análise do Conflito)

### 4.1. Pré-Sprint 0 — Schema PAV Compartilhado (NOVO)

**Objetivo:** Extrair do PAV as entidades canônicas (constantes, variáveis, rotinas) para um módulo Python único que serve tanto Cluster 1 quanto Cluster 5.

**Output:** `vibe-ops/src/models/pav_entities.py` (~300-500 linhas)

**Conteúdo:**
```python
# Constantes (do PAV §1)
class PAVConstants(BaseModel):
    HORARIO_ACORDAR_MIN: int = 3
    HORARIO_ACORDAR_MAX: int = 5
    HORARIO_DORMIR_MIN: int = 18
    HORARIO_DORMIR_MAX: int = 21
    POMODORO_WORK_MIN: int = 50
    POMODORO_BREAK_MIN: int = 10
    POMODORO_ROUNDS_MIN: int = 3
    POMODORO_ROUNDS_MAX: int = 4
    SONO_OPCOES_HORAS: list[int] = [9, 8, 7, 4]
    LUZ_AZUL_CORTE: int = 18
    # + outras 12 constantes (total 22)

# Variáveis (do PAV §2)
class PAVVariables(BaseModel):
    dataAtual: date
    horaAcordou: int
    horaDormiu: int
    horasSonoReal: float  # calculado
    horasSonoPlanejado: int  # 9, 8, 7 ou 4
    qualidadeSono: Literal['excelente', 'boa', 'regular', 'ruim']
    energiaNivel: int  # 1-10
    focoNivel: int  # 1-10
    pomodorosCompletos: int  # 0-12
    interrupcoesCount: int
    tempoTelaTotal: int  # minutos
    rotinasCompletas: list[str]
    rituaisTransicao: list[bool]
    desviosRotina: list[str]
    ajusteFinos: list[AjusteFino]

# Rotinas (do PAV §3)
class Routine(BaseModel):
    periodo: Literal['MANHA', 'TARDE', 'NOITE']
    horario_inicio: time
    horario_fim: time
    rotina_obrigatoria: str
    ritual_transicao: str
    status: Literal['pending', 'in_progress', 'completed', 'skipped']

# Blocos de tempo (do PAV §9)
class TimeBlock(BaseModel):
    block_id: str
    type: Literal['POMODORO_WORK', 'POMODORO_BREAK', 'LONG_BREAK', 'RITUAL']
    start: datetime
    end: datetime
    round: int  # 1-4
    status: Literal['IDLE', 'WORK', 'BREAK', 'LONG_BREAK', 'PAUSED', 'SKIPPED', 'COMPLETE']

# State Machine Pomodoro (do PAV §9 stateDiagram-v2)
class PomodoroState(str, Enum):
    IDLE = 'IDLE'
    WORK = 'WORK'
    BREAK = 'BREAK'
    LONG_BREAK = 'LONG_BREAK'
    PAUSED = 'PAUSED'
    SKIPPED = 'SKIPPED'
    COMPLETE = 'COMPLETE'

# 10 Error Codes (do PAV §6)
class PAVErrorCode(str, Enum):
    ERR_TIME_001 = 'hora_acordou < 3'
    ERR_TIME_002 = 'hora_acordou > 12'
    ERR_TIME_003 = 'hora_acordou > 5'
    ERR_SLEEP_001 = 'horas_sono < 4'
    ERR_SLEEP_002 = 'horas_sono > 12'
    ERR_MEAL_001 = 'refeicao_apos_18h'
    ERR_LIGHT_001 = 'luz_azul_apos_18h'
    ERR_POMO_001 = 'rounds < 3'
    ERR_POMO_002 = 'break < 5min'
    ERR_ROUTINE_001 = 'rotina_incompleta'
```

**Testes do Schema PAV:**
- `tests/unit/test_pav_entities.py` — valida cada constante/variável/routine contra valores do PAV
- `tests/unit/test_pav_state_machine.py` — valida transições Pomodoro
- `tests/unit/test_pav_errors.py` — valida 10 error codes

### 4.2. Roadmap Revisado (Proposta)

```
Sprint 0 (1 sem): Fundação + Schema PAV
   - pyproject.toml, requirements.txt, pytest.ini, conftest.py
   - life/__init__.py, fix imports, .pre-commit-config.yaml
   - NOVO: vibe-ops/src/models/pav_entities.py (300-500 linhas)
   - NOVO: tests/unit/test_pav_*.py (3 arquivos)

Sprint 1-2 (2 sem): Cluster 5 (HABIT/CYBER) + Cluster 1 (PLAN) — PARALELO
   - Cluster 5: H(t), E(t), Q_HE, regime FSM, PolicyEngine
   - Cluster 1: JournalEntry, TimeBlock, Routine, weekly report generator
   - Schema PAV é o contrato compartilhado
   - Cross-tests: PLAN journal entries alimentam HABIT telemetry

Sprint 3 (1 sem): Cluster 4 (IKIGAi) — corrigir GAP
   - Reescrever ikigai_scorer.py (5 vetores canônicos)
   - Expandir ikigai_entities.py (200+ linhas)
   - Depende de PLAN+HABIT rodando

Sprint 4 (1 sem): Cluster 3 (STUDIES)
   - RAG indexer + knowledge tree
   - Skill/Topic/Material/Session

Sprint 5 (1 sem): Cluster 2 (PROJECT)
   - TW sync + roadmap
   - SoftwareProject/Epic/Sprint/Task

Sprint 6 (1 sem): Cross-cluster C1-C6 contracts
   - Implementar os 6 contratos cross-domain
   - E2E test suite

Sprint 7 (1 sem): verify_all_clusters.py + DoD final
   - Métricas automatizadas
   - DoD checklist 110% para cada cluster
```

**Total: 7 sprints (≈ 7-8 semanas).**

**Mudança-chave vs roadmap original:** Sprint 1-2 agora é **paralelo (PLAN + HABIT)** com schema PAV como contrato compartilhado, ao invés de sequencial.

### 4.3. Definition of Done Revisada (Por Par)

**PAIR: PLAN (1) + HABIT (5) = Domínio Operacional**

- [ ] Schema PAV completo (`pav_entities.py`) com 22 constantes + 14 variáveis + 3 rotinas + 1 state machine + 10 error codes
- [ ] Cluster 1 (PLAN): CLI `plan journal log`, `plan journal week`, weekly report generator
- [ ] Cluster 5 (HABIT): CLI `habit qhe`, `habit regime`, PolicyEngine 4-state
- [ ] Cross-test: PLAN journal entry → HABIT telemetry (H aumenta se rotina completed)
- [ ] Cross-test: HABIT regime REDUCE → PLAN weekly report recomenda "reduzir S3 para 2 rounds"
- [ ] 100% CLI com `--json`
- [ ] Idempotência comprovada (re-run pipeline = mesmo output_hash)
- [ ] 0 `except:` genérico
- [ ] Mocks: in-memory + tmp_path
- [ ] Latência CRUD < 100ms, pipeline < 1s

---

## 5. Próximos Passos (Após Aprovação do Plano Revisado)

> **Status atual:** Aguardando aprovação do operador sobre o roadmap revisado (§4).

**Quando aprovado, executar nesta ordem:**

1. **Pré-Sprint 0:**
   - Criar `vibe-ops/src/models/pav_entities.py` (schema PAV compartilhado)
   - Criar `tests/unit/test_pav_*.py` (3 arquivos de teste)
   - Rodar sanity check

2. **Sprint 0 (Fundação):**
   - Criar `pyproject.toml` + `requirements.txt` (raiz)
   - Criar `pytest.ini` + `conftest.py` (raiz)
   - Criar `life/__init__.py` (resolve import)
   - Criar `.pre-commit-config.yaml`
   - Fix imports (`life.cli.config` canônico, `life.config` shim)

3. **Sprint 1-2 (PLAN + HABIT paralelo):**
   - Cluster 1: Pydantic + Storage + CLI + Pipelines
   - Cluster 5: Pydantic + Storage + CLI + Pipelines
   - Cross-tests PAIR

4. **Sprint 3-7:** seguir roadmap §4.2

---

## 6. Documentos de Referência

### 6.1. Fonte Unificada (Conflito)

- `vibe-ops/base/Produtividade Algorítmica Visual.md` (815K) — PAV, contém TANTO constantes/variáveis aritméticas QUANTO rotinas/blocos textuais

### 6.2. Cluster Docs Canônicos (Raiz)

- `CLUSTER_PLAN.md` (88K) — Cluster 1
- `CLUSTER_PROJ.md` (59K) — Cluster 2
- `CLUSTER_STUDY.md` (46K) — Cluster 3
- `CONCEPTUAL_MODEL.md` (25K) — T→B→S framework
- `SYSTEMS_TOPOLOGY.md` (58K) — M1-M8 middlewares
- `ARCHITECTURE_INDEX.md` (35K) — Master index

### 6.3. Engenharia de Código (AI-Native)

- `vibe-ops/architecture/ADR-001-data-flow-topology.md` (26K) — Topologia multi-cluster
- `vibe-ops/architecture/ADR-002-mesh-contracts-state-machines.md` (9.3K) — Contratos + FSMs
- `vibe-ops/architecture/ADR-003-ikigai-as-meta-brain.md` (10K) — IKIGAi meta-brain
- `vibe-ops/architecture/ADR-004-hybrid-rag-strategy.md` (7.8K) — RAG híbrido
- `vibe-ops/architecture/ADR-005-data-mesh-topology.md` (9.7K) — Data-mesh
- `vibe-ops/planning/PRD-*.md` (7 PRDs) + `CLUSTER_PLAN_*.md` (5 drilldowns)
- `vibe-ops/specs/schema-pydantic-models-v2.md` (36K) + `schema-planner-extension.md` (89K)
- `vibe-ops/specs/spec-cluster-plan-*.md` (3 specs)

### 6.4. IKIGAi Planning (Meta-Cérebro)

- `life-ops/planner/ikigai_planning/README.md` (3.4K)
- `life-ops/planner/ikigai_planning/ikigai_4_vectors.md` (12K)
- `life-ops/planner/ikigai_planning/ikigai_north_star_metrics.md` (8.1K) — 22 constantes
- `life-ops/planner/ikigai_planning/ikigai_propagation.md` (9.0K)
- `life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md` (13K) — 6 algoritmos

### 6.5. Estratégia (PT-BR)

- `strategics/00-ÍNDICE-PROGRESSIVO.md` (23K) — Índice mestre
- `strategics/Planejamento (Estratégico e Tático).md` (24K) — Wave/Cycle/Phase
- `strategics/Modelagem Operacional.md` (13K) — 4 regimes, histerese
- `docs/ÍNDICE PROGRESSIVO.md` (18K) — Entrada única

### 6.6. Data-Mesh Conceitual

- `vibe-ops/doc/01-data-mesh-strategy.md` — Estratégia
- `vibe-ops/doc/01.5-data-contracts-and-pipelines.md` (29K) — Master contratos
- `vibe-ops/doc/03-data-mesh-enrichment.md` (27K) — Enrichment

---

## 7. Resumo Executivo (Para Aprovação)

### 7.1. O Que Foi Feito

- ✅ 3 cluster docs canônicos (PLAN, PROJ, STUDY) + 2 framework docs (CONCEPTUAL_MODEL, SYSTEMS_TOPOLOGY) + 1 master index
- ✅ 5 ADRs (topologia, contratos, IKIGAi meta-brain, RAG, data-mesh)
- ✅ 7 PRDs + 5 cluster PLAN drilldowns + 3 cluster PLAN specs
- ✅ 5 IKIGAi planning docs (cérebro do sistema)
- ✅ 6 diagramas PNG renderizados
- ✅ README global consolidado
- ✅ Cluster PLAN roadmap Q3 2026 (12 sprints)
- ✅ 10+ conflitos identificados e documentados em `ARCHITECTURE_INDEX.md §8`

### 7.2. O Que Está em Aberto (Gaps)

- 🔴 `ikigai_scorer.py` diverge do spec (5 vetores)
- 🔴 8 STUBS (0 bytes) em vibe-ops/src
- 🔴 Infraestrutura ausente (pyproject, pytest.ini, conftest, pre-commit)
- 🟡 3 cluster sub-sistemas com code gap (PLAN, PROJECT, STUDIES)

### 7.3. O Que Precisa Ser Decidido (AGORA)

| # | Decisão | Recomendação |
|--:|:--------|:-------------|
| 1 | Aprovar o **schema PAV compartilhado** como pré-Sprint 0? | **SIM** — destrava paralelização PLAN+HABIT |
| 2 | Ordem revisada (Sprint 1-2 paralelo, depois 4→3→2) | **SIM** — depende do schema PAV |
| 3 | Definition of Done por **par** (PLAN+HABIT) ao invés de individual | **SIM** — captura dependência real |
| 4 | Manter pre-commit local-only (sem CI) | **SIM** (já decidido) |
| 5 | Mocks in-memory + tmp_path | **SIM** (já decidido) |

### 7.4. Próximo Passo Imediato

**Aguardar aprovação do operador** sobre o plano revisado (§4).

Após aprovação, começar pelo **Pré-Sprint 0 (Schema PAV)**:
1. Criar `vibe-ops/src/models/pav_entities.py` (extrair do PAV linhas 40-739)
2. Criar 3 testes unitários (`test_pav_entities.py`, `test_pav_state_machine.py`, `test_pav_errors.py`)
3. Sanity check (rodar pytest + verificar coverage)

**Estimativa Pré-Sprint 0:** 1-2 dias.

---

*Checkpoint salvo em 2026-06-07.*
*Desenvolvimento NÃO iniciado (instrução do operador).*
*Aguardando aprovação do plano revisado (§4) antes de prosseguir.*
