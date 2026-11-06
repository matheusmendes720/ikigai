# ikigai — PRODUCT

**Product id:** `production-readiness`
**Data:** 2026-11-06
**Estado:** medido — a matriz de prontidão abaixo foi apurada por inspecção do código e execução da suite, não por leitura de documentos
**Âncora:** [`ADR-037`](../../code-docs/adr/ADR-037-data-layer-canonical-turn.md) · [`ADR-013`](../../code-docs/adr/ADR-013-canonical-scope-discipline.md)
**Comp camaros:** [`TECH.md`](./TECH.md) (o plano) · [`ROADMAP.md`](./ROADMAP.md) (a árvore e os gates)
**Código:** `e675b438` (main)

> Este documento responde a **o que é o produto e em que estado está**. Não
> contém plano de implementação: esse é o [`TECH.md`](./TECH.md). As invariantes
> aqui numeradas (`B1`…`B10`) são o contrato que o plano tem de satisfazer, e o
> [`ROADMAP.md`](./ROADMAP.md) mapeia cada uma ao gate que a prova.

---

## 1. O produto

**Um sistema operativo pessoal, de uma pessoa só, com um store canónico e um
agente externo.**

O dono tem um vault em prosa (`vault/`, 175 ficheiros) e uma hierarquia
estratégica (`strategics/`, 9 ficheiros em PT-BR). O produto é a machinery que
transforma essa prosa em **artefactos tipados, versionados e consultáveis**, e
que depois os devolve ao dono no momento em que ele precisa deles: no telefone,
a meio do dia, quando a decisão é tomada.

| | |
|---|---|
| **Quem** | uma pessoa (o dono), a sério, todos os dias |
| **Em que momento** | no Telegram, com o telefone na mão, e no `pi` quando o agente precisa de contexto |
| **O que é o valor** | a decisão e a nota são registadas **no momento em que são tomadas**, tipadas, e legíveis depois por máquina |
| **O que é o sucesso** | uma nota escrita do telefone, sem editar ficheiro à mão, e relida pelo agente amanhã — com zero escritas perdidas |
| **O que NÃO é** | um produto com utilizadores, um SaaS, um dashboard, um orquestrador, um grafo de agentes |

**A métrica que decide o formato** (ADR-037 §8, já escrita): uma nota escrita de
um cliente sem editar um ficheiro à mão · zero *lost updates* com dois clientes
ativos · uma busca estruturada abaixo de 100 ms em p95. Catorze dias disso
decidem se esta forma funcionou — **e o interesse é a métrica, não a contagem
de features**.

### 1.1 As quatro regras (o que não se negocia)

| # | Regra | Onde vive |
|---|---|---|
| 1 | **Um writer por store.** Os clientes falam MCP; só `src/services/` escreve. Uma revisão obsoleta é um **409**, nunca uma sobrescrita silenciosa. | ADR-037 D5 |
| 2 | **Um DOM, N projeções.** O modelo é partilhado; cada cliente decide como o desenha. | ADR-037 D2, D8 |
| 3 | **O agente é externo.** O harness é o `pi`; este repositório não constrói framework, grafo nem orquestrador. | ADR-037 D7 |
| 4 | **O store ganha.** Num campo estruturado, o Postgres é canónico e o markdown é a prosa de onde veio. | ADR-037 D4 |

---

## 2. O comportamento que o produto promete

Cada invariante é observável por um utilizador ou por um teste. A coluna
**Estado** é a medição de hoje — não o que se pretende.

| # | Invariante | Estado | Onde se prova |
|---|---|---|---|
| **B1** | Uma nota escrita no Telegram existe no store e é relida pelo `pi` no dia seguinte. | **não provado** — o caminho integrado nunca correu | [ROADMAP G2](../production-readiness/ROADMAP.md) |
| **B2** | Uma escrita nunca se perde: revisão obsoleta produz **409**, e o cliente decide — nunca forçar. | **parcial** — o store faz 409 (`repository.py:158,183`); **o bot nunca chega lá** (`bot/main.py:197` envia sempre `expected_revision: None`) | [TECH §5](../production-readiness/TECH.md) |
| **B3** | A mesma escrita repetida (mesma `idempotency_key`) produz **uma** escrita. | **provado em memória** — `tests/services/test_artifacts_service.py` (20 testes, `FakeRepository`) | — |
| **B4** | O cliente **falha fechado**: sem `IKIGAI_BOT_ALLOWED_CHAT_IDS`, não há bot. | **provado** — `bot/main.py:429-435` + `test_bot_client.py` | — |
| **B5** | O bot nunca abre uma base de dados: fala MCP. | **provado** — zero `psycopg|asyncpg|DSN|cursor(` em `src/bot/`; o compose dá-lhe `IKIGAI_MCP_URL` e **não** um DSN (`compose.yml:74-81`) | — |
| **B6** | O transporte nunca transporta SQL. | **provado** — zero `select|insert|update|delete` em `mcp_server.py`; `test_the_transport_exposes_no_sql` | — |
| **B7** | O healthcheck mede o **plano de dados**, não um socket que devolve bytes. | **provado** — `healthcheck.py:65-86` insere uma linha real e faz `rollback`; `test_store_rls.py:139-176` prova que a inserção falha sob RLS | — |
| **B8** | A prosa entra pelo vault e sai como linhas tipadas. | **não provado** — o `VaultSync` existe (`services/sync.py`, 334 LOC) mas **não está no wiring** (`wiring.py:28-35`), não é tool MCP e não tem CLI | [ROADMAP G1](../production-readiness/ROADMAP.md) |
| **B9** | O grounding estratégico chega ao agente. | **falso hoje** — o loader filtra por tag `strategic` (`loader.py:66`) e **nenhum** dos 9 `strategics/*.md` tem `tags:` no frontmatter ⇒ índice vazio | [TECH §5](../production-readiness/TECH.md) |
| **B10** | A cadência produz o artefacto do seu tipo, com os campos que o tipo exige. | **parcial** — o bot valida contra `KIND_MODELS` antes de escrever (`bot/main.py:223-231`) e pergunta a 2.ª linha quando falta; **a rotina do `pi` nunca correu** | [ROADMAP G3](../production-readiness/ROADMAP.md) |

**Resumo das invariantes: 5 provadas, 3 parciais, 2 não provadas.** As duas que
não estão provadas são exactamente as que fecham o ciclo — e nenhuma delas é
uma feature: são **falta de um ensaio**.

---

## 3. O que existe, medido

Inventário apurado por leitura do código e execução da suite em `e675b438`.

### 3.1 A superfície

| Peça | Estado | Evidência |
|---|---|---|
| **Contratos (DOM)** | **REAL** — 10 kinds, uniões discriminadas, 10 subclasses tipadas + `KIND_MODELS` | `dom.py` 158 LOC · `dom_kinds.py` 127 · `common.py` 92 · `store.py` 62 · `errors.py` 47 |
| **Schema + migrações** | **REAL, nunca aplicadas** — 4 pares up+down (8 ficheiros SQL, 296 linhas) + runner com checksum, *advisory lock* e CLI `up/down/status` | `src/contracts/migrations/` · `apply.py` 166 LOC |
| **Store (pool + repositório)** | **REAL** — pool async `psycopg_pool`, retry com backoff, transacção, create/update optimista ⇒ `ConflictError`, ledger de idempotência, soft delete, FTS português com cursor *keyset*, busca vectorial | `client.py` 222 · `repository.py` 432 |
| **Serviços (regras)** | **REAL** — envelope validado, arestas validadas, travessia *cycle-safe*, cache de embedding | `artifacts.py` 65 · `relations.py` 65 · `embeddings.py` 79 · `wiring.py` 47 |
| **Transporte MCP** | **REAL** — 6 tools delegadas nos serviços, FastMCP (`stdio`/`http`/`sse`), host/porta do ambiente | `mcp_server.py` 286 LOC · 6 `@mcp.tool()` |
| **Cliente Telegram** | **REAL** — 8 comandos de escrita (`/nota /sonho /revisao /plano /onda /fase /desc /okr`) + `/busca` + `/uid`, validação pré-envio contra o modelo do kind, *fail-closed* | `bot/main.py` 445 LOC |
| **Healthcheck** | **REAL** — mede o plano de dados | `healthcheck.py` 136 LOC |
| **Contrato do harness** | **REAL** — `.pi/mcp.json` versionado (HTTP, `/mcp`); 7 skills com **drift test** byte-a-byte | `specs/harness/` · `.pi/mcp.json` |
| **Contentor** | **REAL, nunca construído em CI** — 1 Dockerfile, 1 estágio, 3 papéis pelo comando; migrations no arranque; healthcheck do plano de dados | `deploy/Dockerfile` 77 · `compose.yml` 3 serviços |
| **Rede de guardas** | **REAL e sólida** — 28 ficheiros, 4090 LOC, *append-only*, falsificadas uma a uma | `src/ikigai/tests/` |

**O rácio que diz tudo:** a rede de guardas tem **4090 LOC** e o código de
produto **2844 LOC**. O esqueleto está muito mais vigiado do que está testado
no mundo real.

### 3.2 A matriz de prontidão

Escala 0–5: **0** não existe · **1** existe mas não funciona · **2** funciona
em teoria, nunca foi exercitado · **3** exercitado por unidade, nunca
integrado · **4** integrado e verificado · **5** em produção.

| Componente | Estado | Prontidão | O que o trava |
|---|:-:|:-:|---|
| Contratos (DOM) | real | **4** | `SCHEMA_VERSION = 1` é decorativo (`store.py:36`): há 4 migrações e o ledger real é `ikig.schema_migrations` |
| Schema + migrações | escrito, nunca aplicado | **3** | nunca correram contra uma base viva |
| Pool + repositório | real | **3** | sem Postgres em lado nenhum, o caminho SQL nunca foi percorrido |
| Regras de domínio | real | **3** | testadas contra `FakeRepository`, não contra o store |
| **Embeddings** | **morto** | **1** | `set_embedding` (`repository.py:449`) **não tem caller** ⇒ a coluna fica NULL ⇒ a busca semântica devolve sempre vazio e o índice HNSW está vazio |
| Transporte MCP | real | **4** | **sem autenticação nenhuma**; `client_id` auto-declarado (`mcp_server.py:144`) |
| Cliente Telegram | real | **3** | `expected_revision` sempre `None` ⇒ **só cria**; o cliente MCP não tem timeout nem retry (`main.py:258-261`) |
| Healthcheck | real | **4** | — |
| **VaultSync** | **inalcançável** | **2** | ausente do `Services`, ausente das 6 tools, sem CLI — a skill `vault-sync` manda executar uma ingestão que não tem porta de entrada |
| **Loader de strategics** | **vazio no corpus real** | **1** | o filtro exige tag `strategic`; nenhum dos 9 ficheiros tem `tags:` ⇒ índice vazio. Os 8 testes usam fixtures **inventadas** |
| Skills do harness | real | **4** | a projecção é mantida por drift test; **nenhuma rotina correu** |
| Contentor + compose | real | **3** | nunca construído no CI; corre como **root**; `curl` instalado e não usado |
| CI | parcial | **3** | 5 portões de pacote + revisão pré-merge, mas **sem Docker e sem Postgres** ⇒ os 14 testes do store saltam em toda a execução |
| Entrega ao VPS | não reproduzível | **1** | `scripts/` é gitignored ⇒ `deploy-vps.sh` **não existe num clone**; sem rollback; sem injecção de segredos |
| **e2e** | **não existe** | **0** | `-m "not e2e"` não exclui nada: nenhum ficheiro versionado usa o marcador `e2e`; o único candidato está gitignored |
| Rede de guardas | real | **5** | — |

### 3.3 O que a suite prova — e o que não prova

`150 passed, 14 skipped` em `e675b438`.

Os **14 skipped** são exactamente os testes que tocam o store real
(`test_store_bench` 4, `test_store_concurrency` 2, `test_store_relations` 2,
`test_store_rls` 6) — saltam porque não há Docker nesta máquina **nem serviço
Postgres no CI**. Os 12 testes de `test_store_schema.py` passam porque leem o
SQL **como texto** e o comparam com os contratos: provam que o ficheiro diz a
certa coisa, **não** que o Postgres a aceita.

**Consequência directa:** o contrato "escrevo hoje e releio amanhã" **nunca foi
demonstrado contra um Postgres real**, em nenhum sítio, por ninguém.

---

## 4. A distância até produção diária

O que falta, do mais bloqueante ao menos:

| # | Falta | Distância | Custo |
|---|---|---|---|
| **1** | **O store nunca correu.** Sem Docker local, sem Postgres no CI, as migrações nunca foram aplicadas. | **um dia** — o trabalho está escrito; falta executá-lo | instanciar o stack no CI e correr os 14 testes |
| **2** | **O vault nunca é ingerido.** O `VaultSync` está implementado e é inalcançável. | **meio dia** — ligar ao wiring + uma tool MCP + o gate | pequena |
| **3** | **O grounding estratégico está vazio.** O loader devolve índice vazio para o corpus real. | **meio dia** — frontmatter nos 9 ficheiros + um teste que aponte para o corpus real | pequena |
| **4** | **O bot só cria.** Editar duplica; o 409 é inalcançável do cliente; o contrato de conflito — a promessa central do ADR-037 D5 — nunca é exercitado por um cliente real. | **um dia** — ler a revisão actual antes de escrever + derivar o uid de forma estável | média |
| **5** | **Não há e2e.** Nada liga Telegram → `/mcp` → Postgres → releitura pelo `pi`. | **um dia** — com o stack a correr, é um teste | média |
| **6** | **A entrega não é reproduzível.** O script de deploy não está no branch; sem rollback; sem segredos automáticos. | **um dia** | média |
| **7** | **O MCP não tem autenticação e o `client_id` é auto-declarado.** Decisão do dono (2026-11-06): *single-player real* — o RLS sai do caminho crítico. | **horas** — reduzir o promessa, não a cumprir | pequena |
| **8** | **A busca semântica é uma mentira.** Decisão do dono (2026-11-06): sai do contrato v1 até haver provider. | **horas** — tirar `embed_text` e `semantic: true` | pequena |

**Veredicto de distância: o produto está a ~60% do caminho do "uso diário".**
O que falta **não são features** — são três ensaios (stack, ingestão, e2e) e
quatro correcções de contrato (bot revisa, semântica fora, grounding, entrega).
Nenhuma exige arquitectura nova.

**O que está a 100% e não está no caminho crítico:** o contentor, o healthcheck,
o transporte, os contratos, a rede de guardas. O esqueleto está bom; o que
falta é **pôr a correr**.

---

## 5. As fronteiras

**Não é o produto:**

- um produto multi-utilizador — o `client_id` é `owner` e é auto-declarado (decisão 2026-11-06)
- uma plataforma de plugins — o `pi` é externo e não está neste repositório
- um dashboard — não há frontend; o Telegram é a superfície
- a camada algorítmica — PAV, *hysteresis*, scoring: adiada por ADR-037 D1, e o
  repo não publica kernel nenhum
- um orquestrador — sem LangGraph, sem SDK de modelo, sem grafo de agentes
- o `vault/` como fonte canónica — é a **prosa de entrada**; o store é canónico

**O que este repositório não faz, por desenho:** não apaga conteúdo. O corte de
âmbito (2026-11-05) despublicou 490 caminhos e **não apagou um ficheiro** — ficam
no disco do dono e no histórico (ADR-037 §"publicação independente").

---

## 6. Decisões fechadas nesta peça

| # | Decisão | Efeito | Onde |
|---|---|---|---|
| D1 | **RLS sai do caminho crítico.** Single-player real: um `client_id`, sem `force row level security`, sem `set_config`, sem `client_id` no token. | O `0003_rls.sql` deixa de ser uma promessa que não se cumpre; a atenção vai para o store. | [TECH §11](../production-readiness/TECH.md) |
| D2 | **A semântica sai do contrato v1.** `embed_text` e `semantic: true` saem até haver provider real; o hashing-trick fica interno. | O MCP passa a ter 5 tools honestas; o índice HNSW fica para quando houver provider. | [TECH §11](../production-readiness/TECH.md) |
| D3 | **O bot revisa.** Lê a revisão actual antes de escrever; editar deixa de duplicar. | O 409 passa a existir do lado do cliente e a invariante B2 fica completa. | [TECH §11](../production-readiness/TECH.md) |
| D4 | **O stack corre primeiro no CI.** O GitHub Actions tem Docker: constrói a imagem, sobe o compose, aplica as migrações e corre os 14 testes do store em cada PR. | O store deixa de ser código não exercitado, e a correcção de D1–D3 tem um lugar onde se prova. | [TECH §7](../production-readiness/TECH.md) |

---

## 7. Escopo futuro: as progressões naturais

As decisões de §6 fecham o **plano de hoje**. As alternativas que foram
deixadas de fora não são erros a corrigir — são **o degrau seguinte** de cada
uma. Este registo diz o que são, **o gatilho que as activa** e o que custam,
para que a decisão não se perca e ninguém a refaça do zero quando chegar a
hora.

> Nada nesta secção é compromisso. É o mapa do que fica **depois** do dia zero,
> na ordem natural em que a maturidade do produto cresce.

### 7.1 As alternativas às decisões de hoje

| # | A decisão de hoje | A alternativa | **Gatilho** — o que tem de ser verdade para a alternativa entrar | Custo |
|---|---|---|---|---|
| **D1** | RLS fora do caminho crítico | **Activar o RLS a sério** (`force row level security` + `set_config` por transação + role de aplicação separado do dono) | existir **dois `client_id` distintos** a falar com o mesmo store — ou seja: um segundo dispositivo, um segundo cliente, ou o `pi` com identidade própria | 1 dia (o SQL e o teste já existem) |
| **D1** | — | **RLS + token no MCP** (autenticação por token, claim por sessão) | o transporte deixar de ser loopback — reverse proxy, túnel exposto, ou um terceiro a falar com o store | 2 dias |
| **D2** | semântica fora do contrato v1 | **Provider real de embeddings** (API, chave, custo por escrita) | **duas condições, ambas**: (i) o caminho cloud native validado (G1–G5 + a métrica de 14 dias), e (ii) o corpus passar do que a FTS portuguesa resolve — medido, não sentido: **≥ 5 000 artefactos** e a busca por sinónimos a falhar | 1 dia + custo por escrita |
| **D2** | — | **Embeddings locais** (`sentence-transformers` em CPU) | o VPS ter CPU sobrando e o custo por API doer ou a latência de escrita unacceptable | 2 dias + ~500 MB de imagem |
| **D3** | o bot revisa (lê a revisão antes de escrever) | **Telegram append-only**: cada mensagem é um artefacto e editar é operação à parte | o dono decidir que o *log* de mensagens é a verdade e a revisão é ruído | 0 (é o estado actual) |
| **D3** | — | **Edição inline no Telegram** mapeada para `upsert` com revisão | o dono **editar de facto** notas no Telegram — sinal: duplicados a aparecerem apesar de D3 | 1 dia |
| **D3** | — | **Comandos de operação** no bot: `/supersede`, `/undo`, `/revisar` | o conflito (409) passar a acontecer na prática — hoje não há ninguém a colidir | 1 dia |
| **D4** | o stack corre primeiro no CI | **Docker Desktop na máquina do dono** | o ciclo de *feedback* do CI (minutos) deixar de ser rápido o suficiente para iterar no código do store | 1 dia de instalação |
| **D4** | — | **O VPS como primeiro runner**, com o CI a validar antes | o CI estar lento *e* o dono precisar do ambiente real para debugging de rede/volume | — |

### 7.2 As tracks que a maturidade abre

Cada track tem uma **precondição** — e a precondição é quase sempre uma das
invariantes de §2 ficar provada. A ordem não é estética: é de dependência.

| Track | O que é | **Precondição** | Custo |
|---|---|---|---|
| **T1 · Backup do store** | dump automático do volume `db-data`, retenção e **reposição testada** | o store ter corrido com dados reais por uma semana | 1 dia |
| **T2 · Instrumentação da métrica** | medir a métrica de 14 dias (p95 de busca, writes por cliente) sem tocar à mão | T1 — medir dados que se podem perder é mentira | 2 dias |
| **T3 · Multi-dispositivo** | o telefone e o `pi` com `client_id` distintos → **B2 passa a ter dois clientes a colidir** | D1 (RLS) — sem isolamento, multi-dispositivo é multi-escrita sem dono | 2 dias |
| **T4 · Embeddings reais** | provider de embeddings de verdade: a coluna passa a ser escrita, a busca semântica passa a existir e o `semantic: true` volta ao contrato | **o caminho cloud native validado** (G1–G5 + métrica de 14 dias) **e** o corpus a justificar (≥ 5 000 artefactos, busca por sinónimos a falhar). É a track que o dono sinalizou como interesante — e a ordem é deliberada: **depois** de o sistema estar vivo, não antes | 1 dia + custo por escrita |
| **T5 · `vault_write` (ADR-012)** | escrever de volta no vault é hoje proibido; a tool que o faz é o outro cliente real da service layer | B8 provado — a ingestão tem de estar fiável antes de escrever | 2 dias |
| **T6 · Skills de engenharia** | `contract-change-drift-test`, `ci-green-gate`, `release-deploy` existem só em `SKILL-SPECS.md`, sem projecção | o repo estabilizar — uma skill de engenharia sobre um repo instável é ruído | 1 dia |
| **T7 · Projecções** | TUI, depois web — o DOM já é N projeções (ADR-037 D2) | o DOM estar estável o suficiente para uma segunda leitura | 3+ dias |
| **T8 · Timeline** | deixa de ser "o artefacto que falta" e vira uma *view* sobre o DOM (ADR-037 §7) | haver histórico suficiente para uma view valer | 3 dias |
| **T9 · A camada algorítmica** | PAV kernel, *hysteresis* FSM, scoring — **adiada por ADR-037 D1** | a **métrica de 14 dias** estar medida e o store a ter dados reais | dias |
| **T10 · `life vault-note`** (SPEC-02 do Vanilla Pivot) | o primeiro cliente da service layer que não é o Telegram | B8 e D3 | 1 dia |

**A ordem natural**: `G1` (store) → `G2` (conteúdo) → `G3`/`G4` (harness,
Telegram) → `G5` (entrega) → **métrica de 14 dias** → e só então `T1`…`T10`.
Dentro das tracks: **`T4` (embeddings reais) vem depois de `T3`**, porque é a
primeira track que **custa dinheiro por uso** e a primeira que toca no caminho
de escrita — e um caminho de escrita só se mexe depois de o sistema estar vivo
e medido. A camada algorítmica (T9) é a última de todas, e ADR-037 D1 diz
porquê: um kernel de scoring sem dados reais é uma máquina que produz ruído
com confiança.

---

## 8. Como se sabe que está feito

**A métrica de 14 dias** (ADR-037 §8), que decide se esta forma funcionou:

1. uma nota escrita de um cliente **sem editar um ficheiro à mão** — e relida pelo `pi`
2. **zero lost updates** com dois clientes activos
3. uma busca estruturada abaixo de **100 ms** em p95

**Antes da métrica, os gates técnicos** — cada um com um PASS falsificável, no
[`ROADMAP.md`](./ROADMAP.md):

| Gate | O que prova | PASS |
|---|---|---|
| **G1 · store** | o Postgres real aceita o schema e o repo | os 14 testes do store **passam** (hoje saltam) no CI |
| **G2 · conteúdo** | a prosa entra e o grounding chega | o store tem linhas do `vault/`; o índice estratégico não está vazio |
| **G3 · harness** | o `pi` corre uma rotina | o `pi` chama uma tool e o store devolve o artefacto do tipo certo |
| **G4 · telegram** | o dono escreve do telefone | a nota do Telegram é relida pelo `pi` com a revisão certa |
| **G5 · entrega** | um clone vira um serviço | `git clone` → `docker compose up` → healthcheck verde, sem mão |

---

*PRODUCT.md — 2026-11-06 — medido em `e675b438`. Actualizar no mesmo PR em que
mude o estado de qualquer componente desta matriz, ou em que uma invariante
mude de "parcial" para "provada".*
