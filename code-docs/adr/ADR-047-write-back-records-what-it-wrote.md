---
id: ADR-047
title: "Emenda à ADR-043: o write-back regista no store o que escreveu"
date: 2026-11-11
status: accepted
---

> **Esta ADR emenda a [ADR-043](./ADR-043-vault-write-back.md).** A ADR-043
> continua publicada e não é reescrita — as ADRs aceites são imutáveis
> (`code-docs/adr/README.md`). O que muda é o que a ADR-043 **diz** sobre o
> write-back escrever no store: o §2 e o §10 recusam-no, e o código faz-o.
> A razão da divergência está escrita aqui, e a razão de o código fazer o que
> faz está escrita aqui também.

## 1. Veredito

**Entra:** uma emenda a **um** ponto da ADR-043.

> **O `vault_write` regista no store o que escreveu.** Depois de escrever o
> ficheiro, o escritor diz ao store qual é o conteúdo do ficheiro (`body`), o
> seu hash (`body_hash`) e que ficheiro é (`vault_path`) — pela via versionada
> de sempre (ADR-037 D5), com `client_id = "vault-write"`.

**O que a emenda NÃO toca, e é o que importa:**

| Invariante | Antes | Depois |
|---|---|---|
| O store escreve a prosa | ✓ | ✓ — o que chega ao ficheiro é a prosa **do store** |
| A prosa nunca reescreve o store | ✓ | ✓ — ver §3.2: o registo é o **ficheiro do próprio store**, reconhecido pela identidade, não a prosa do dono a impôr-se |
| Escrever em artefactos que já vieram de um ficheiro | recusado | recusado — o âmbito continua a ser os que **não** têm `vault_path` |
| O conflito é explícito | ✓ | ✓ — o ficheiro que divergiu não é reescrito |
| `push` para o GitHub | recusado | recusado |
| A **identidade** é o `ueid` no frontmatter | ✓ | ✓ — é ela que faz o registo ser reconhecido e não reingestado |

**Não entra, e a razão fica escrita:**

| Coisa | Veredicto | Porquê |
|---|---|---|
| O writer deixar de escrever no store | **recusado** | o PASS 6 (o ciclo fecha: a ingestão a seguir ao write-back dá `unchanged` e a revisão não sobe) **só** é literalmente verdadeiro se o store souber o hash do ficheiro. Sem o registo, o store diria que o corpo é outro, a ingestão reescreveria, a revisão subiria — e o ciclo abriria |
| O writer escrever em artefactos que já têm `vault_path` | **recusado** | continua a ser last-write-wins sobre a prosa do dono |
| O writer escrever por outra via que não a versionada | **recusado** | ADR-037 D5: uma escrita sem revisão e sem chave de idempotência é uma escrita sem dono |

---

## 2. A pilha

```text
   ┌────────────────────────────────────────────┐
   │  store (Postgres)                         │  ← canónico
   │  ikig.artifacts + vault_path              │
   └──────────────┬─────────────────────────────┘
                  │  VAULT_WRITE
                  │  1. lê o store
                  │  2. escreve o ficheiro  ───────────┐
                  │  3. REGISTA: body, body_hash,      │
                  │     vault_path (escrita versionada)│
                  ▼                                  │
   ┌────────────────────────────────────────────┐   │
   │  store, outra vez — com o que o writer     │◀──┘
   │  escreveu e o hash do ficheiro             │
   └──────────────┬─────────────────────────────┘
                  │
                  ▼
   ┌────────────────────────────────────────────┐
   │  INGESTÃO (vault-sync)                     │
   │  lê o ficheiro → encontra o `ueid` →       │
   │  o corpo É o que o store já diz →           │
   │  `unchanged`, a revisão não sobe            │
   └────────────────────────────────────────────┘
```

**O que NÃO está neste diagrama, e porquê:**

- **Nenhuma escrita de volta a partir do markdown.** A ingestão continua a ser
  a única que escreve no store **a partir de um ficheiro**. O writer escreve
  **para** um ficheiro e **regista** o que escreveu.
- **Nenhum `push`.** O `origin` continua a ser escrito pelo CI.
- **Nenhuma escrita no clone git.** `/opt/mathe/ikigai/vault` continua `ro` e
  descartável.

---

## 3. Justificativa

### 3.1 A tensão que a ADR-043 criou

A ADR-043 §2 escreve, no diagrama do que **não** entra:

> *Nenhuma escrita de volta no store. O `vault_write` escreve ficheiros, não
> artefactos.*

E o §10 põe na lista do que fica de fora:

> *Escrever no store a partir do markdown — a ingestão já faz isso; dois
> escritores do store é o que ADR-037 D5 proíbe.*

E, ao mesmo tempo, o §9 exige:

> | 6 | O ciclo fecha | ingestion depois do write-back ⇒ `unchanged`, e o `revision` não sobe | retirar o `ueid` do frontmatter ⇒ a ingestão cria um **segundo** artefacto e o teste falha |

As duas coisas **não podem ser ambas verdadeiras**. O PASS 6 é um critério
**sobre o estado do store**: a ingestão, depois do write-back, tem de dizer
`unchanged` e a revisão não pode subir. Isso só é verdade se o store já
descrever o ficheiro — e o store descreve um ficheiro pelo seu **hash**.

Logo: **o PASS 6 obriga o writer a escrever no store.** A ADR-043 escrevia
as duas metades, e elas não cabiam juntas. Esta ADR escolhe a metade que o
PASS exige e **escreve a razão**.

### 3.2 Porque isto NÃO é "a prosa a reescrever o store"

A regra que a ADR-043 substituiu (ADR-012) era: *o `vault_write` é o único
que escreve no vault; a prosa nunca reescreve o store*. O medo é o
last-write-wins: o ficheiro do dono passa por cima do que o store dizia.

O registo do writer não é isso, por três razões que se medem:

1. **O conteúdo registado é o do store.** O writer escreve `body = content`,
   onde `content` é `render_artifact(artifact)` — a prosa **do store**, com o
   frontmatter do store fundido. Não é uma transcrição do ficheiro: é o store
   a dizer-se a si próprio em markdown.
2. **A identidade torna o registo reconhecido.** O ficheiro carrega o `ueid`
   do artefacto. Quando a ingestão o lê, encontra a identidade e diz "este
   artefacto sou eu" — em vez de criar um segundo (que foi exactamente o bug
   medido: 18 duplicados em 23 ficheiros).
3. **O âmbito não mudou.** O writer escreve só o que **não** tinha ficheiro.
   Um artefacto que já tem `vault_path` tem um ficheiro que é de quem o
   escreveu — e o writer não lhe toca. A mão do dono continua intocável.

O invariante que sobrevive, escrito de forma que se possa falsificar:

> **O store escreve a prosa. A prosa do dono nunca reescreve o store. O
> writer escreve a prosa do store num ficheiro, e regista no store o que
> escreveu.**

### 3.3 Porque o registo tem de ser versionado

ADR-037 D5: uma escrita carrega `revision` e `idempotency_key`. O registo do
writer não é uma excepção — é uma escrita:

- `expected_revision` = a revisão que o writer leu. Se alguém escreveu por
  baixo, o registo é um **conflito** (409), e o conflito é **registado**,
  nunca forçado.
- `idempotency_key` = `vault-write:<uid>:<hash>:<revisão>`. A mesma ronda
  com o mesmo conteúdo é a mesma intenção.
- `client_id` = `vault-write` — distinto da ingestão (`vault-sync`) e do
  agente. No store, a autoria é visível.

---

## 4. A ponte que já existe

| Peça | Onde | Porque serve |
|---|---|---|
| `WriteRequest` | `src/contracts/dom.py` | a via versionada de sempre: revisão esperada, chave de idempotência, `client_id` |
| `vault_path` | `src/contracts/dom.py`, migração `0005` | diz **que ficheiro** é este artefacto — e `NULL` = nunca foi ficheiro = o writer pode escrevê-lo |
| `body_hash` | `src/contracts/dom.py` | o hash do **ficheiro** é o que torna a reingestão um `unchanged` |
| O `ueid` no frontmatter | `render_artifact` | fecha o ciclo: a ingestão reconhece o artefacto e não cria um segundo |
| `VaultSync._uid_for` | `src/services/sync.py` | o `ueid` declarado vence a identidade derivada do caminho |
| `VaultSync._ingest_file` | `src/services/sync.py` | o `body_hash` que decide se algo mudou |
| `client_id` | `WriteRequest` | distingue quem escreveu: `vault-write`, `vault-sync`, `pi-*`, `tg-*` |

O que **não** existe e esta emenda não precisa: uma tool nova, um canal novo,
um protocolo novo, uma migração.

---

## 5. O que está quebrado, com evidência

Medido no box a 2026-11-10/11 (`hetzner-vpn`):

| # | Facto | Como se mediu | Consequência |
|---|---|---|---|
| 1 | A ADR-043 diz que o writer **não** escreve no store | §2 e §10 da ADR-043 | um ADR publicado que **mente** sobre o código: o código escreve, e a peça diz que não |
| 2 | O PASS 6 **exige** que o store saiba o hash do ficheiro | ADR-043 §9, passo 6 | as duas metades não cabem juntas: uma tem de ceder |
| 3 | A primeira versão do writer **não** escrevia o `ueid` em 18 dos 23 ficheiros | `scanned=23 written=23` e a ingestão a seguir criou **18 duplicados**; o store foi de 1 976 para **1 994** | a identidade é o que fecha o ciclo — sem ela, o mesmo corpo chega ao store duas vezes |
| 4 | Com o `ueid` escrito **sempre**, o ciclo fecha | reparo medido: reset dos 18 `vault_path` → `scanned=18 written=18 conflicts=0` → **23/23** ficheiros com `ueid` → soft-delete das 18 cópias → store de volta a **1 976** | o registo no store é o que faz a ingestão dizer `unchanged` |
| 5 | Em repouso, nada se mexe | writer `scanned=0 written=0 unchanged=0 conflicts=0 skipped=0`; ingestão `scanned=1977 created=0 updated=0 unchanged=1976 skipped=25` | o registo não gera tráfego: o store já dice o que o ficheiro diz |
| 6 | O `revision` **não sobe** na segunda volta | o `unchanged=1976` da ingestão, e o `tests/store/test_vault_write_cycle.py` contra o Postgres real | o PASS 6 é literalmente verdadeiro, e é um teste |

O item 1 é o que se resolve com esta emenda. Os itens 3 a 6 são a prova de
que o que o código faz — e o que esta emenda passa a dizer — funciona.

---

## 6. Inventário, com a razão de cada peça

| # | Peça | Ficheiro | Porque existe |
|---|---|---|---|
| 1 | `VaultWrite._record` | `src/services/vault_write.py` | o registo: `body` = o ficheiro, `body_hash` = o seu hash, `vault_path` = o caminho relativo |
| 2 | A escrita versionada | `src/services/vault_write.py` | `expected_revision` + `idempotency_key` + `client_id = "vault-write"` |
| 3 | O `ueid` escrito **sempre** | `render_artifact` | é o que faz a ingestão reconhecer o artefacto — a correcção do bug dos 18 duplicados |
| 4 | `tests/store/test_vault_write_cycle.py` | `src/ikigai/tests/store/` | o PASS 6 contra o Postgres real |
| 5 | `tests/services/test_vault_write_back.py` | `src/ikigai/tests/services/` | os PASS 3/4/5/7/8 e o falsificador do PASS 6 |
| 6 | Esta ADR | `code-docs/adr/ADR-047-*.md` | a emenda, e a razão dela |

**O que não entra:** nenhuma migração, nenhum endpoint, nenhuma tool nova,
nenhuma mudança no âmbito do writer.

---

## 7. Dia zero

O que fica verdade quando esta emenda entra:

1. A ADR-043 continua publicada, com o seu texto — e com a sua tensão.
2. O `vault_write` **regista** no store o que escreveu, pela via versionada.
3. O `client_id` do registo é `vault-write`, e é visível no store.
4. O PASS 6 é literalmente verdadeiro: a ingestão a seguir ao write-back dá
   `unchanged` e a revisão não sobe.
5. O âmbito continua a ser os artefactos **sem** `vault_path`.
6. Um artefacto com `vault_path` continua intocável pelo writer.
7. Um ficheiro que divergiu do store é um **conflito** — nunca reescrito.
8. O `vault/` do clone git continua `ro` e descartável; não há `push`.

---

## 8. Evolução

| Quando | O que muda |
|---|---|
| **Agora** | o writer regista o que escreve, e a ADR-043 é emendada por esta |
| **Se o dono quiser editar os ficheiros do writer** | o writer passa a poder reescrever os **seus** ficheiros (os que têm `vault_path`), com o conflito explícito: só reescreve se o `body_hash` do store bater com o do ficheiro — é o §8 da ADR-043 |
| **Se a ingestão passar a ler a árvore escrita** | a ingestão lê o `vault-escrita` à `ro`; o `ueid` mantém o ciclo fechado |
| **Se o Syncthing deixar de ser a entrega** | o writer passa a fazer `commit` + `push` numa branch — e nesse dia o VPS precisa de `contents: write`, que é uma decisão de segurança à parte |

Nenhuma delas muda o invariante central: *o store escreve a prosa; a prosa do
dono nunca reescreve o store.*

---

## 9. Passos com PASS falsificável

| # | Passo | PASS | Como se falsifica |
|---|---|---|---|
| 1 | O writer **regista** o que escreveu | o artefacto escrito tem `body_hash` = o hash do ficheiro e `vault_path` = o caminho relativo | não registar ⇒ o store continua sem `vault_path` ⇒ o writer reescreve a cada ronda ⇒ o teste falha |
| 2 | O registo é **versionado** | uma revisão que mudou por baixo ⇒ o registo é um conflito, e o ficheiro **não** é forçado | pôr `expected_revision=None` ⇒ o registo sobrescreve ⇒ o teste falha |
| 3 | A **autoria** é visível | o artefacto escrito tem `client_id = "vault-write"` | escrever com o `client_id` da ingestão ⇒ o teste falha |
| 4 | O **ciclo fecha** | a ingestão a seguir ao write-back dá `unchanged`, e a revisão não sobe | retirar o registo ⇒ a ingestão reescreve e a revisão sobe ⇒ o teste falha |
| 5 | A **identidade** é escrita **sempre** | 23/23 ficheiros com `ueid` no frontmatter | retirar o `ueid` num corpo que já tem frontmatter ⇒ a ingestão cria um segundo artefacto ⇒ o teste falha |
| 6 | O writer **não** toca no que tem ficheiro | um artefacto com `vault_path` não ganha ficheiro novo | pôr `vault_path` no `body` de um artefacto novo ⇒ o teste falha |
| 7 | O **conflito** é explícito | um ficheiro que divergiu não é reescrito, e a divergência é registada | reescrever na mesma ⇒ o teste falha |
| 8 | Nenhum **`push`** | o contentor não tem `contents: write` nem token do GitHub | pôr um token no `.env` ⇒ o teste falha |

---

## 10. Fora de escopo

| Coisa | Porque fica de fora | O que a reabre |
|---|---|---|
| **Escrever em artefactos que já têm `vault_path`** | é onde a prosa do dono seria destruída | o §8 "se o dono quiser editar", com o conflito medido |
| **Mudar o âmbito do writer** | o âmbito (só sem `vault_path`) é a regra do conflito, não um detalhe | uma emenda que diga outra coisa, com PASS |
| **Tirar o `ueid` do frontmatter** | sem ele o ciclo abre, e o store recebe o mesmo corpo duas vezes | nunca, sem outra ADR |
| **`push` para o GitHub** | o Syncthing entrega ao desktop sem token | o Syncthing deixar de ser a via de entrega |
| **Um segundo processo de escrita no store** | ADR-037 D5: um writer por store | nunca, sem outra ADR |
| **Reescrever a ADR-043** | as ADRs aceites são imutáveis | nunca — emenda-se, como esta |

---

## 11. Decisões com default

| # | Decisão | Default | O que a muda |
|---|---|---|---|
| D1 | O writer **regista** o que escreveu | regista | nunca, sem outra ADR — é o PASS 6 |
| D2 | O registo é a **via versionada** de sempre | versionada | ADR-037 D5 mudar |
| D3 | O `client_id` é `vault-write` | `vault-write` | nada |
| D4 | O `body` registado é o **ficheiro** (frontmatter incluído) | o ficheiro | a ingestão passar a guardar só a prosa — e então o `body_hash` deixou de ser o hash do ficheiro |
| D5 | O âmbito continua a ser os que **não** têm `vault_path` | só sem `vault_path` | o dono querer que o writer mantenha os seus ficheiros (§8) |
| D6 | A identidade escreve-se **sempre** | sempre | nunca — sem ela o ciclo abre |
| D7 | O conflito é **explícito** e o ficheiro não é reescrito | conflito explícito | o dono decidir que o markdown é canónico — o que inverteria ADR-037 D4 |

---

## 12. Camadas de falha

| Camada | Se falhar | O que se vê |
|---|---|---|
| A escrita do ficheiro | o ficheiro não sai | o registo não acontece; o log diz qual |
| O registo no store | o store recusa (conflito) | o ficheiro **já está** no disco — o Syncthing leva-o na mesma; o registo fica pendente e a próxima ronda repete |
| A identidade no frontmatter | o ficheiro não é reconhecido | a ingestão cria um **segundo** artefacto — foi o bug dos 18 duplicados, e o PASS 5 desta ADR existe para o travar |
| A ingestão | o `vault/` não é lido | o store fica como estava; o ficheiro novo espera |
| O `commit` | o directório não é um repo git | o ficheiro **já** está no disco; só o registo git se perde |

**A ordem importa:** o ficheiro escreve-se **antes** do registo, e o registo
**antes** de qualquer entrega externa. Perder o registo custa uma ronda; perder
o ficheiro custa a prosa.

---

## 13. Referências

- [ADR-043](./ADR-043-vault-write-back.md) — a peça emendada: §2 e §10 (o que não entra), §9 (o PASS 6), §11 (as decisões)
- [ADR-037](./ADR-037-data-layer-canonical-turn.md) — D4 (o store é canónico num campo estruturado), D5 (uma escrita, versionada, conflito = 409)
- `ADR-012` — **não publicada**: fica no disco do dono e na história (ADR-037 §"publicação independente"). É a regra que esta peça substitui no ponto que a tornava binding
- `src/services/vault_write.py` — `VaultWrite._record`, `render_artifact`
- `src/ikigai/tests/store/test_vault_write_cycle.py` — o PASS 6 contra o Postgres real
- `src/ikigai/tests/services/test_vault_write_back.py` — os PASS 3/4/5/7/8 e o falsificador do PASS 6
