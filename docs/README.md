# Docs — Algorithmic Life OS

> **Camada de dados primeiro.** A virada canônica de 2026-11-01 (ADR-037)
> substituiu o foco em interfaces por uma **camada de dados**: um único DOM,
> um único Postgres, services que são os únicos writers, um transporte MCP
> over HTTP, e clientes que são projeções do DOM. O harness é o `pi` — e é
> **externo**: esta repo não constrói agent framework, grafo custom,
> checkpoint ou memory layer.
>
> O escopo foi renovado em 2026-11-02: a branch **é** o serviço.

> **Aviso de leitura.** Este directório guarda **duas coisas diferentes**, e
> elas não se confundem:
>
> - **O mapa canónico** (primeiro) — o que o sistema **é** hoje.
> - **O registo datado** (mais abaixo) — documentos com data, que descrevem
>   o sistema **anterior**. Uma decisão que cita o que eliminou é história,
>   não arquitectura. Nada ali descreve o que corre hoje.
>
> Se estás a ler para saber **como o sistema funciona**, para no mapa
> canónico. Se estás a ler para saber **como chegámos aqui**, o registo é
> o lugar certo — datado e preservado de propósito.

---

## O mapa canónico

| Precisas de… | Vai aqui |
|---|---|
| o que o produto é, em 60 segundos | o [README da raiz](</../README.md>) |
| a decisão que produziu esta forma | [ADR-037 — Virada Canônica](</../code-docs/adr/ADR-037-data-layer-canonical-turn.md>) |
| o que um agente pode e não pode fazer | [ADR-013 — disciplina de scope](</../code-docs/adr/ADR-013-canonical-scope-discipline.md>) |
| como o harness encontra prompt, skill e cadência | [specs/harness/router.md](</../specs/harness/router.md>) |
| os prompts por papel | [specs/harness/SYSTEM-PROMPTS.md](</../specs/harness/SYSTEM-PROMPTS.md>) |
| o contrato de cada skill | [specs/harness/SKILL-SPECS.md](</../specs/harness/SKILL-SPECS.md>) |
| a projecção das skills | [specs/harness/skills/](</../specs/harness/skills/>) |
| o modelo de dados e o SQL | [src/contracts/](</../src/contracts/>) · [specs/data-layer/TECH.md](</../specs/data-layer/TECH.md>) |
| a especificação da série da camada de dados | [00 — a série](superpowers/specs/2026-11-01-00-data-layer-series.md) · [01 DOM](superpowers/specs/2026-11-01-01-unified-dom.md) · [02 Store](superpowers/specs/2026-11-01-02-cloud-store.md) · [03 Service + Transporte](superpowers/specs/2026-11-01-03-service-transport-pi.md) |
| o que foi removido da branch, e porquê | [o corte](superpowers/specs/2026-10-30-05-cut.md) |
| o que corre, e o que está adiado | o [README da raiz](</../README.md>) · [estado do jogo](</../README.md#the-state-of-play) |

## O que esta branch publica

```text
src/contracts/   o DOM — um modelo, tipagem forte (Pydantic v2, frozen)
src/data/        o cliente do store — Postgres em pool, retries, transações
src/services/    as regras de domínio — o ÚNICO writer do store
src/transport/   o transporte MCP over HTTP, e o healthcheck
src/bot/         o cliente Telegram — uma projeção do DOM
src/ikigai/      o pacote Poetry: o loader de strategics + a suite canônica
vault/           a prosa (markdown). INPUT do store.
strategics/      o material estratégico PT-BR. Somente leitura.
deploy/          o container: Dockerfile + compose + o contrato de ambiente
specs/           as specs do harness e da série da camada de dados
code-docs/adr/   as decisões, com o raciocínio que eliminou o resto
docs/            este wiki — o mapa canônico e o registo
```

O **README da raiz** é a porta de entrada: as quatro regras, como rodar, os
seis tools, as skills, e o que **não** está aqui.

## As quatro regras

| # | Regra | Onde |
|---|---|---|
| 1 | **Um writer por store.** Clientes falam MCP; só `src/services/` escreve. Revisão obsoleta é **409**, nunca sobrescrita silenciosa. | ADR-037 D5 |
| 2 | **Um DOM, N projeções.** O modelo é compartilhado; cada cliente decide como renderizar. | ADR-037 D2, D8 |
| 3 | **O agente é externo.** O harness é o `pi`; esta repo não constrói framework, grafo nem orquestrador. | ADR-037 D7 |
| 4 | **O store vence.** Em campo estruturado, Postgres é canônico e o markdown é a prosa de onde ele veio. | ADR-037 D4 |

## O que NÃO está aqui — e porquê

O sistema pré-ADR-037 — o harness langchain/langgraph, o CLI do operador, a
malha de forks, o motor cybernético, a suite de testes da raiz — é
**não publicado, não deletado**. Os ficheiros ficam no disco do dono e no
histórico do git; não estão nesta branch. A cláusula é ADR-037
§"publicação independente".

Os algoritmos estão **adiados** (ADR-037 D1): sem kernel PAV, sem FSM de
histerese, sem scoring na árvore publicada. Vêm por último, e precisam de
dados reais para valerem algo.

---

# O registo (datado, preservado)

> ⚠️ **Isto é arquivo.** Cada documento abaixo descreve um sistema que **não
> está publicado nesta branch**. Estão aqui porque explicam **como as
> decisões foram tomadas** — e uma decisão sem o que eliminou não se
> avalia. Para saber como o sistema funciona hoje, volta ao mapa canónico.

- [`docs/superpowers/`](superpowers/) — specs formais, planos de implementação, glossários
- [`docs/diagnostics/`](diagnostics/) — auditorias e migrações (structure-audit, doc-migration)
- [`docs/design-system/`](design-system/) — topologia, canvases de arquitetura, patterns, tokens
- [`docs/2026-09-29-langgraph-dev-studio-e2e.md`](2026-09-29-langgraph-dev-studio-e2e.md) — o harness antigo, em e2e
- [`docs/PAV_INVENTORY.md`](PAV_INVENTORY.md) — o inventário do kernel adiado
- [`code-docs/adr/`](</../code-docs/adr/>) — as ADRs, com o raciocínio que eliminou as alternativas
- [`vault/`](</../vault/>) — a prosa: ciclos de planejamento, decisões, metas
- [`vanilla-pivot.html`](vanilla-pivot.html) — o relatório que precede a virada (2026-10-30)

## Modo atual

A ordem do trabalho não mudou com o pivot, mas **o que está em frente mudou**:
o cliente Telegram deixou de ser "produto novo a não iniciar" e passou a ser
**a superfície do produto** — é por ele que o dono escreve uma nota sem
editar ficheiro à mão.

```text
DOM · store · services + transporte · harness · clientes
                                        ▲           ▲
                          o pi carrega as skills   o Telegram é o cliente
```

O gate continua a ser o mesmo — a métrica de 14 dias do ADR-037 §8: uma nota
escrita sem editar arquivo à mão, de cliente não-desktop; zero lost update
com dois clientes ativos; busca estruturada com p95 < 100ms.

## GitHub

| Recurso | URL |
|----------|-----|
| Repositório | https://github.com/matheusmendes720/ikigai |
| Project Board | https://github.com/users/matheusmendes720/projects/5 |
| Issues | https://github.com/matheusmendes720/ikigai/issues |
| CI/CD | `.github/workflows/ci.yml` — ruff, mypy, pytest |

## Entrada por persona

| Persona | Comece aqui |
|---|---|
| Agente implementando a camada de dados | [ADR-037](</../code-docs/adr/ADR-037-data-layer-canonical-turn.md>) → [série 2026-11-01](superpowers/specs/2026-11-01-00-data-layer-series.md) → [TECH.md](</../specs/data-layer/TECH.md>) |
| Agente implementando um feature | `src/contracts/` + a ADR relevante — **e confira a ordem em ADR-037 §3 D1 antes de aceitar** |
| Agente construindo uma skill | [specs/harness/SKILL-SPECS.md](</../specs/harness/SKILL-SPECS.md>) → a projecção em [specs/harness/skills/](</../specs/harness/skills/>) |
| Agente auditando o scope | `src/ikigai/tests/test_canonical_scope.py` + `test_drift_invariants.py` — a rede de drift é a especificação |
| Humano querendo entender o sistema | o [README da raiz](</../README.md>) |
| Humano querendo usar | `/nota` · `/sonho` · `/busca` · `/uid` no Telegram; e `deploy/README.md` para o container |

---

*Docs — raiz da wiki. O índice completo por sub-árvore vive em
[`docs/design-system/`](design-system/).*
