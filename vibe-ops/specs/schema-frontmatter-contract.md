# Schema: Contrato de YAML Frontmatter

**Versão:** 0.1.0
**Última Atualização:** 2026-05-03
**Referência:** `specs/schema-pydantic-models.md`, `doc/03-data-mesh-enrichment.md`

Este documento define o **contrato de formato** para os YAML Frontmatters usados em todos os arquivos Markdown do domínio de planejamento (`vibe-ops/planning/`, `strategics/`, `fin_ops/docs/`).

---

## 1. Regras Gerais de Frontmatter

### 1.1. Obrigatoriedade

| Regra | Descrição |
|:------|:----------|
| Todo arquivo `.md` no domínio Planning **DEVE** ter Frontmatter | Sem Frontmatter = arquivo ignorado pelo pipeline |
| O campo `entity_type` é **sempre obrigatório** | Determina qual Pydantic Model será usado na validação |
| O campo `id` é **sempre obrigatório** | Identificador único dentro do tipo de entidade |
| O campo `status` é **sempre obrigatório** | Determina se a entidade é processada (`active`) ou ignorada (`archived`) |

### 1.2. Convenções de Nomenclatura

| Campo | Formato | Exemplos |
|:------|:--------|:---------|
| `id` (Dream) | `S` + número inteiro | `S1`, `S2`, `S15` |
| `id` (Objective) | `O` + número inteiro | `O1`, `O2`, `O42` |
| `id` (Meta) | `M` + número inteiro | `M1`, `M2`, `M99` |
| `id` (Project) | `proj_` + snake_case | `proj_alfa_01`, `proj_auth_module` |
| `quarter` | `Q[1-4]_YYYY` | `Q3_2026`, `Q1_2027` |
| `wave` | `W[N]_Mmm_YYYY` | `W2_Jul_2026` |
| `tags` | Array de strings, snake_case | `["backend", "@vscode", "phase:learn"]` |

### 1.3. Campos Opcionais Universais

Estes campos podem aparecer em **qualquer** Frontmatter, independente do `entity_type`:

```yaml
# Metadados universais
created: "2026-07-15"        # Data de criação (ISO 8601)
updated: "2026-07-20"        # Última modificação (ISO 8601)
tags: ["tag1", "tag2"]       # Vocabulário controlado (ver doc/03)
notes: "Contexto adicional"  # Texto livre para anotações
```

---

## 2. Schemas por Tipo de Entidade

### 2.1. Dream (`entity_type: "dream"`)

```yaml
---
# ═══════════════════════════════════════════════════
# CAMPOS OBRIGATÓRIOS
# ═══════════════════════════════════════════════════
id: "S1"
title: "Fonte de Renda com Programação"
entity_type: "dream"
status: "active"                     # active | paused | completed | archived
created: "2026-01-15"

# ═══════════════════════════════════════════════════
# CAMPOS ESPECÍFICOS DO DREAM
# ═══════════════════════════════════════════════════
horizon: "annual"                    # annual | multi_year
ikigai_vectors:
  passion: 0.8                       # float 0.0 → 1.0
  skill: 0.9                        # float 0.0 → 1.0
  market: 0.7                       # float 0.0 → 1.0
  revenue: 0.6                      # float 0.0 → 1.0
review_cycle: "quarterly"           # daily | weekly | monthly | quarterly | annual

# ═══════════════════════════════════════════════════
# CAMPOS OPCIONAIS
# ═══════════════════════════════════════════════════
tags: ["renda", "programacao", "carreira"]
notes: ""
---
```

### 2.2. Objective (`entity_type: "objective"`)

```yaml
---
id: "O2"
title: "Conseguir Primeiro Freela de Backend"
entity_type: "objective"
status: "in_progress"
created: "2026-07-01"

# FK obrigatória
parent_dream: "S1"                   # FK → DreamEntity.id (VALIDADA)

# Específicos do Objective
quarter: "Q3_2026"
revenue_impact: "HIGH"               # CRITICAL | HIGH | MEDIUM | LOW | NONE
review_cycle: "monthly"

key_results:
  - kr_id: "KR1"
    description: "Completar 3 projetos de portfólio"
    target: 3
    current: 1
  - kr_id: "KR2"
    description: "Aplicar para 20 vagas/freelas"
    target: 20
    current: 5

tags: ["backend", "freela", "portfolio"]
---
```

### 2.3. Meta (`entity_type: "meta"`)

```yaml
---
id: "M3"
title: "Sprint: API REST com Autenticação JWT"
entity_type: "meta"
status: "active"
created: "2026-07-15"

# FK obrigatória
parent_objective: "O2"              # FK → ObjectiveEntity.id (VALIDADA)

# Específicos da Meta
wave: "W2_Jul_2026"
duration_days: 15                    # int 1 → 30
estimated_hours: 30                  # float > 0
priority: "P1"                      # P1 (urgente) | P2 | P3 | P4 (backlog)
review_cycle: "weekly"

tags: ["api", "jwt", "sprint"]
---
```

### 2.4. Project (`entity_type: "project"`)

```yaml
---
id: "proj_alfa_01"
title: "Módulo de Autenticação"
entity_type: "project"
status: "active"
created: "2026-07-16"

# FKs obrigatórias (cadeia completa)
parent_meta: "M3"                   # FK → MetaEntity.id
parent_objective: "O2"              # FK → ObjectiveEntity.id
parent_dream: "S1"                  # FK → DreamEntity.id

# Específicos do Project
revenue_impact: "HIGH"
estimated_size: "8h"                 # Formato livre: '4h', '2d', '1w'

# Campo computado (gerado pelo pipeline, NÃO editado manualmente):
# tw_project_key: "S1.O2.M3.proj_alfa_01"

tags: ["@backend", "@security"]
---
```

---

## 3. Anti-Patterns (O Que NÃO Fazer)

| Anti-Pattern | Exemplo Ruim | Correção |
|:------------|:-------------|:---------|
| Frontmatter sem `entity_type` | `id: "S1"` (sem tipo) | Adicionar `entity_type: "dream"` |
| FK para entidade inexistente | `parent_dream: "S99"` (S99 não existe) | Verificar registro de Dreams |
| Tags com espaços | `tags: ["deep work"]` | Usar snake_case: `tags: ["deep_work"]` |
| Datas em formato BR | `created: "15/07/2026"` | Usar ISO 8601: `created: "2026-07-15"` |
| `tw_project_key` manual | Escrever a chave no Frontmatter | Deixar o pipeline computar |
| IKIGAi vectors fora de range | `passion: 1.5` | Máximo é `1.0` |
| `id` duplicado entre entidades | Dois Projects com `id: "proj_alfa_01"` | IDs devem ser globalmente únicos |

---

## 4. Processo de Validação pelo Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ✅ FLUXO DE VALIDAÇÃO DE FRONTMATTER                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. PARSE                                                               │
│     python-frontmatter.load(filepath)                                   │
│     → Extrai YAML como dict + corpo Markdown                           │
│                                                                         │
│  2. ROTEAMENTO                                                          │
│     entity_type = data["entity_type"]                                   │
│     model_class = MODEL_MAP[entity_type]                                │
│     → Seleciona o Pydantic Model correto                               │
│                                                                         │
│  3. VALIDAÇÃO                                                           │
│     try:                                                                │
│         entity = model_class(**data)                                    │
│     except ValidationError as e:                                        │
│         → Log erro tipado (FK_NOT_FOUND, TYPE_ERROR, etc.)             │
│         → Abortar este arquivo, continuar com o próximo                 │
│                                                                         │
│  4. FK RESOLUTION                                                       │
│     if entity.parent_dream:                                             │
│         assert entity.parent_dream in dream_registry                    │
│     → Valida toda a cadeia hierárquica                                  │
│                                                                         │
│  5. ENRICHMENT                                                          │
│     entity.tw_project_key = compute_key(entity)                        │
│     entity.upstream_id = sha256(project_key + task_index)[:12]         │
│     → Adiciona campos computados                                       │
│                                                                         │
│  6. EMIT                                                                │
│     payload = TaskPayload.from_entity(entity)                          │
│     tasklib.inject(payload)                                            │
│     → Push para Taskwarrior                                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

> 💡 **NOTA:** Este schema é o **contrato de interface** entre o humano que escreve Markdown e o pipeline que processa dados. Qualquer alteração nos campos obrigatórios deve ser refletida nos Pydantic Models (`specs/schema-pydantic-models.md`) e documentada em `CHANGELOG.md`.
