# ikigai — ROADMAP

**Feature id:** `production-readiness`
**Data:** 2026-11-06
**Estado:** execução — as decisões D1–D4 estão fechadas; os gates G1–G5 são a sequência
**Âncora:** [`PRODUCT.md`](./PRODUCT.md) (o que é e em que estado) · [`TECH.md`](./TECH.md) (o plano e os PASS)
**Código medido:** `e675b438`

> Este documento liga a **árvore de planeamento** (o que existe e o que falta
> em cada nível), o **grafo de dependências** (o que tem de vir antes do quê) e
> os **gates** (os ensaios que fecham cada fase, com critério de aceitação
> falsificável).

---

## 1. A árvore de planeamento, e o buraco nela

O repositório tem um meio forte e duas pontas vazias. A tabela diz o que há em
cada nível da hierarquia SDD e o que falta.

| Nível | Pergunta que responde | Documento | Estado |
|---|---|---|:-:|
| **BRD** | *porquê este produto, para quem, e o que decide se funcionou* | **não existe como documento** | ⛔ |
| **PRD** | *o que o produto faz, e como se sabe que faz* | [`PRODUCT.md`](./PRODUCT.md) (novo, 2026-11-06) — as invariantes `B1`–`B10` e a matriz de prontidão | 🆕 |
| **SPEC** | *o comportamento observável, numerado* | a série de 2026-11-01: [`00`](../../docs/superpowers/specs/2026-11-01-00-data-layer-series.md) · [`01 DOM`](../../docs/superpowers/specs/2026-11-01-01-unified-dom.md) · [`02 Store`](../../docs/superpowers/specs/2026-11-01-02-cloud-store.md) · [`03 Service+Transporte`](../../docs/superpowers/specs/2026-11-01-03-service-transport-pi.md) — ⚠️ **escrita antes do corte**: cita `sys_ikigai/`, `src/mesh/` e `interfaces-cli`, que já não estão publicados | ⚠️ |
| **ADR** | *que decisão foi tomada, e o que ela eliminou* | [`011`](../../code-docs/adr/ADR-011-ikigai-mcp-http-sse-transport.md) · [`013`](../../code-docs/adr/ADR-013-canonical-scope-discipline.md) · [`014`](../../code-docs/adr/ADR-014-ueid-canonical-format.md) · [`033`](../../code-docs/adr/ADR-033-ueid-single-source-mandate.md) · [`037`](../../code-docs/adr/ADR-037-data-layer-canonical-turn.md) | ✅ |
| **TECH** | *como se constrói, com que ordens e que provas* | [`specs/data-layer/TECH.md`](../data-layer/TECH.md) (2026-11-01) · [`specs/production-readiness/TECH.md`](./TECH.md) (novo) | ✅ |
| **Tasks** | *o que se executa, em que ordem, com que aceitação* | **não existe como artefacto** — vive no §9 do `TECH.md` e neste ficheiro | ⛔ |

### 1.1 O buraco do topo: o BRD

O BRD não foi escrito. As suas peças existem dispersas:

| Peça do BRD | Onde está hoje | Falta |
|---|---|---|
| A tese do produto | [`README.md`](../../README.md) §1 · ADR-037 | uma afirmação única de **para quem** e **que problema resolve** |
| A métrica que decide | ADR-037 §8 — as três métricas dos 14 dias | está numa ADR, não num BRD |
| As prioridades em PT-BR | `vault/_strategics_excerpt.md` (Vida > Trabalho, RECOVER > PUSH, anti-padrões) | está num ficheiro de vault, não num BRD |
| O utilizador e o momento | [`PRODUCT.md`](./PRODUCT.md) §1 | ✅ (nasceu hoje) |
| O que o produto **não** é | [`PRODUCT.md`](./PRODUCT.md) §5 | ✅ (nasceu hoje) |

**A acção**: `specs/product-brief/PRODUCT-BRIEF.md` — curto, com a métrica no
topo. **Não é um pré-requisito da execução**: o BRD organiza a história, não
trava o código.

### 1.2 O buraco do meio: a série de specs é anterior ao corte

A série `2026-11-01-0{0..3}` é a especificação de comportamento do DOM, do
store e do transporte — e é **o que o `TECH.md` de 2026-11-01 prometeu**. Mas
foi escrita antes do corte de âmbito e cita árvores que já não estão
publicadas (`sys_ikigai/`, `src/mesh/`, o entry `interfaces-cli` do CI).

**A acção**: reescrever a série em cima do que existe, ou marcá-la como
histórico e deixar o `PRODUCT.md` (invariantes `B1`–`B10`) ser a especificação
vigente. **Recomendação**: a segunda — a série é um documento datado de uma
decisão datada, e ADR-037 §"publicação independente" diz que isso é história,
não arquitectura.

### 1.3 O buraco de baixo: as Tasks

O `TECH.md` §9 tem os nove passos com PASS. O que falta é o artefacto que os
transforma em trabalho executável — com dependências, dono e ordem.

**A acção**: `specs/production-readiness/TASKS.md`, gerado a partir do §9 do
`TECH.md`, com uma entrada por passo (`S1`…`S9`), o PASS, os ficheiros que
toca e a dependência. **Formato**: a convenção SDD — cada task cabe numa
sessão, tem um objectivo, entradas, saídas e uma verificação.

### 1.4 As ADRs que faltam

| ADR | Decisão | Porquê merece ADR |
|---|---|---|
| **ADR-038** | **O store é single-player.** O `client_id` é rótulo de auditoria, não isolamento; as políticas de RLS ficam inertes e declaradas | muda o que o store **promete** (D1) — e a promessa é o que o ADR-037 D5 construiu |
| **ADR-039** | **A semântica sai do contrato v1** até haver provider; o MCP passa a ter 5 tools | muda o **contrato público** do transporte (D2) |
| **ADR-040** | **A âncora de identidade do cliente Telegram é o `message_id`, carried no 3.º segmento do UID** | toca o formato do UID (ADR-014) e decide se o bot revisa ou duplica (D3) |
| ~~ADR-041~~ | ~~o store prova-se no CI~~ | **não é ADR** — é engenharia; vive no `TECH.md` §7 e §9 (D4) |

---

## 2. O grafo

```mermaid
graph TD
    D["D1–D4 fechadas<br/>2026-11-06"] --> G1
    G1["G1 · STORE<br/>S1 job de integração · S2 e2e do MCP<br/>14 testes: skip → pass"] --> G2
    G2["G2 · CONTEÚDO<br/>S3 VaultSync ligado · S4 frontmatter<br/>store com linhas · índice não vazio"] --> G3
    G2 --> G4
    G3["G3 · HARNESS (pi)<br/>rotina do pi contra a api real"] --> G5
    G4["G4 · TELEGRAM<br/>o dono escreve · editar revisa"] --> G5
    G5["G5 · ENTREGA<br/>S8 clone → deploy → healthcheck"] --> M["MÉTRICA DE 14 DIAS<br/>ADR-037 §8"]
    M --> T["escopo futuro<br/>PRODUCT.md §7 · T1…T10"]
    G1 -.-> A["ADRs 038 · 039 · 040"]
    G2 -.-> A
```

**As dependências que não se podem quebrar:**

- **G1 antes de tudo.** Sem um Postgres real, cada passo seguinte é testado
  contra dublês — que é o que a suite faz hoje, e é por isso que 150 testes
  verdes não provam o produto.
- **G2 antes de G3 e G4.** O `pi` e o Telegram escrevem no mesmo store; se o
  store nasce vazio e sem grounding, os dois vão "funcionar" e não vão
  encontrar nada.
- **G3 e G4 em paralelo.** São clientes diferentes do mesmo api; nenhum
  depende do outro.
- **G5 antes da métrica.** A métrica de 14 dias mede um sistema em produção
  daily; um sistema que só existe numa máquina não a mede.
- **A métrica antes de T1…T10.** ADR-037 D1: a camada algorítmica vem depois
  dos dados, e os dados vêm depois de o sistema estar vivo.

---

## 3. Os gates

Cada gate tem: o que se faz, o **critério de aceitação** (falsificável), o
que conta como falha, e a variante manual (para o VPS, quando o box voltar).

### G1 · Store — *o Postgres real aceita o schema e o repositório relê*

| | |
|---|---|
| **Onde** | job novo no CI (`integration-stack`), com Docker do runner |
| **Passos** | `docker build` → `compose up -d db api` → `apply up` → healthcheck → os 14 testes de `tests/store/` |
| **Critério de aceitação** | **os 14 testes passam** (hoje: `skipped`) **e** `python -m src.transport.healthcheck` sai 0 |
| **Falso positivo** | "passou" com `skipped` — o job tem de **falhar** se algum teste saltar |
| **Falsificação** | remover o `services:`/Docker do job ⇒ os testes saltam ⇒ o job falha |
| **Manual (VPS)** | `docker compose up -d --build` · `docker compose exec api python -m src.contracts.migrations.apply up` · `docker compose exec api python -m src.transport.healthcheck` |
| **Invariantes** | B1, B2, B3 |

### G2 · Conteúdo — *a prosa entra e o grounding chega*

| | |
|---|---|
| **Onde** | CI, com o stack de G1 a correr |
| **Passos** | ingestionar o `vault/` → `search_artifacts` → carregar os `strategics/` |
| **Critério de aceitação** | (a) `search_artifacts` devolve um artefacto cujo `body_hash` é o hash de um ficheiro conhecido do vault; (b) `load_strategics(<raiz real>)` devolve **9 documentos** e o `index` não está vazio |
| **Falso positivo** | um teste com fixtures inventadas a passar — o teste tem de apontar para o **corpus publicado** |
| **Falsificação** | remover o `tags:` de um `strategics/*.md` ⇒ o índice perde-o ⇒ o teste falha |
| **Invariantes** | B8, B9 |

### G3 · Harness — *o `pi` corre uma rotina de verdade*

| | |
|---|---|
| **Onde** | a máquina do dono (o `pi` está instalado) ou o VPS, por túnel SSH — `.pi/mcp.json` aponta para `http://127.0.0.1:8000/mcp` |
| **Passos** | `pi mcp list` (tem de mostrar o servidor `ikigai` e as suas 5–6 tools) → `pi -p "<prompt da rotina>" --mode json` → o store |
| **Critério de aceitação** | por rotina: o artefacto do **tipo** certo existe no store, com os **campos que o tipo exige** |
| **Detalhe por rotina** | `daily-note` ⇒ uma `nota` · `weekly-review` ⇒ uma `revisao` · `monthly-review` ⇒ uma `desc` **com `rationale`** (a skill exige as duas linhas) · `quarterly-plan` ⇒ `plano` + `fase` + `okr` + `onda`, ligados por `parent_of`/`derives_from` |
| **Falso positivo** | o agente responder em prosa sem chamar tool nenhuma — o critério é a **tool chamada** e a **linha no store**, não a resposta |
| **Falsificação** | apontar `.pi/mcp.json` para uma porta errada ⇒ `pi mcp list` tem de mostrar o erro, e o gate tem de reprovar |
| **Invariantes** | B10, B1 |

### G4 · Telegram — *o dono escreve do telefone, e editar revisa*

| | |
|---|---|
| **Onde** | o bot no VPS (o token e a allowlist vivem em `deploy/.env`) |
| **Passos** | `/nota <título>` → o store → o `pi` relê |
| **Critério de aceitação** | (a) a nota existe com `revision = 1`; (b) **editar a mensagem produz `revision = 2` e UM artefacto** (hoje duplica); (c) `/desc` com uma linha → o bot **pergunta a segunda e não escreve nada**; com duas linhas → escreve a decisão com a `rationale`; (d) `/busca` devolve a nota |
| **Falso positivo** | "o bot respondeu bem" — o critério é o **estado no store**, não a resposta do bot |
| **Falsificação** | repor `expected_revision: None` ⇒ editar duplica ⇒ o gate reprova |
| **Invariantes** | B1, B2, B10 |

### G5 · Entrega — *um clone vira um serviço*

| | |
|---|---|
| **Onde** | o VPS |
| **Passos** | `git clone` → `bash scripts/deploy-vps.sh main` → healthcheck |
| **Critério de aceitação** | healthcheck verde **sem intervenção humana**, a partir de um clone limpo, e o `db-data` com **dump antes** do `up` novo |
| **Falso positivo** | "funciona na minha máquina" — o critério é um clone **limpo**, num directório novo |
| **Falsificação** | trocar o script por uma versão sem dump ⇒ o teste de rollback falha |
| **Invariantes** | — |

---

## 4. A sequência

Três ondas. Cada onda tem um PASS próprio e pode ser mergeada sozinha.

| Onda | Passos | Leva | PASS da onda |
|---|---|---|---|
| **O1 · Provar o store** | S1, S2 (+ I9, I10, I11) | o CI passa a ter Docker e a provar o Postgres | **os 14 testes do store passam no CI** |
| **O2 · Encher e ancorar** | S3, S4, S7 (+ ADR-038) | o vault entra, o grounding chega, o contrato deixa de prometer isolamento | **o store tem linhas do vault e o índice não está vazio** |
| **O3 · O dono escreve** | S5, S6, S12 (+ ADR-039, ADR-040) | o bot revisa, a semântica sai, o cliente tem timeout | **editar no Telegram revisa em vez de duplicar** |
| **O4 · Entregar** | S8, S9 (+ ADR-040) | o deploy passa a ser do branch | **clone → serviço, sem mão** |

**O porquê desta ordem**: a O1 é a única que desbloqueia a verificação de todas
as outras. A O2 é a que dá conteúdo ao produto. A O3 é a que fecha a promessa
do conflito (B2). A O4 é a que torna o sistema repetível. E a **métrica de 14
dias** vive depois da O4.

---

## 5. Critérios de aceitação do produto

As invariantes do `PRODUCT.md` §2, mapeadas no gate que as prova. A coluna
**hoje** é a medição de 2026-11-06.

| Invariante | Gate | Critério de aceitação | Hoje |
|---|:-:|---|:-:|
| **B1** nota escrita no Telegram existe no store e é relida pelo `pi` | G1, G3, G4 | o artefacto existe com o tipo certo, a revisão certa e o corpo lido de volta | não provado |
| **B2** zero escritas perdidas; revisão obsoleta = 409 | G1, G3, G4 | duas escritas concorrentes com a mesma revisão ⇒ **1× 409, 0 sobrescrita** | parcial (o store sim; o cliente não chega lá) |
| **B3** idempotência | G1 | a mesma `idempotency_key` duas vezes ⇒ **uma** escrita | provado em memória |
| **B4** o cliente falha fechado | G3, G4 | sem `IKIGAI_BOT_ALLOWED_CHAT_IDS` o bot **não arranca** | provado |
| **B5** o bot nunca abre a base de dados | G4 | o bot não tem DSN no compose e fala MCP | provado |
| **B6** o transporte nunca transporta SQL | G1, G3 | zero `select\|insert\|update\|delete` em `mcp_server.py` | provado |
| **B7** o healthcheck mede o plano de dados | G1 | a inserção de sonda passa (ou é recusada pela RLS) — nunca `select 1` | provado |
| **B8** a prosa entra pelo vault e sai como linhas tipadas | G2 | uma linha por ficheiro ingerido, com o `body_hash` certo | **não provado** |
| **B9** o grounding estratégico chega ao agente | G2, G3 | o índice tem os 9 documentos e o agente os cita | **não provado** |
| **B10** a cadência produz o artefacto do seu tipo, com os campos que o tipo exige | G3 | o `pi` produz uma `desc` com `rationale`, um `okr` com `key_result` | parcial |

**Contagem**: 5 provadas · 3 parciais · 2 não provadas. **Depois da O4**: 10
provadas, e o único teste que falta é o dos 14 dias.

---

## 6. O que fica registado e não executado

O escopo futuro — as alternativas a D1–D4 e as tracks `T1`…`T10` — está em
[`PRODUCT.md` §7](./PRODUCT.md), com o gatilho de cada uma. Resumo da ordem:

```
G1 → G2 → G3/G4 → G5 → MÉTRICA 14 DIAS → T1 T2 → T3 T4 → T5…T10
```

`T4` (embeddings reais) é a primeira track que **custa dinheiro por uso** e a
primeira que toca no caminho de escrita — por isso vem depois de o sistema
estar vivo e medido, e não antes.

---

*ROADMAP.md — 2026-11-06 — os gates G1–G5 e a sequência O1–O4. Actualizar
no mesmo PR em que um gate mude de PASS, ou em que uma ADR nova preencha o
§1.4.*
