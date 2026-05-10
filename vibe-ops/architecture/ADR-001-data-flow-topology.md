# ADR-001: Topologia de Fluxo de Dados do Vibe-Ops Data-Mesh

**Status:** Aceita
**Data:** 2026-05-03
**Autores:** Matheus (Arquiteto de Produtividade) + AI Agent
**Contexto:** `life/vibe-ops/`

---

## 1. Contexto do Problema

O workspace `produtividade` opera com **múltiplos sistemas desacoplados** que precisam trocar dados para gerar insights de produtividade:

| Sistema | Tipo | Dado Principal | Formato Nativo |
|:--------|:-----|:---------------|:---------------|
| Markdown/Obsidian | Planejamento estratégico | Sonhos, Objetivos, Metas, Tarefas | YAML Frontmatter + Markdown |
| Taskwarrior | Execução operacional | Tasks, Projetos, Status, Prioridade | JSON (`.task` binary) |
| Timewarrior | Rastreamento de tempo | Intervalos de início/fim por tag | JSON/Text (`.timew`) |
| GnuCash/fin_ops | Contabilidade e ROI | Receitas, Despesas, Valoração | SQLite / CSV |
| IKIGAi Model | Framework de decisão | Vetores de alinhamento estratégico | Markdown + Equações |
| Day Logger (legado) | Input diário de hábitos | Scores binários + horas | CSV/pandas |

O problema central é: **como conectar esses sistemas de forma que o dado flua de ponta a ponta sem duplicação, sem perda de contexto, e sem exigir input manual complexo do operador humano?**

---

## 2. Decisão

Adotar uma arquitetura **Data-Mesh Desacoplada** com um **Middleware Python centralizado** que atua como "barramento de integração" entre todos os domínios.

### 2.1. Princípios Arquiteturais Eleitos

| Princípio | Justificativa |
|:----------|:-------------|
| **Fully Local** | Zero dependência de cloud. Todos os dados residem no filesystem local. Soberania total. |
| **Append-Only** | Documentos de planejamento nunca são sobrescritos — apenas expandidos. Garante rastreabilidade. |
| **Single Source of Truth (por domínio)** | Cada sistema "manda" no seu domínio de dados. Não há duplicação autoritativa. |
| **Schema-First** | Todo contrato de dados é definido ANTES da implementação. Pydantic valida antes de injetar. |
| **Human-in-the-Loop para Metadados** | O humano escreve Markdown. O pipeline extrai e enriquece. O humano aprova triagens. |
| **Idempotência** | Re-executar o pipeline não cria duplicatas. `upstream_id` como chave de idempotência. |

### 2.2. Topologia Final

```
                    ┌────────────────────────────────────┐
                    │        PLANNING DOMAIN             │
                    │  (Markdown + YAML Frontmatter)      │
                    │  Owner: Humano                      │
                    │  SoT: Metadados, Nomenclaturas      │
                    └──────────┬─────────────────────────┘
                               │ YAML Parse
                               ▼
                    ┌────────────────────────────────────┐
                    │        MIDDLEWARE (Python)          │
                    │  Pydantic Models (Validation)       │
                    │  tasklib (TW Interface)             │
                    │  python-frontmatter (YAML Parse)    │
                    │  SQLite/DuckDB (Analytics Store)    │
                    └────┬──────────┬──────────┬─────────┘
                         │          │          │
              ┌──────────▼──┐  ┌───▼────┐  ┌──▼──────────┐
              │ TASKWARRIOR │  │TIMEW   │  │ ANALYTICS   │
              │ (.task DB)  │  │(.timew)│  │ (SQLite)    │
              │ SoT: Status │  │SoT:    │  │ Snapshots   │
              │ & Prioridade│  │Tempo   │  │ Históricos  │
              └─────────────┘  └────────┘  └──────┬──────┘
                                                   │
                                            ┌──────▼──────┐
                                            │ BI/DASHBOARD│
                                            │ Streamlit   │
                                            │ (Read-Only) │
                                            └─────────────┘
```

---

## 3. Alternativas Consideradas

### 3.1. Alternativa A: Taskwarrior como Hub Central (Rejeitada)

**Descrição:** Colocar toda a inteligência dentro do TW via UDAs (User Defined Attributes), hooks, e configurações avançadas.

**Motivos de Rejeição:**
- UDAs têm limites de tipo (string, numeric, date, duration) — sem suporte a arrays ou objetos aninhados
- Hooks em shell/Python executam a cada `task add/modify`, criando overhead em operações simples
- Toda a lógica de validação estaria acoplada ao TW — impossível testar isoladamente
- Migração futura para outro task manager seria catastrófica

### 3.2. Alternativa B: Obsidian Dataview como Motor de Consulta (Parcialmente Aceita)

**Descrição:** Usar o plugin Dataview do Obsidian para fazer queries diretamente no YAML Frontmatter, sem pipeline Python.

**Veredito:** Aceita como **camada de visualização leve** para o domínio Planning, mas rejeitada como motor de pipeline:
- Dataview é read-only — não pode injetar dados no TW
- Não suporta JOINs entre TW e Markdown
- Performance degrada com vaults grandes (>1000 notas)
- Útil para: dashboards locais do Obsidian, revisões semanais rápidas

### 3.3. Alternativa C: PostgreSQL como Data Warehouse (Rejeitada)

**Motivos de Rejeição:**
- Overhead de manutenção para um sistema single-user
- Requer daemon rodando permanentemente
- SQLite oferece 95% das funcionalidades sem nenhum processo servidor
- DuckDB oferece OLAP nativo para analytics sem sair do filesystem

---

## 4. Consequências

### 4.1. Positivas
- **Flexibilidade:** Cada domínio evolui independentemente sem quebrar os outros
- **Testabilidade:** Pipeline Python pode ter testes unitários com dados sintéticos
- **Auditoria:** SQLite mantém snapshots históricos imutáveis
- **Baixo custo:** Zero infra cloud, zero licenças, zero dependências externas

### 4.2. Negativas / Riscos Aceitos
- **Complexidade inicial:** Precisa codificar o middleware antes de ter qualquer benefício
- **Manutenção do parser:** Mudanças no formato do Frontmatter exigem update no Pydantic
- **Single point of failure:** Se o pipeline Python quebrar, os dados ficam dessincronizados
- **Curva de aprendizado:** Operador precisa entender a topologia para debugar problemas

### 4.3. Mitigações
- Fase A (parser + schemas) pode entregar valor em 2 semanas
- Pydantic gera documentação automática dos schemas
- Pipeline é idempotente — re-execução corrige dessincronias
- `triagem.md` captura o que o pipeline não consegue processar

---

## 5. Referências

| Documento | Caminho | Relevância |
|:----------|:--------|:-----------|
| Data Contracts & Pipelines | `doc/01.5-data-contracts-and-pipelines.md` | Contrato Master do pipeline |
| Data-Mesh Enrichment | `doc/03-data-mesh-enrichment.md` | Fluxos de enriquecimento |
| IKIGAi Model | `base/IKIGAi.md` | Função objetivo e setpoints |
| PAV | `base/Produtividade Algorítmica Visual.md` | Constantes e variáveis do sistema |
| SPEC | `SPEC.md` | Regras operacionais do agente |
| Frontmatter Contract | `specs/schema-frontmatter-contract.md` | Schemas YAML |
| Pydantic Models | `specs/schema-pydantic-models.md` | Modelos de validação |
