# SPEC-INDEX — Data Layer Series (Virada Canônica)

**Date:** 2026-11-01 · **Status:** proposed — awaiting owner approval
**Origin:** virada canônica de 2026-11-01 (decisão do owner) · [ADR-037](../../code-docs/adr/ADR-037-data-layer-canonical-turn.md)
**Predecessor:** [Vanilla Pivot Series](2026-10-30-00-series.md) (2026-10-30) — ver §"Re-alvo" abaixo

---

## O que esta série resolve

O Vanilla Pivot resolveu a **ordem** (a infraestrutura foi construída antes do conteúdo). Esta série resolve o **alvo**: onde a força vai agora.

**A pergunta:** como hospedar o vault na cloud para versionar updates entre múltiplos clientes e dispositivos, servir **vector, graph e embeddings** a partir do mesmo store, e dar **busca rápida por índices estruturados** — com schema bom e tipagem forte — para que cada cliente (Telegram, TUI, CLI) seja só uma **projeção** do mesmo DOM?

**A resposta em 4 specs:**

```
vault/ (markdown, prosa)  ⇄  sync versionado  ⇄  Postgres cloud (DOM estruturado)
                                                   ├─ pgvector  → embeddings
                                                   ├─ edges/FK  → grafo
                                                   └─ índices   → busca estruturada
                                                            │
                                          services/ (domínio puro)
                                                            │
                                          MCP over HTTP (fastmcp)
                                                            │
                                          pi (harness) → clientes
```

---

## A série

| # | Spec | Entrega | Depende de | Bloqueia |
|---|---|---|---|---|
| 01 | [`2026-11-01-01-unified-dom.md`](2026-11-01-01-unified-dom.md) | O DOM unificado: schema, tipagem forte, UID | — | 02, 03 |
| 02 | [`2026-11-01-02-cloud-store.md`](2026-11-01-02-cloud-store.md) | O store cloud: versionamento, índices, vector, graph, RLS | 01 | 03 |
| 03 | [`2026-11-01-03-service-transport-pi.md`](2026-11-01-03-service-transport-pi.md) | Services + transporte MCP + integração pi | 01, 02 | — |

**Ordem obrigatória.** 01 antes de tudo (sem contrato, o SQL é adivinhação). 02 antes de 03 (não há transporte sem store). **Nenhum cliente antes de 03 estar verde** — Telegram e TUI entram depois.

**Estimativa: 5–8 dias** para as 3 specs com verificação em disco. Compare com os ~6–9 pessoa-meses do Option D e os ~3 dias do Vanilla Pivot: **o escopo é menor porque a tudo que não é dado está fora de escopo por decisão** (ADR-037 §3 D1).

---

## Re-alvo da série Vanilla Pivot (2026-10-30)

A série anterior não foi descartada — foi **re-alvo**. Ver ADR-037 §7.

| Spec anterior | Destino | Quem executa |
|---|---|---|
| `01-vault-paths` | **Superada** — o bug das 2 árvores morre com o store estruturado (ADR-037 D4). Sobra só o caminho canônico da prosa | — |
| `02-writer` (`life vault-note`) | **Re-alvo** — vira o **primeiro cliente** da service layer: nota → UID → store | SPEC-03 (fase 5) |
| `03-dispatcher` (`skill-run`) | **Superada** — o dispatcher vira **MCP sobre services** (ADR-037 D6) | SPEC-03 |
| `04-timeline` | **Adiada** — a timeline é uma *view* sobre o DOM; só faz sentido depois do DOM existir | cliente, depois |
| `05-cut` (~15k LOC) | **Mantida e antecipada** — agora é o que a camada de dados substitui. Segue **gated** (go explícito do owner) | owner |

**Consequência prática:** a SPEC-03 **absorve** o requisito da SPEC-03 anterior (`skill-run` sem grafo) como pré-requisito de engenharia, não como entrega de produto.

---

## As 5 regras da série

1. **Onde há invariante, código; onde há julgamento, prompt.** (Herdada do Vanilla Pivot — sobrevive à virada.)
2. **Um DOM, N projeções.** A plataforma entrega o modelo; cada aplicação decide como usá-lo. Nenhum campo "de Telegram" ou "de TUI" entra no contrato.
3. **Um writer por store, escrita versionada.** `vault_write` para o markdown; service layer para o Postgres. `revision` otimista + `idempotency_key`. Conflito → **409**, nunca last-write-wins.
4. **O pi é o cliente de referência.** Toda capability precisa ser demonstrável no fluxo normal de requisição do pi — não só em teste unitário.
5. **Append-only nos dois stores.** Markdown: nunca deletar. Banco: `deleted_at` + `artifact_revisions`, nunca `DELETE` físico.

---

## O que esta série NÃO faz

- **Não** especifica o cliente Telegram. Nenhum produto antes da base.
- **Não** mexe na TUI (standby por decisão — ADR-037 D1).
- **Não** constrói harness. O pi é o runtime; a repo não escreve agent framework (ADR-037 D7).
- **Não** implementa o corte do SPEC-05 Vanilla Pivot (~15k LOC) — é gated e fica para depois.
- **Não** revive PAV/Q_HE/regime (arquivado, ADR-024).
- **Não** faz `update`/`delete`/`done` no mesh (v1.2+, fora de escopo por ADR-013).

---

## A métrica que decide se funcionou

Não "o código compila". **Estas três, medidas 14 dias depois da SPEC-03:**

| Métrica | Fonte | Alvo |
|---|---|---|
| Notas escritas **sem editar arquivo à mão**, de um cliente que não é o desktop | `artifact_revisions` com `client_id` ≠ local | ≥ 5 |
| **Zero lost update** com 2 clientes ativos | log de `409` vs escritas aceitas | 0 perda |
| `p95` de busca estruturada | log do store | < 100 ms |

**Se (a) for 0 depois de 14 dias com a camada de dados servindo, o diagnóstico final é hábito, não arquitetura** — e a resposta é reduzir a ambição do sistema, não aumentar a máquina.

---

## A variável de fornecedor — RATIFICADA (R1)

**Supabase** — escolhido pelo owner em 2026-11-01. Único que entrega pgvector + RLS + Realtime + Edge Functions sem operação própria, e `fastmcp` + PostgREST cobrem o resto.

**Por que isto NÃO travou a série:** o schema (SPEC-01/02) é Postgres puro. Supabase é *uma implementação* do Postgres. Trocar de fornecedor depois muda 3 linhas de conexão e nenhuma linha de contrato. Formalizada na SPEC-02 §R1 (D10).

**Postgres de teste no CI:** via **testcontainers** (SPEC-02 D11) — os testes de store rodam em todo PR, não só em local.

---

## Correções verificadas nas specs (2026-11-01)

As specs foram escritas conferindo cada premissa contra o código do repo. Correções **já aplicadas**:

| # | Spec | O que estava errado | Correção |
|---|---|---|---|
| C1 | 01 | `UEID` como `str` solto | `UEID` é `class UEID(str)` em `src/contracts/common.py:60`, com `__get_pydantic_core_schema__` — o DOM reusa a **classe**, não reimplementa |
| C7 | 01 | o "fork 5 / UEID P0" do Vanilla Pivot §2 está **defasado** | ADR-033 (2026-09-21) já fez `sys_ikigai/entities/ueid.py` **importar** `_UEID_PATTERN` — o regex tem fonte única. O que resta é **duas identidades de tipo** (`class UEID(str)` vs `Annotated[str, StringConstraints]`), deferida por ADR-033 Alt E. O DOM usa `src.contracts.common.UEID` (a classe) — uma identidade só |
| C2 | 01 | kinds "inventados" | Os 10 kinds derivam do que o vault **realmente** contém (`vault/ikigai/closing-2026/`) + o que o Vanilla Pivot §7 provou necessário — não de um brainstorm |
| C3 | 01 | `parent_uid` sem FK | FK real no Postgres (SPEC-02), FK lógica no Pydantic (o repo tem 2 identidades de módulo — ver §Import-Path Rules do `life/CLAUDE.md`) |
| C4 | 02 | "Supabase já decidido" | O owner disse *"pode ser supabase"* — é candidata, não decisão. Ratificação explícita em R1 |
| C5 | 02 | RLS assumindo `auth.uid()` | O cliente é 1 usuário com N dispositivos; RLS por `client_id` claim, não por usuário Supabase Auth |
| C6 | 03 | "pi consome MCP" sem prova | `pi` consome MCP — mas a integração precisa ser **verificada no fluxo normal de requisição**, não assumida. Task 3.5 é a prova |

---

## Ordem de execução e onde parar

| Fase | Spec | Para quando |
|---|---|---|
| 1 | 01 — DOM | Contrato Pydantic + drift test contra o SQL redigido |
| 2 | 02 — Store | Store provisionado, migrations aplicadas, busca < 50ms p95 em 10k |
| 3 | 03 — Service + Transport + pi | `search`/`get`/`upsert` respondem via MCP no fluxo do pi |

**Depois da fase 3, e só depois:** cliente Telegram (primeiro cliente real) → timeline (view sobre o DOM) → corte do SPEC-05.

---

*Spec series proposed 2026-11-01. Aguardando aprovação do owner.*
