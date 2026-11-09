# ADR-040 — O estado do cliente, e os drafts que sobrevivem à ligação

**Status:** Accepted
**Date:** 2026-11-09
**Deciders:** human (Matheus) + agent
**Scope:** o que significa "cliente stateful" neste sistema, e o que fica de fora com a razão escrita
**Anchor:** [ADR-037](./ADR-037-data-layer-canonical-turn.md) · [ADR-039](./ADR-039-websocket-sync-transport.md) · ADR-012 (vault_write sole writer — **não publicada**, citada por ADR-037)

---

## 1. Veredito

**Entra:** o estado de um cliente que ainda não acabou de pensar — um **draft**
— como cidadão de primeira classe do store, alcançado por um **terceiro tipo
de frame** no websocket. Não é um sétimo tool, não é um artifact, e não entra
no índice nem no feed.

**Não entra, e a razão fica escrita:**

| Pedido | Veredito | Porquê |
|---|---|---|
| sync **bi-direccional** do vault | **recusado** | colide com ADR-012 (`vault_write` é o único writer) e com ADR-037 D4 (o store é canónico; o markdown é a prosa de entrada) |
| índice/compressão **"hysteresis"** | **recusado** | ADR-037 D1 adia a camada algorítmica; `PRODUCT.md` §5 lista PAV/hysteresis/scoring como fora do produto; não existe na árvore publicada |

O resto — ligação stateful, drafts que sobrevivem à reconexão, e o caminho
para uma TUI — **entra**, e é o que esta ADR especifica.

---

## 2. A pilha

```text
cliente (Telegram · TUI)
   │  websocket /sync            ← três tipos de frame, um socket
   ├── "call"    → os SEIS tools (ADR-037 D6, inalterado)
   ├── "event"   → o que o store anunciou (ADR-039)
   └── "draft"   → save · get · list · discard          ← NOVO (esta ADR)
   │
   ▼
services/drafts.py             ← as regras; o ÚNICO writer de ikig.drafts
   ▼
data/drafts.py                 ← persistência; revisão optimista + ledger
   ▼
ikig.drafts · ikig.draft_keys  ← migração 0006
```

---

## 3. Justificativa

### 3.1 O que "stateful" quer dizer aqui, e o que não quer

Hoje o websocket já é **bi-direccional no transporte**: o cliente chama, o
servidor responde, e o servidor empurra o que o store mudou. Isso resolve
*sincronização*. Não resolve **estado**: se o cliente cai, o que ele estava a
escrever desaparece, e um evento que chegou enquanto ele estava fora está
perdido para sempre.

"Stateful" neste sistema significa uma coisa só, e é verificável: **o que o
cliente estava a fazer sobrevive à ligação**. Não significa sessão em RAM no
servidor — isso seria uma segunda verdade, e a primeira regra deste repo é que
há um store.

### 3.2 Porque é que o draft não é um artifact

É a decisão central, e tem três razões, todas medíveis:

1. **A busca.** `ix_artifacts_body_fts` e `ix_artifacts_embedding_hnsw` indexam
   *todas* as linhas de `ikig.artifacts`. Uma frase a meio entraria no ranking
   de toda a query que partilhasse uma palavra com ela, e empurraria a prosa
   acabada para baixo. O store tem 1954 artifacts e 1954 vectores; uma frase
   inacabada a competir com eles é ruído com peso.
2. **O feed.** O trigger de `0004_artifact_events.sql` anuncia cada escrita. Um
   keystroke não é uma mudança ao DOM, e um feed que dispara a cada tecla não
   transporta nada.
3. **A história.** `ikig.artifact_revisions` é append-only e é a história de
   uma coisa que existe. Um draft é sobrescrito no lugar e descartado sem
   rasto.

### 3.3 Porque é que isto não é um sétimo tool

`test_drift_invariants.py` fixa a superfície em **exatamente seis** tools
(ADR-037 D6), e o websocket constrói o registo *a partir* do servidor MCP para
que as duas superfícies não possam divergir. Um sétimo tool partiria a guarda e
a razão dela.

Um draft também não é uma operação sobre o DOM: é estado. Por isso viaja num
tipo de frame próprio, ao lado de `call` e `event` — a mesma decisão de
desenho que separou o feed dos tools.

---

## 4. A ponte que já existe

Nada aqui inventa um caminho novo. O que já estava:

| Peça | Onde | O que já dava |
|---|---|---|
| o socket com três tipos de frame | `src/transport/ws_server.py:10-30` | `hello`, `result`, `event` |
| o anúncio do que o servidor sabe fazer | `hello_frame` | `tools` |
| a guarda optimista | `src/data/repository.py` (`_update`) | `expected_revision` → conflito |
| o ledger de idempotência | `ikig.idempotency_keys` | chave consumida → `unchanged` |
| o erro tipado que o transporte traduz | `src/contracts/errors.py` | `conflict`/`validation`/`not_found` |
| a identidade do cliente | `IKIGAI_CLIENT_ID` | um `client_id` por deployment |

O que faltava era **uma tabela e um tipo de frame**, não uma arquitetura.

---

## 5. O que está quebrado, com evidência

Não é hipótese. Medido nesta sessão, contra o store real do VPS:

| # | Defeito | Evidência |
|---|---|---|
| 1 | **O feed não retoma.** Um evento que chega com o cliente desligado está perdido — `broadcast` escreve para o conjunto de sockets vivos e não guarda nada. | `ws_server.py:237-244`; não há sequência nem cursor |
| 2 | **O cliente não tem identidade própria.** Um draft scoped a um socket morreria com ele — que é exatamente o que os drafts existem para evitar. | não havia estado por cliente em lado nenhum |
| 3 | **Um cliente que retenta escreve duas vezes** se a chave de idempotência não distinguir a *escrita* do *conteúdo*. Já corrigido para a ingestão nesta sessão (`6aeae7ab`); o mesmo erro estava disponível aqui. | ver §7 de `sync.py` |

O defeito **1** fica **fora do âmbito desta ADR** e registado em §10: retomar o
feed exige uma tabela de eventos, e o trigger de hoje anuncia sem persistir.

---

## 6. Inventário, com a razão de cada peça

| Peça | Ficheiro | Porque existe |
|---|---|---|
| O contrato | `src/contracts/drafts.py` | `Draft` (sem `uid` — não está no DOM), `DraftSaveRequest` (a mesma forma do `WriteRequest`), `DraftOutcome` |
| O schema | `src/contracts/migrations/0006_drafts.sql` | `ikig.drafts` com chave `(client_id, draft_id)`; `ikig.draft_keys` para o ledger |
| A persistência | `src/data/drafts.py` | save/get/list/discard; a guarda na revisão **e** no cliente |
| As regras | `src/services/drafts.py` | o único writer; carimba o relógio, preserva o `created_at` |
| A cablagem | `src/services/wiring.py` | `Services.drafts` |
| O transporte | `src/transport/ws_server.py` | `type: "draft"` com `op` ∈ {save, get, list, discard} |
| O anúncio | `hello_frame` | `drafts: ["save","get","list","discard"]` |

**Decisões dentro das peças, e porquê:**

- **`(client_id, draft_id)` e não um UEID.** Um draft não tem identidade no DOM
  porque ainda não está no DOM. Dois dispositivos a compor ao mesmo tempo são
  dois drafts.
- **Um ledger próprio (`draft_keys`) e não `ikig.idempotency_keys`.** Esse
  ledger tem uma coluna `uid` que aponta para um artifact; um draft não tem
  uid, e uma chave contra um uid inexistente é uma foreign key a apontar para
  o nada.
- **`created_at` preservado no segundo save.** Re-carimbar a cada tecla tornava
  "quando é que eu comecei isto?" irrespondível.
- **O `discard` corre numa transação.** O `client.execute` devolve **linhas**;
  a resposta a um `delete` é um `rowcount`. Ler `rowcount` de uma lista de
  linhas é como um delete passa a acreditar que não apagou nada — e foi um bug
  real, apanhado por um teste antes de correr contra o store.

---

## 7. Dia zero

O que isto muda para quem chega:

```bash
# a migração é aplicada pelo api no arranque, como as outras
cd deploy && docker compose up -d api

# o store ganha duas tabelas
docker compose exec db psql -U ikigai -d ikigai -c '\dt ikig.draft*'
```

Nada muda na superfície MCP, no bot, no harness, nem na ingestão. Um cliente
que ignore os drafts continua a funcionar exatamente como antes — o
`hello_frame` diz que eles existem, e não os impõe.

---

## 8. Evolução

Quando o **TUI** chegar, o caminho é o mesmo socket:

1. liga a `/sync`, recebe `hello` com os seis tools e as quatro operações de draft;
2. `{"type":"draft","op":"list"}` ao arrancar, e o utilizador vê o que deixou a meio;
3. `{"type":"draft","op":"save","draft_id":"...","expected_revision":N}` a cada
   pausa de teclado, e a reconexão não perde nada;
4. quando o utilizador manda commitar, o cliente chama `upsert_artifact` — o
   draft não commita por ele (§9).

O passo que isto **não** dá, e que fica em §10: retomar o *feed*. Um cliente
que esteve fora sabe o que **escreveu** (os drafts), não o que **mudou** (os
eventos).

---

## 9. Passos com PASS falsificável

| # | Passo | PASS | Como se falsifica |
|---|---|---|---|
| 1 | A superfície continua seis | `pytest -k tool` verde; `CANONICAL_TOOLS` verde | acrescentar um tool de draft e ver a guarda falhar |
| 2 | Um draft não entra na busca | `search_artifacts` com o texto do draft devolve 0 | gravar o draft em `ikig.artifacts` e ver a busca devolvê-lo |
| 3 | Um draft não dispara o feed | nenhum frame `event` depois de um save | pôr o trigger a ler `drafts` e ver o evento chegar |
| 4 | Uma revisão obsoleta é conflicto | 409 com `detail` "stale" | forçar `expected_revision` errado — o **`discard` foi o bug real aqui** |
| 5 | Um cliente não lê o draft de outro | `list`/`get` de outro `client_id` devolve vazio/404 | tirar o `client_id` do `WHERE` e ver o teste falhar |
| 6 | Um save repetido não escreve duas | `outcome=unchanged`, "already consumed" | apagar o ledger e ver a segunda escrita passar |
| 7 | O serviço não commita | `ast` do módulo não importa `ArtifactService` | importá-lo e ver o teste falhar |

Todos os sete correm sem base de dados, exceto o 1 e o 2 quando exercidos
contra o store: os fakes capturam o SQL e os argumentos, que é onde um filtro
desaparece em silêncio.

---

## 10. Fora de escopo

| Coisa | Porque fica de fora | O que a reabre |
|---|---|---|
| **Sync bi-direccional do vault** | ADR-012: `vault_write` é o único writer de `vault/`, e o vault é append-only. ADR-037 D4: o store ganha em campo estruturado, o markdown é a prosa de entrada. Escrever do store para o vault cria um segundo writer e um segundo canónico. | Uma ADR que **substitua** ADR-012 explicitamente, com a direção, o conflito e o lock escritos. Não é um incremento: é a troca de um invariante. |
| **Índice/compressão "hysteresis"** | ADR-037 D1 adia a camada algorítmica; `PRODUCT.md` §5: "a camada algorítmica — PAV, *hysteresis*, scoring: adiada por ADR-037 D1, e o repo não publica kernel nenhum". Não existe na árvore publicada. | Dados reais e uma ADR que a promova — e ela vem **depois** do store, não antes. |
| **Retomar o feed** | Exige uma tabela de eventos: o trigger de `0004` anuncia sem persistir, e um `NOTIFY` não é lido por quem não estava ligado. | Uma migração `0007` com `ikig.artifact_events` + sequência + cursor no `hello`. É o degrau seguinte, e é pequeno. |

**Sobre "bi-direccional":** o transporte **já é** bi-direccional (chamadas num
sentido, eventos no outro). O que o dono pediu pode já estar cumprido no que
toca ao transporte, e ser só a *escrita de volta para o vault* que está barrada.
Vale a pena confirmar qual dos dois antes de reabrir ADR-012.

---

## 11. Decisões com default

| # | Decisão | Default | O que a muda |
|---|---|---|---|
| D1 | O draft vive no store, não na memória do cliente | store | um cliente que nunca reconecta |
| D2 | A chave é `(client_id, draft_id)` | por cliente | multi-utilizador real (hoje é single-player, ADR-037 D1) |
| D3 | O `client_id` vem de `IKIGAI_CLIENT_ID` quando o frame não o nomeia | `owner` | o segundo dispositivo real, que exigiria identidade por ligação |
| D4 | Um draft guarda `kind` | sim | nada: é o que permite ao cliente saber que campos pedir antes de pedir |
| D5 | O draft **não** expira | não expira | um cliente que acumule drafts órfãos — aí é `discard`, não um TTL |

---

## 12. Camadas de falha

Cada uma falha sozinha, e nenhuma leva as outras:

| Camada | Se falhar | O que o cliente vê |
|---|---|---|
| o socket | o cliente fica sem canal | reconecta; os drafts estão no store |
| o frame | `malformed` / `validation` com o id | corrige e reenvia |
| a revisão | `conflict` + `detail` | relê e reaplica |
| o ledger | a chave não é consumida | o retry escreve — e é por isso que a chave leva o conteúdo |
| o store | o socket responde `error`, o `/healthz` fecha | o container fica unhealthy, e é a verdade |
| a migração | o `api` não arranca (aplica no arranque) | nada serve, e é a ordem correta |

---

## 13. Referências

- [ADR-037](./ADR-037-data-layer-canonical-turn.md) — D1 (ordem), D4 (store canónico), D5 (uma escrita, versionada), D6 (seis tools)
- [ADR-039](./ADR-039-websocket-sync-transport.md) — o websocket como segundo transporte e o feed
- `ADR-012` — `vault_write` como único writer do vault. **Não publicada**: fica no disco do dono e na história, como ADR-037 §"publicação independente" dispõe. É citada por ADR-037 e por esta ADR, e não por link, porque um documento publicado não pode ligar a um caminho que o branch não publica.
- `specs/production-readiness/PRODUCT.md` §5 — "a camada algorítmica — PAV, *hysteresis*, scoring: adiada"
- `src/ikigai/tests/test_drift_invariants.py` — `CANONICAL_TOOLS`, a guarda dos seis
- `src/contracts/migrations/0004_artifact_events.sql` — o anúncio que não persiste
