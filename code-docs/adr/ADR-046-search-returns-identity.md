---
id: ADR-046
title: "A busca devolve a identidade; a prosa pede-se à parte"
date: 2026-11-11
status: accepted
---

## 1. Veredito

**Entra:** uma mudança ao **contrato público** do `search_artifacts`. A busca
passa a devolver `ArtifactSummary` — a identidade e os metadados de cada
artefacto — e **não** a prosa. O corpo lê-se com `get_artifact`, a uma chamada
de distância, que é o que a skill de leitura já descrevia.

**Não entra, e a razão fica escrita:**

| Coisa | Veredicto | Porquê |
|---|---|---|
| Um `preview` do corpo (os primeiros N caracteres) | **recusado** | um corpo truncado é um corpo que se pode citar como se estivesse inteiro. O agente precisa de um facto, não de um fragmento |
| Um `include_body` opcional na query | **recusado** | a knob que ninguém liga não muda nada; a knob que alguém liga repõe o payload. O que se quer é uma busca, e a busca é uma |
| Trazer os **campos tipados** para a busca (o `target` do KPI) | **fora** | estão em tabelas de extensão; juncá-las à busca é um join por chamada, e a busca não os tinha antes. Não é o que esta ADR mede |
| Mover a prosa para o `embed_text` | **recusado** | `embed_text` embute texto; não o devolve. Não é um caminho de leitura |
| Trocar o `search_artifacts` por outra tool | **recusado** | são seis tools (ADR-037 D6) e a sexta não muda por causa de um payload |

**A regra que substitui a intuição:** *a busca responde "quais"; a leitura
responde "o quê".* A prosa é a resposta da segunda pergunta, e paga-se por ela
quando se pergunta.

---

## 2. A pilha

```text
        agente (pi)
              │  search_artifacts  →  identidade + metadados   (8,9 KB / 20 hits)
              │  get_artifact      →  a prosa de UM artefacto   (a uma chamada)
              ▼
      ┌──────────────────────────┐
      │  TRANSPORTE (MCP)        │
      │  6 tools · sem SQL       │
      └────────────┬─────────────┘
                   ▼
      ┌──────────────────────────┐
      │  SERVIÇOS                │
      │  ArtifactService.search  │
      └────────────┬─────────────┘
                   ▼
      ┌──────────────────────────┐
      │  DATA                    │
      │  select … sem `body`     │   ← a coluna não existe no SELECT
      └──────────────────────────┘
```

**O que NÃO está neste diagrama, e porquê:**

- **Nenhum `body` no caminho da busca.** Nem seleccionado, nem esvaziado depois:
  um corpo que é buscado e deitado fora já cruzou a rede e já ocupou memória.
- **Nenhuma escrita.** Isto é uma leitura que fica mais leve. O store, o
  schema e as migrations não se tocam.

---

## 3. Justificativa

### 3.1 O que estava a medir mal

A métrica de 14 dias (ADR-037 §8) tem três condições, e uma delas é:

> *uma busca estruturada abaixo de **100 ms** em p95.*

Medido no box (2026-11-11, imagem `sha-8e30bc93`), o `search_artifacts` por
MCP over HTTP custava **p50 99,64 ms · p95 177,95 ms** numa medição e
**p50 146,92 ms · p95 272,02 ms** noutra. Nenhuma passa.

E o culpado não era o store: o mesmo search, **em processo**, custava
**p50 10,61 ms · p95 16,77 ms**. A diferença — ~90 ms no p50, ~161 ms no p95 —
era o transporte, e dentro do transporte a maior parte era **o payload**.

### 3.2 O payload era a prosa

A página de vinte hits pesava **384 999 bytes**. Desses:

| Fatia | Bytes | % |
|---|---:|---:|
| Os **corpos** da prosa do dono | 365 744 | **95,0 %** |
| Tudo o resto (identidade e metadados) | 8 898 | 2,3 % |

Um ficheiro do vault é a escrita do dono: 15 KB de mediana, 68 KB o maior.
A busca transportava **o vault inteiro** a cada chamada, e pagava-o por
cima do trabalho de serializar o JSON.

### 3.3 Porque isto não é a framework

A repartição medida (mesma máquina, mesma chamada, três medições):

| Camada | p50 | p95 |
|---|---:|---:|
| O store e o serviço, em processo | 10,61 ms | 16,77 ms |
| A serialização do `SearchResult` | 6,37 ms | 39,02 ms |
| O transporte **fixo** (`tools/list`, que não toca o store) | 25,81 ms | 68,21 ms |
| A escrita dos **385 KB** pela streamable-HTTP | ~100 ms | — |

O custo fixo do framework é 25,81 ms — é real, é trabalho sobre ADR-011, e
**não é o que esta ADR resolve**. O payload são ~100 ms: é a prosa do dono a
pagar a fatura de uma busca.

E a curva confirma: com `limit=1` (43 KB) o p95 desce para **76,52 ms** — já
abaixo dos 100 ms. Não era o caminho que estava lento; era o **tamanho**.

### 3.4 Porque o agente não perde nada

O que a busca deixou de trazer, `get_artifact` traz — e já trazia:

- **`get_artifact`** devolve o `Artifact` **com o corpo**, e o corpo é o
  ficheiro do vault tal como está (frontmatter incluído), porque é assim que a
  ingestão o guarda. O `target` de um KPI, o "Done quando" de uma fase e o
  texto de uma revisão continuam a estar lá — a uma chamada de distância.
- **O bot** (`/busca`, o painel do Mini App, a cadência) só lê `uid`, `kind`,
  `title` e `updated_at`. Nenhum deles tocava no corpo.
- **O websocket** transporta `uid`, `op` e `seq`. Não toca no corpo.
- **A skill `store-read`** já dizia, no passo 1: *"Narrow with
  `search_artifacts` before fetching anything"*, e no passo 3: *"Read one
  artifact with `get_artifact`"*. O contrato é que estava desalinhado da
  própria skill — esta ADR alinha-os.

---

## 4. A ponte que já existe

Nada disto precisa de um primitivo novo:

| Peça | Onde | Porque serve |
|---|---|---|
| `get_artifact` | `src/transport/mcp_server.py` | devolve o artefacto **com a prosa**, e as suas arestas; a `depth=0` é a leitura barata |
| `ArtifactBundle` | `src/contracts/dom.py` | `artifact: Artifact` — o corpo faz parte do que se lê |
| `ArtifactSummary` | `src/contracts/dom.py` (novo) | a identidade e os metadados, **herdados** por `Artifact` — os dois não podem divergir |
| `_SUMMARY_COLUMNS` | `src/data/repository.py` (novo) | a lista de colunas da busca: a mesma sem o `body` |
| A skill `store-read` | `specs/harness/skills/store-read/SKILL.md` | já descrevia o padrão "estreitar e depois ler"; agora diz-onde |
| O `store-read` como contrato | `specs/harness/SKILL-SPECS.md` | o mesmo, na fonte canónica |

O que **não** existe e esta ADR não precisa: um endpoint novo, um canal novo,
um protocolo novo, uma migração.

---

## 5. O que está quebrado, com evidência

Tudo medido no box a 2026-11-11 (`hetzner-vpn`, contentor `ikigai-api-1`,
imagem `sha-8e30bc93`), contra o store de produção:

| # | Facto | Como se mediu | Consequência |
|---|---|---|---|
| 1 | A busca por MCP custa **p50 99,64 ms · p95 177,95 ms** | 20 chamadas `tools/call` com `text="projeto"`, `limit=20`, depois de aquecer | o p95 da métrica de 14 dias **falha por 78 ms** |
| 2 | Noutra medição, a mesma chamada deu **p50 146,92 ms · p95 272,02 ms** | a mesma medição, com a caixa a carregar (ingestão a cada 60 s) | a variância é do ambiente, mas **todas** as medições estão acima de 100 ms |
| 3 | O mesmo search **em processo** custa **p50 10,61 ms · p95 16,77 ms** | `build_services().artifacts.search(...)` no mesmo contentor | o store não é o gargalo: **10,6 ms** de um orçamento de 100 ms |
| 4 | O payload da busca são **384 999 bytes** | `len(result.model_dump_json())` sobre os 20 hits | 19 KB por hit, para responder "quais" |
| 5 | **95,0 %** do payload são corpos (365 744 bytes) | soma de `len(a.body)` sobre os 20 hits | sem os corpos o payload é **8 898 bytes** — **43× menos** |
| 6 | O transporte **fixo** custa **25,81 ms** de p50 | `tools/list`, que não toca o store | é um trabalho à parte (ADR-011) e **não** é o que esta ADR resolve |
| 7 | Com `limit=1` (43 KB) o p95 é **76,52 ms** | a mesma chamada com limites 1/5/10/20 | o caminho já passa abaixo de 100 ms com um payload pequeno |

A consequência prática: **a métrica de 14 dias é inalcançável** enquanto a
busca transportar a prosa. A métrica é o critério de sucesso do produto
(ADR-037 §8) — falhá-la não é um detalhe de desempenho.

---

## 6. Inventário, com a razão de cada peça

| # | Peça | Ficheiro | Porque existe |
|---|---|---|---|
| 1 | `ArtifactSummary` | `src/contracts/dom.py` | a identidade e os metadados, **sem** o corpo. Herda o que `Artifact` herda — os dois não podem divergir |
| 2 | `Artifact(ArtifactSummary)` | `src/contracts/dom.py` | o artefacto **com** a prosa: o que uma escrita transporta e o que `get_artifact` devolve |
| 3 | `SearchResult.artifacts: tuple[ArtifactSummary, ...]` | `src/contracts/dom.py` | o tipo do que a busca devolve — e o schema que o agente lê |
| 4 | `_SUMMARY_COLUMNS` | `src/data/repository.py` | as colunas da busca, sem `body` |
| 5 | `_to_summary(row)` | `src/data/repository.py` | a mesma linha, o mesmo artefacto, sem a prosa |
| 6 | `_page` e `_search_semantic` | `src/data/repository.py` | as duas consultas da busca passam a trazer sumários |
| 7 | `test_search_payload.py` | `src/ikigai/tests/contracts/` (novo) | os guards: o sumário sem corpo, o SELECT sem a coluna, a prosa alcançável, o payload independente da prosa, a resposta igual |
| 8 | A skill `store-read` | `specs/harness/skills/store-read/SKILL.md` | diz onde a prosa se lê — e que a busca não a traz |
| 9 | As quatro cadências | `specs/harness/skills/{daily-note,weekly-review,monthly-review,quarterly-plan}/SKILL.md` | cada rotina passa a ler o que vai classificar, em vez de o receber na busca |
| 10 | O contrato canónico | `specs/harness/SKILL-SPECS.md` | o mesmo, na fonte |

**O que não entra:** nenhuma migração (o schema não muda), nenhum endpoint,
nenhuma tool nova, nenhuma mudança no bot, no Mini App ou no websocket.

---

## 7. Dia zero

O que fica verdade quando esta ADR entra:

1. `search_artifacts` devolve `ArtifactSummary` — sem `body`.
2. `get_artifact` continua a devolver o corpo, a `depth=0` e a `depth=1`.
3. O `Artifact` continua a ser o que uma escrita transporta, com o corpo.
4. O store, o schema e as migrations **não mudam**.
5. O bot, o Mini App e o websocket **não mudam** — nenhum deles lia o corpo da
   busca.
6. As skills de leitura e as quatro cadências **são actualizadas** — a rotina
   que lê o que classifica passa a dizê-lo.
7. A métrica de 14 dias fica **alcançável**: o p95 da busca passa de
   ~178 ms para a faixa dos 60–80 ms, que é a da curva medida com o payload
   pequeno (§5, facto 7). **A remedição em produção é o que prova isto** — a
   previsão não é a prova.

---

## 8. Evolução

| Quando | O que muda |
|---|---|
| **Agora** | a busca devolve a identidade; a prosa lê-se à parte |
| **Se os campos tipados passarem a ser lidos com frequência** | a busca passa a trazê-los — e isso é um **join** com as tabelas de extensão, que se mede antes de se decide |
| **Se o `get_artifact` ficar caro demais** | a leitura passa a ter um `depth` novo, ou um endpoint que devolve a prosa de vários artefactos de uma vez — o que muda o número de chamadas, não o tamanho |
| **Se o custo fixo do transporte passar a ser o gargalo** | é uma emenda ao ADR-011, e mede-se à parte: 25,81 ms de p50 com `tools/list` |

Cada uma destas é uma **emenda** a esta ADR, não um redimensionamento: o
invariante central — *a busca identifica, a leitura traz a prosa* — não muda
em nenhuma delas.

---

## 9. Passos com PASS falsificável

| # | Passo | PASS | Como se falsifica |
|---|---|---|---|
| 1 | A busca **não** devolve o corpo | o `ArtifactSummary` não tem o campo `body` | pôr o campo no sumário ⇒ o teste falha |
| 2 | A **coluna** não está no SELECT da busca | as colunas seleccionadas não includem `body` | pôr `body` em `_SUMMARY_COLUMNS` ⇒ o teste falha |
| 3 | A prosa **continua alcançável** | `get_artifact` devolve o `body` | tirar o corpo do read path ⇒ o teste falha |
| 4 | O payload **não cresce com a prosa** | duas páginas de vinte hits, uma com 500 KB de corpo por hit, têm o **mesmo** tamanho | meter o corpo no sumário ⇒ o teste falha |
| 5 | A busca **continua a responder o mesmo** | uid, kind, title, quarter, status, vault_path, revision e body_hash chegam todos | perder um campo do sumário ⇒ o teste falha |
| 6 | As skills **são as do contrato** | `.claude/skills/ikigai-*` é byte a byte a projecção | divergir uma ⇒ o teste falha |

---

## 10. Fora de escopo

| Coisa | Porque fica de fora | O que a reabre |
|---|---|---|
| **Os campos tipados na busca** | estão em tabelas de extensão; juncá-las é um join por chamada, e a busca não os tinha | o agente precisar do `target` sem uma segunda chamada, e a medição mostrar que o join é barato |
| **O custo fixo do transporte MCP** (25,81 ms de p50) | é o ADR-011, não o payload; e 25,81 ms cabem no orçamento de 100 ms | o p95 medido ficar acima de 100 ms **depois** desta ADR |
| **Um `preview` do corpo** | um corpo truncado cita-se como se estivesse inteiro | um contrato que diga explicitamente "isto está truncado" e um agente que o respeite |
| **O `depth=1` do `get_artifact`** | traz os vizinhos **com o corpo inteiro** — é caro por desenho, e é o que o agente quer quando quer o grafo | a medição mostrar que as relações chegam antes do que a prosa |
| **Trocar o `search_artifacts`** | são seis tools (ADR-037 D6) | uma ADR que substitua o D6 |
| **Mudar o store ou o schema** | o `body` continua a estar lá — a muda é **quem o transporta** | nunca, sem outra ADR |

---

## 11. Decisões com default

| # | Decisão | Default | O que a muda |
|---|---|---|---|
| D1 | A busca devolve `ArtifactSummary` — e **não** `Artifact` com `body=None` | sumário | um `body: null` é ambíguo: "sem prosa" ou "não buscada"? O schema não pode responder isso |
| D2 | A prosa lê-se com `get_artifact` | `depth=0` para a prosa, `depth=1` quando o grafo importa | o `get_artifact` ficar caro demais |
| D3 | **Não** há `preview` truncado | sem preview | um contrato que marque o truncamento de forma explícita |
| D4 | **Não** há `include_body` opcional | sem knob | uma knob que alguém liga de facto — e a medição de que o custo é aceitável |
| D5 | A busca **não** passa a trazer os campos tipados | sem tipados | o join das tabelas de extensão ser medido como barato |
| D6 | O `body_hash` **fica** no sumário | fica | nada — é a proveniência da prosa, e é o que o write-back compara |
| D7 | O `Artifact` **herda** o sumário | herança | nada — é o que impede os dois de divergirem |
| D8 | O bot, o Mini App e o websocket **não mudam** | não mudam | um cliente que passe a precisar do corpo da busca |

---

## 12. Camadas de falha

Cada uma falha sozinha, e nenhuma leva as outras:

| Camada | Se falhar | O que se vê |
|---|---|---|
| A skill de leitura | o agente não sabe que a prosa se lê à parte | o relatório cita a identidade e não a prosa — e diz que a prosa não foi lida |
| A rotina | classifica sem ler | a classificação sem evidência; a regra de cada cadência ("uma classificação sem evidência é *não iniciado*") segura o caso |
| O `get_artifact` | a prosa não vem | o agente reporta o que sabe e o que não leu — nunca inventa o corpo |
| A migração de clientes | um cliente antigo espera o corpo na busca | o schema novo não tem `body`: o cliente vê que tem de o pedir |
| O store | não responde | a busca não responde; o contentor fica unhealthy, e é a verdade |

---

## 13. Referências

- [ADR-037](./ADR-037-data-layer-canonical-turn.md) — D6 (as seis tools) e §8 (a métrica de 14 dias: p95 < 100 ms na busca estruturada)
- [ADR-011](./ADR-011-ikigai-mcp-http-sse-transport.md) — o transporte FastMCP sobre HTTP, cujo custo **fixo** (25,81 ms de p50) esta ADR não toca
- [ADR-043](./ADR-043-vault-write-back.md) — o `vault_write`, que lê o `body_hash` do store: o campo que o sumário continua a trazer
- `src/contracts/dom.py` — `ArtifactSummary`, `Artifact`, `SearchResult`
- `src/data/repository.py` — `_SUMMARY_COLUMNS`, `_to_summary`, `_page`
- `src/ikigai/tests/contracts/test_search_payload.py` — os seis guards
- `specs/harness/skills/store-read/SKILL.md` — a leitura, e onde a prosa se lê
- `specs/harness/SKILL-SPECS.md` — o contrato canónico das skills
- `specs/production-readiness/ROADMAP.md` — a métrica de 14 dias e a track **T2** (instrumentá-la sem mão)
