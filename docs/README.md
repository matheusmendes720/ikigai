# Docs — Algorithmic Life OS

> **Camada de dados primeiro.** A virada canônica de 2026-11-01 (ADR-037)
> substituiu o foco em interfaces por uma **camada de dados**: um único DOM,
> um único Postgres, services que são os únicos writers, um transporte MCP
> over HTTP, e clientes que são projeções do DOM. O harness é o `pi` — e é
> **externo**: esta repo não constrói agent framework, grafo custom,
> checkpoint ou memory layer.
>
> O escopo foi renovado em 2026-11-02: a branch **é** o serviço.

---

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
docs/            este wiki — incluindo o diagnóstico que produziu esta forma
```

O **README da raiz** é a porta de entrada: as quatro regras, como rodar, os
seis tools, e o que **não** está aqui.

## As quatro regras

| # | Regra | Onde |
|---|---|---|
| 1 | **Um writer por store.** Clientes falam MCP; só `src/services/` escreve. Revisão obsoleta é **409**, nunca sobrescrita silenciosa. | ADR-037 D5 |
| 2 | **Um DOM, N projeções.** O modelo é compartilhado; cada cliente decide como renderizar. | ADR-037 D2, D8 |
| 3 | **O agente é externo.** O harness é o `pi`; esta repo não constrói framework, grafo nem orquestrador. | ADR-037 D7 |
| 4 | **O store vence.** Em campo estruturado, Postgres é canônico e o markdown é a prosa de onde ele veio. | ADR-037 D4 |

## O que NÃO está aqui — e por quê

O sistema pré-ADR-037 — o harness langchain/langgraph, o CLI do operador, a
malha de forks, o motor cybernético, a suite de testes da raiz — é
**não publicado, não deletado**. Os ficheiros ficam no disco do dono e no
histórico do git; não estão nesta branch. A cláusula é ADR-037
§"publicação independente".

Os algoritmos estão **adiados** (ADR-037 D1): sem kernel PAV, sem FSM de
histerese, sem scoring na árvore publicada. Vêm por último, e precisam de
dados reais para valerem algo.

Uma consequência prática: `docs/` guarda o **registro**, não a arquitetura
corrente. Documentos datados que descrevem o sistema anterior continuam
aqui de propósito — são a história das decisões. O que é **canônico** está
listado abaixo.

## Canônico

- **A decisão:** [ADR-037 — Virada Canônica: camada de dados primeiro](../code-docs/adr/ADR-037-data-layer-canonical-turn.md)
- **A série de specs:** [docs/superpowers/specs/2026-11-01-00-data-layer-series.md](superpowers/specs/2026-11-01-00-data-layer-series.md) · [01 DOM](superpowers/specs/2026-11-01-01-unified-dom.md) · [02 Store](superpowers/specs/2026-11-01-02-cloud-store.md) · [03 Service+Transporte](superpowers/specs/2026-11-01-03-service-transport-pi.md)
- **O plano de implementação:** [specs/data-layer/TECH.md](../specs/data-layer/TECH.md)
- **O corte:** [superpowers/specs/2026-10-30-05-cut.md](superpowers/specs/2026-10-30-05-cut.md) — o que foi removido da branch, e por quê
- **O relatório que precede a virada:** [vanilla-pivot.html](vanilla-pivot.html) (2026-10-30)

## O registro (datado, preservado)

- [`docs/superpowers/`](superpowers/) — specs formais, planos de implementação, glossários
- [`docs/diagnostics/`](diagnostics/) — auditorias e migrações (structure-audit, doc-migration)
- [`docs/design-system/`](design-system/) — topologia, canvases de arquitetura, patterns, tokens
- [`code-docs/adr/`](</../code-docs/adr/>) — as ADRs, com o raciocínio que eliminou as alternativas
- [`vault/`](</../vault/>) — a prosa: ciclos de planejamento, decisões, metas

## Modo atual

A força vai para a camada de dados, nesta ordem: DOM · store · services +
transporte · harness · clientes. **Não** iniciar produto novo (Telegram,
timeline, TUI) antes da fase 3 verde.

O gate é a métrica de 14 dias do ADR-037 §8: uma nota escrita sem editar
arquivo à mão, de cliente não-desktop; zero lost update com dois clientes
ativos; busca estruturada com p95 < 100ms.

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
| Agente implementando a camada de dados | [ADR-037](../code-docs/adr/ADR-037-data-layer-canonical-turn.md) → [série 2026-11-01](superpowers/specs/2026-11-01-00-data-layer-series.md) → [TECH.md](../specs/data-layer/TECH.md) |
| Agente implementando um feature | `src/contracts/` + a ADR relevante — **e confira a ordem em ADR-037 §3 D1 antes de aceitar** |
| Agente auditando o scope | `src/ikigai/tests/test_canonical_scope.py` + `test_drift_invariants.py` — a rede de drift é a especificação |
| Humano querendo entender o sistema | o [README da raiz](</../README.md>) |
| Humano querendo usar | `src/bot/main.py` — o cliente Telegram; e `deploy/README.md` para o container |

---

*Docs — raiz da wiki. O índice completo por sub-árvore vive em
[`docs/design-system/`](design-system/).*
