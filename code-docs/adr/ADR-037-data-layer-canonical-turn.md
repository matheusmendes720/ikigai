# ADR-037 — Virada Canônica: camada de dados primeiro

**Status:** Accepted
**Date:** 2026-11-01
**Owner:** matheus
**Supersedes:** framing de artefato-visual em `docs/vanilla-pivot.html` §7–§9 · convenção "Fully local / zero cloud deps" em `docs/README.md` · `master-branch-carro-chefe-2026-08-28` (deep-agent como carro-chefe)
**Relacionado:** [ADR-012](ADR-012-fork-connection-architecture.md) (vault_write sole writer) · [ADR-013](ADR-013-canonical-scope-discipline.md) (planner-only) · [ADR-014](ADR-014-ueid-canonical-format.md) (UEID 4 partes) · [ADR-033](ADR-033-ueid-single-source-mandate.md) · [ADR-036](ADR-036-paperclip-four-nested-loops.md) · [ADR-007](ADR-007-data-first-methodology.md)

---

## §0 — Resumo em uma linha

> **A virada:** para de construir máquina (harness, grafo, gateway MCP, UIs) e constrói **a camada de dados** — um único banco Postgres serverless que hospeda o vault versionado, indexado, servindo vector + graph + embeddings, com tipagem forte, e exposto por camadas de serviço e transporte a múltiplos clientes — sobre um harness **já pronto** (pi), não um novo.

## §1 — Contexto (o que o Vanilla Pivot provou)

O relatório [`docs/vanilla-pivot.html`](../../docs/vanilla-pivot.html) (2026-10-30) establece, com evidência do próprio repositório:

| Fato medido | Fonte |
|---|---|
| 79.320 LOC / 555 arquivos para ~1 usuário; harness = **49×** o contrato que ele serve | `docs/vanilla-pivot.html` §1 |
| **39%** das 123 células de capacidade verdes | `specs/2026-09-04-capability-status.md` §5 |
| **7 semanas de silêncio no vault** (último registro 2026-09-07) | vault `04-relatórios-diários/` |
| **Duas árvores de vault** — todo caminho automatizado lê a árvore vazia | `cadence.py:78-93` vs `vault/ikigai/closing-2026/` |
| 10 dos 16 nós do LangGraph são prompts com roupa de Python | `src/ikigai/src/agents/v2/nodes/` |
| 22 tools MCP, **9 apontando para tools inexistentes** | `mcp_bridge.py:88-130` vs `server.py` |
| **0 linhas** integrando `life` e `fin_ops` | §7 |

O veredito do pivot: *"o sistema não tem um problema de escala, tem um problema de **ordem**: a infraestrutura foi construída antes do conteúdo, e o conteúdo nunca chegou."*

E o SPEC-05 mapeou o corte (~15k LOC). **Mas o pivot parou no papel**: 0 tasks executadas, 0 deliverables existindo, `converge.js` nunca instalado, vault ainda só com placeholders.

## §2 — O que muda nesta virada

O Vanilla Pivot resolve a **ordem** (cortar o harness, criar o input port). Esta ADR resolve o **alvo**: o input port não é mais uma timeline local — é **a camada de dados do vault, hospedada na cloud, versionada, consultável e compartilhada**.

Três movos concretos:

1. **Abandonar o foco em operar TUI.** A TUI é *uma* das superfícies de cliente previstas (PC). Ela entra em **standby**. O cliente em foco passa a ser o **Telegram** — mas explicitamente **depois** de infra, arquitetura e engenharia de dados. Nenhum produto novo é especificado antes de a base de dados existir.
2. **Concentrar força total na camada de dados.** Primeiro: persistência do vault na cloud (update, edição, inserção, versionamento), e **busca rápida por índices estruturados**, servindo **vector, graph e embeddings** a partir do mesmo store.
3. **Reusar um harness pronto.** O fluxo normal de requisição do **pi agent** é o alvo. Construir outro harness multiplicaria a complexidade de manutenção — que é exatamente o que o diagnóstico reprova.

## §3 — Decisão

### D1 — Ordem de esforço (não negociável)

```
1. CAMADA DE DADOS          ← onde toda a força vai agora
   ├─ DOM unificado (schema + tipagem forte)
   ├─ Store cloud (Postgres serverless) — versionamento, índices, vector, graph
   └─ Sync vault markdown ↔ store
2. CAMADAS DE SERVIÇO + TRANSPORTE
   ├─ services/  (lógica de domínio, pura)
   └─ transport/ (MCP sobre HTTP via fastmcp)
3. BACKEND (deep dive)
   └─ harness pi.dev como runtime; a repo NÃO constrói harness
4. CLIENTES
   ├─ Telegram  ← foco atual
   └─ TUI/PC    ← standby
```

Cada fase tem uma **condição de entrada verificável**. Não se começa a fase N+1 sem a métrica da fase N.

### D2 — Um único DOM unificado

Um modelo de dados **único e compartilhado** (`src/contracts/`) serve todas as aplicações. **Cada aplicação decide como usá-lo** — a decisão de projeção é do cliente, não da plataforma. A plataforma entrega o modelo; não entrega opinion about como o Telegram deve renderizar um KPI.

- **Tipagem forte:** Pydantic v2 estrito (`frozen=True`, `extra="forbid"`) — invariante do repo, mantida.
- **UID = chave de artefato.** O UEID de 4 partes (ADR-014) é a chave primária de todo artefato. Clientes convertem **KPIs, DESC e OKRs em UID** para que o mesmo artefato apareça em **views diferentes da timeline** sem duplicação. Isso substitui a noção de "cada fork tem seu schema" (fork 3 do Vanilla Pivot) por "um DOM, N projeções".
- **Grafo é parte do DOM**, não um efeito colateral: arestas tipadas entre UIDs, com integridade referencial real.

### D3 — Um único banco cloud serverless

**Postgres serverless** como store único. Candidata: **Supabase** (Postgres gerenciado + pgvector + RLS + Realtime + Edge Functions). Requisitos que a escolha precisa satisfazer:

| Necessidade | Exigência do store |
|---|---|
| Servir embeddings | **pgvector** (índice HNSW) |
| Servir grafo | tabela de arestas com FK + índices bidirecionais |
| Busca rápida por índices estruturados | índices compostos + GIN/tsvector + trigram |
| Versionar updates do vault entre clientes | histórico append-only + `revision` otimista |
| Paralelismo / multi-threading / multi-device | transações + RLS por cliente, **sem lock distribuído** |
| Tipagem forte | contratos Pydantic como SOT + drift test contra o SQL |

> **Ratificação pendente (única variável aberta desta ADR):** Supabase **versus** Postgres gerenciado mais simples (Neon) **versus** Postgres self-hosted (VPS + pgvector). A recomendação é **Supabase** — é o único que entrega pgvector + RLS + Realtime + Edge Functions sem operação própria. Isso é uma decisão de fornecedor, não de arquitetura: o schema e os contratos não mudam. Formalizada na SPEC-02 §R1.

### D4 — O vault deixa de ser um diretório e passa a ser um store versionado

O vault passa a ter **duas camadas com direção explícita** (o que mata o bug das duas árvores):

| Camada | Store | Canônico para | Direção |
|---|---|---|---|
| **Prose** | markdown em `vault/` | notas de planejamento, SONHO, prosa | humano escreve → agente lê |
| **Estruturado** | Postgres cloud | artefatos, KPIs, OKRs, relações, embeddings | **store vence** em campo estruturado |

O markdown deixa de ser lido por caminho automatizado para busca estruturada — o que elimina exatamente o defeito do `cadence.py` (`vault/daily/` inexistente) e do SPEC-01 da série Vanilla Pivot.

**Append-only é preservado nos dois lados:** no markdown (invariante existente) e no banco (`deleted_at` + `artifact_revisions` append-only; nenhuma escrita destrutiva).

### D5 — Invariante de escrita: uma escrita por store, versionada

**Substitui** o "vault_write é o sole writer" (ADR-012) por uma forma mais precisa:

| Store | Writer único | Conflito |
|---|---|---|
| `vault/` markdown | `vault_write` (ADR-012, inalterado) | lock de arquivo local |
| Postgres cloud | **service layer** (uma por store) | `revision` otimista + `idempotency_key` |

`expected_revision` desatualizado → **409**, nunca last-write-wins silencioso. Sem lock distribuído: a transação e o `revision` resolvem.

### D6 — Transporte: MCP sobre HTTP, sobre os serviços

O gateway MCP custom (22 tools, 9 quebradas) **sai**. O caminho é:

```
pi (harness)
  → MCP over HTTP (fastmcp, ~50 LOC)
    → services/ (domínio puro)
      → data client (Postgres)
```

Isto é a regra D4 do SPEC-05 aplicada à luz da virada: **fastmcp sobre a CLI** vira **fastmcp sobre as services**.

### D7 — Harness: pi, não um novo

O harness do agente é **externo e pronto**. A repo **não constrói** agent framework, grafo custom, orquestrador de agentes, checkpoint, memory layer nem SSE publisher — tudo isso está no corte do SPEC-05, e agora com motivo adicional: *não é para onde vai a força*.

O que a repo **faz** é expor a camada de dados por MCP e garantir que ela funcione no **fluxo normal de requisição** do pi.

### D8 — Clientes são projeções, não bifurcações

Cada cliente (Telegram, TUI, CLI) é uma **projeção do DOM**:
- converte KPIs/DESC/OKRs → UID
- consulta o DOM por índice estruturado
- renderiza sua própria view
- escreve de volta pelo mesmo DOM

Fork 3 e fork 4 do Vanilla Pivot (3 backends de tarefa, 3 UIs) morrem como conceito: **um store, N projeções**.

## §4 — Consequências

### Positivas

| Consequência | Por quê |
|---|---|
| O gate circular do vault se quebra | O vault deixa de esperar "as camadas funcionais" — o store é a camada |
| Busca estruturada fica viável | Índices reais + vector + grafo no mesmo banco, não `grep` em markdown |
| Multi-device / multi-client fica resolvido | Versionamento + RLS + Realtime, não copies divergentes |
| Complexidade total cai | O corte do SPEC-05 (~15k LOC) fica justificável *e* executável |
| Superfície de integração deixa de ser 22 tools | 6–8 tools MCP sobre services, todas com contrato |

### Negativas (aceitas)

| Custo | Mitigação |
|---|---|
| **Quebra a invariante "Fully local"** | Explicitamente substituída: *local-first + cloud store único*. O drift net precisa registrar a troca, não-negar |
| Dependência de fornecedor cloud | Schema e contratos não dependem do fornecedor; Postgres é o padrão (Supabase é uma implementação) |
| Latência de rede no caminho de leitura | Cache local + write-behind para leitura; sync offline-first |
| Segredos/credenciais de cliente | RLS por `client_id`; chaves por dispositivo; nada de segredo em disco no repo |
| O DOM precisa ser bom para todos | Falhar cedo: schema versionado + migrações + drift test contra os contratos |

### Invariantes que esta ADR **substitui**

| Invariante anterior | Nova forma |
|---|---|
| "Fully local — SQLite + filesystem only, zero cloud deps" (`docs/README.md`) | **Single cloud store + local cache** |
| "vault_write é o sole writer" (ADR-012) | **Um writer por store** (D5) |
| "Vault = markdown = fonte da verdade" (ADR-012, `master-branch-carro-chefe`) | **Prose = markdown; estruturado = Postgres** (D4) |
| "VAULT_ROOT = vault/ para todo caminho automatizado" (SPEC-01 Vanilla Pivot) | **Caminho canônico só para prosa**; estruturado vem do store |
| "3 UIs para 1 usuário" (fork 4) | **N projeções de 1 DOM** |

## §5 — Alternativas consideradas

| Alternativa | Por que **não** |
|---|---|
| **Continuar o Vanilla Pivot como está** (timeline local como artefato-alvo) | Resolve a ordem mas mantém o vault como diretório — não há versionamento multi-client nem busca estruturada. Não atende "múltiplos clientes e dispositivos" |
| **Terminar o Option D** (terminar o harness planejado) | ~6–9 pessoa-meses, e o relatório prova que **não resolve**: constrói mais máquina, o gate comportamental continua |
| **GraphQL próprio** | Resolver novo + servidor + auth + subscriptions = mais superfície. MCP já é o protocolo que o pi consome |
| **Neo4j / banco de grafo separado** | Duas fontes de verdade, duas consistências, mais operação. Arestas + FK em Postgres dão o grafo que precisa |
| **Chroma separado** (o `vibe_ops.db` atual tem coleção criada, 0 embeddings) | pgvector no mesmo Postgres: uma transação, um backup, um RLS |
| **Construir harness próprio** | Multiplicaria a complexidade de manutenção — o defeito diagnosticado |
| **S3/Markdown como store** | Sem índice estruturado, sem versionamento transacional, sem RLS |

## §6 — Regras de implementação

1. **Onde há invariante, código; onde há julgamento, prompt** (mesma regra do Vanilla Pivot — ela sobrevive à virada).
2. **Nenhum cliente escreve direto no banco.** Só `services/`. Clientes falam MCP.
3. **Pydantic v2 estrito é o contrato** (`src/contracts/`). O SQL é derivado e verificado por drift test — nunca editado à mão sem o contrato.
4. **Toda escrita é versionada e idempotente.** `revision` + `idempotency_key`. Conflito → 409, nunca sobrescrita silenciosa.
5. **Migrations versionadas e aditivas.** Sem `DROP COLUMN` em produção sem etapa de depreciação.
6. **O pi é o cliente de referência.** Qualquer capability da camada de dados precisa ser demonstrável no fluxo normal do pi, não só em teste unitário.
7. **Append-only nos dois stores.** Markdown: nunca deletar. Banco: `deleted_at` + revisões, nunca `DELETE` físico.
8. **Nenhuma TUI até o DOM estar servindo.** Telegram e TUI entram só depois da fase 1.
9. **Um UID por artefato, N views.** Conversão KPI/DESC/OKR → UID é responsabilidade do cliente, e usa o mesmo UID para todas as views.

## §7 — Relação com a série Vanilla Pivot (2026-10-30)

A série anterior não é descartada — é **re-alvo**. Mapeamento canônico:

| Spec anterior | Destino nesta virada |
|---|---|
| `01-vault-paths` | **Superada** — o problema das 2 árvores morre com D4 (store estruturado). O caminho canônico sobra só para prosa |
| `02-writer` (`life vault-note`) | **Re-alvo** — vira o **primeiro cliente** da service layer: uma nota vira UID e vai para o store |
| `03-dispatcher` (`skill-run`) | **Superada** — o dispatcher vira **MCP sobre services** (D6). A spec 03 (grafo-free) virou pré-requisito, não entrega |
| `04-timeline` | **Adiada** — a timeline é uma das *views* sobre o DOM, e só faz sentido depois do DOM existir. Deixa de ser "o artefato que falta" |
| `05-cut` | **Mantida e antecipada** — ~15k LOC a cortar, agora com motivo: é o que a camada de dados substitui. Continua **gated** (go explícito do owner) |

**A spec 01 e a spec 03 do Vanilla Pivot viram pré-requisitos de engenharia**, não entregas de produto.

## §8 — Fases e métrica de avanço

| Fase | Entrega | Métrica de passagem |
|---|---|---|
| **1. DOM** | Contracts Pydantic + schema SQL + drift test | Contrato e SQL divergem → teste falha; round-trip de um artifact por kind |
| **2. Store** | Postgres serverless provisionado + migrations + índices + pgvector + RLS | Busca por índice < 50ms p95 num corpus de 10k; escrita concorrente de 2 clientes sem lost update |
| **3. Sync** | vault markdown ↔ store, versionado, idempotente | Noted no vault aparece no store; 100% das escritas com `revision` |
| **4. Service + Transport** | `services/` + MCP over HTTP | `search`/`get`/`upsert` respondem via MCP no fluxo do pi |
| **5. Cliente Telegram** | projeção do DOM | KPI/DESC/OKR do vault aparecem no bot |

**Métrica de 14 dias (adaptada do Vanilla Pivot):** uma nota escrita num cliente **sem editar arquivo à mão**; **zero lost update** com 2 clientes ativos; `p95` de busca estruturada < 100ms.

> Se a métrica de 14 dias falhar com a camada de dados servindo, o diagnóstico final é **hábito**, não arquitetura — e a resposta é reduzir a ambição do sistema, não aumentar a máquina. (Regra herdada do Vanilla Pivot §"A métrica que decide se funcionou".)

## §9 — Specs desta série

| # | Spec | Entrega |
|---|---|---|
| 00 | [`2026-11-01-00-data-layer-series.md`](../../docs/superpowers/specs/2026-11-01-00-data-layer-series.md) | Índice da série, ordem, regras, correções |
| 01 | [`2026-11-01-01-unified-dom.md`](../../docs/superpowers/specs/2026-11-01-01-unified-dom.md) | O DOM unificado — schema, tipagem forte, UID |
| 02 | [`2026-11-01-02-cloud-store.md`](../../docs/superpowers/specs/2026-11-01-02-cloud-store.md) | O store cloud — versionamento, índices, vector, graph, RLS |
| 03 | [`2026-11-01-03-service-transport-pi.md`](../../docs/superpowers/specs/2026-11-01-03-service-transport-pi.md) | Services + transporte MCP + integração pi |

---

## Self-review

D1–D9 cobertas por §3. Cada fase tem métrica de passagem (§8) e condição de entrada. Nenhuma entrega de produto antes da fase 1. O mapeamento da série anterior está em §7, sem órfãos. O ponto de ratificação de fornecedor (D3) está isolado em um único item — a arquitetura não depende dele.

**Risco principal:** o DOM ficar grande demais antes de existir um cliente real que o force. Mitigação: a ordem D1 põe o cliente Telegram na fase 5, mas o **conjunto de kinds** (`sonho`, `plano`, `onda`, `fase`, `nota`, `kpi`, `desc`, `okr`, `tarefa`) é o que o Vault Pivot §7 já provou necessário — não é adivinhação.

*ADR-037 accepted 2026-11-01. Supersede, não reescreva.*
