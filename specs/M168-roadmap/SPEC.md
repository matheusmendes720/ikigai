# M168 — Roadmap personalizado: horizonte A/B/C do Q4 fresh start

**Status:** 🟡 PLANNED (roadmap, não execução)
**Date:** 2026-09-29
**Author:** loop-orchestrator + user
**Builds on:** M154-AUDIT (inventário v2), M155 (deep agent spec),
              M156 (stubs PAV), M157 (fix import), M158 (td chat REPL)
**Goal:** Visão completa de tudo que falta pro objetivo da sessão
("v2 completamente funcional via studio chat + todas as feats do
taskdog integradas"), em horizontes A (essencial), B (estendido),
C (visionário), com versão simplificada B (TUI nativa + deep agents)
como caminho de execução até estarmos prontos pra saltos maiores.

---

## TL;DR

| Horizonte | O que é | LOC | Tempo | Entrega |
|---|---|---|---|---|
| **A — Essencial** | TUI completa do taskdog upstream adaptada ao fork | ~3.700 | 5-7 sessões | `td` com 22 subcomandos do upstream, schema expandido, TUI live |
| **B — Estendido** | Deep agent completo + skills + cache + studio | ~1.500 | 1-2 sessões | `td chat` rico, skills automáticas, Studio UI |
| **C — Visionário** | Recursive reflection, cross-session memory, multi-agent | ~? | várias semanas | ainda não especificado |

**Versão simplificada que estamos seguindo AGORA (caminho de execução):**

1. Continuar de onde paramos (M159 → M162 da Fase B)
2. Quando B estiver confiável, **migrar pra A simplificado** (M163-M165):
   schema migration + subcomandos essenciais + TUI reescrita
3. Só então dar "saltos maiores" (A completo com gantt/optimize, ou C)

---

## Estado atual (verificado 2026-09-29)

### O que JÁ funciona
- `td list`, `td show`, `td status`, `td timeline`, `td tui` (M151, M153)
- `td add`, `td done`, `td update`, `td propagate` (M151, write path)
- 12 taskdog tools via MCP bridge (M148)
- v2 graph compila e executa end-to-end (M154)
- 14 prompts PAV stubificados (M156, ADR-013)
- `langchain_anthropic` quebrado não crasha mais (M157)
- `td chat` REPL funcional com v2 deep agent (M158)
- 33/33 testes (6 m158 + 17 m151 + 10 v2 prompts)

### O que está PARTIDO / em falta
- DB schema só tem 8 colunas (faltam tags, deps, audit_log, started_at, completed_at)
- `td` tem 9 subcomandos (faltam 13+ do upstream: tag, dep, note, pause/reopen/cancel, rm/restore, audit, db backup/restore, export, stats, fix-times, gantt, optimize)
- `td tui` é one-shot dashboard (não tem panels live, gantt, timeline interativo)
- Deep agent é REPL (não Studio UI)
- Vault embeddings cache não existe (recall_node re-embedda)
- Skills `taskdog-triage` e `vault-intent-extract` não implementadas
- Skills `daily/weekly/monthly/quarterly` ainda chamam PAV stubs (não substituídos por agregação real)

---

## Horizonte A — TUI completa do taskdog upstream

**Quando entramos:** depois que B (deep agent simplificado) estiver confiável.

**Por que:** sem TUI sólida, o deep agent não tem superfície de uso prático.

**Sub-horizontes:**

### A.1 — Schema migration (M163, ~300 LOC, 1 sessão)
- Adicionar colunas: `tags` (JSON array), `deps` (JSON array), `audit_log` (JSON),
  `started_at`, `completed_at`, `priority_label` (P0/P1/P2 textual)
- Migration script com backup automático
- Tests: old data preservado, new data tem colunas

### A.2 — Subcomandos essenciais (M164, ~700 LOC, 1 sessão)
- `td tag add/remove/list/clear <ueid> [tag1 tag2 ...]`
- `td dep add/remove/list/blocked <ueid> [other_ueid]`
- `td note add/show <ueid> [text]`
- `td pause/reopen/cancel <ueid>` (status transitions)
- Tests: cada subcomando + edge cases (dep cycle detection, tag validation)

### A.3 — TUI live reescrita (M165, ~500 LOC, 1 sessão)
- `td tui --mode=dashboard|timeline|gantt` (3 modes)
- Layout: header (counts) + 2 panels (tasks list + gantt timeline)
- Keys: `q` quit, `r` refresh, `tab` switch mode, `+` add, `d` done
- Tests: render correctness, key handling, refresh loop

### A.4 — Subcomandos avançados (M166, ~700 LOC, 1-2 sessões)
- `td rm/restore <ueid>` (soft-delete com audit trail)
- `td audit [ueid]` (history de mudanças)
- `td db backup/restore [path]` (SQLite backup)
- `td export [json|csv]` (export tasks)
- `td stats` (completion rate, avg time, by-tag breakdown)
- `td fix-times` (corrigir timestamps de tasks antigas)
- Tests: cada um

### A.5 — Gantt + optimize (M167, alto risco, 1-2 sessões)
- `td gantt` (ASCII gantt com base nas deps)
- `td optimize` (sugerir reordenação de priorities baseado em deps)
- Tests: algoritmo correto, output format

**Total A:** ~3.700 LOC, 5-7 sessões

**Quando parar A:** quando `td --help` mostrar 22+ subcomandos e
`td tui` tiver 3 modes funcionando.

---

## Horizonte B — Deep agent completo (estamos AQUI)

**Sub-horizontes restantes:**

### B.4 — Vault embeddings cache (M159, ~100 LOC, esta sessão)
- `src/ikigai/src/agents/v2/vault_cache.py` (ChromaDB PersistentClient)
- `get_or_compute(file_path)` com mtime invalidation
- Wired em `recall_node`
- Tests: cache hit > 80% em workload típico, mtime change re-indexa

### B.5 — 2 skills novos (M161, ~400 LOC, próxima sessão)
- `taskdog-triage` (cron 09:00): lê vault + taskdog, propõe (NUNCA executa)
  - Detecta: deadline < 48h, overdue, sem descrição
  - Output: Proposal com mudanças via meta_plan pattern
- `vault-intent-extract` (cron 22:00): lê `vault/daily/{date}.md`
  - Regex + LLM: "amanhã eu faço X" → task candidate
  - Output: Proposal com tasks via review queue
- Tests: cada skill roda end-to-end, proposta emitida, approval gate

### B.6 — Adaptação cadência (M162, ~300 LOC, próxima sessão)
- `ikigai-daily` (08:57): substitui PAV por agregação (counts done/pending/cancelled)
- `ikigai-weekly` (segunda 09:00): agrega 7 daily reports
- `ikigai-monthly` (dia 1 10:00): agrega 4 weekly
- `ikigai-quarterly` (jan/abr/jul/out dia 1 11:00): agrega 3 monthly + 13 weekly
- Output: vault/weekly-review/{date}.md, monthly-review, quarterly-review
- Approval: meta_plan pattern (vault_write ANTES de modificar, DEPOIS de executar)
- Tests: cada skill roda, vault entry criado, review queue populado

**Total B (restante):** ~800 LOC, 2-3 sessões

**Quando parar B:** quando as 7 skills (5 adaptados + 2 novos) rodarem
diariamente sem erro e você conseguir usar `td chat` pra conversar sobre
planejamento de forma útil.

### B.7 — Studio UI (opcional, integrado em B ou C)
- Resolver CORS: tunnel cloudflared com URL capturada
- Langgraph dev já tem `ikigai_maintainer_v2` registrado
- Studio UI conecta via tunnel URL
- Tempo: 1-2 dias se cloudflared cooperar, 0 LOC se desistir

---

## Horizonte C — Visionário (ainda não especificado)

Ideias pra C (não escopadas, são exemplos):

- **Recursive reflection** — agent revisa próprias decisões, ajusta
- **Cross-session memory** — agent lembra de conversas passadas com você
- **Multi-agent collaboration** — subagents paralelos (planning + research + execution)
- **Vault como single source** — escrita 100% no vault, taskdog é só cache
- **Voice interface** — `td chat` aceita input de voz
- **Web UI** — Dashboard HTML5 servido pelo langgraph dev (substitui TUI)

**Quando entrar em C:** quando A e B estiverem sólidos, **você** vai
sentir falta dessas features. Aí especificamos C com calma.

---

## Versão simplificada (CAMINHO DE EXECUÇÃO AGORA)

Você escolheu: **continuar de onde paramos (deep agents) + quando
confiável, migrar pra TUI completa (A) aos poucos**.

**Sequência:**

```
M159 (vault cache)        — esta sessão, 30min
M160 (cancelado)          — td tui NÃO vira console de agent
M161 (skills novos)       — próxima sessão, ~400 LOC
M162 (cadência adaptada)  — depois de M161, ~300 LOC
M163 (schema migration)   — quando B estiver confiável, ~300 LOC
M164 (subcomandos A.2)    — depois de M163, ~700 LOC
M165 (TUI reescrita A.3)  — depois de M164, ~500 LOC
[A.4, A.5 opcional]       — quando A.3 estiver sólido
```

**Critério de "B confiável":**
- 7 skills rodam diariamente sem erro
- `td chat` permite planejar revisão Q4 com base em vault
- Propostas sempre pedem `--approve` (nunca auto-exec)
- Vault entry de cada proposta/commit existe

**Critério de "migrar pra A":**
- Você usa `td chat` pelo menos 1x/semana
- Tasks criadas via deep agent aparecem corretamente no `td list`/`td tui`
- Schema do DB tem `tags`, `deps`, `audit_log` faltando (gargalo)

---

## Visão completa do horizonte (TL;DR tabela)

| Milestone | Horizonte | LOC | Sessão | Status |
|---|---|---|---|---|
| M154 | (audit) | 0 | ✓ feito | ✅ |
| M155 | (spec) | 0 | ✓ feito | ✅ |
| M156 | B | ~300 | ✓ feito | ✅ |
| M157 | B | ~50 | ✓ feito | ✅ |
| M158 | B | ~250 | ✓ feito | ✅ |
| **M159** | B | ~100 | **próximo** | ⏳ |
| M160 | (cancelado) | 0 | — | 🚫 |
| M161 | B | ~400 | 2 | ⏳ |
| M162 | B | ~300 | 3 | ⏳ |
| **M163** | A.1 | ~300 | 4 | ⏳ |
| **M164** | A.2 | ~700 | 5 | ⏳ |
| **M165** | A.3 | ~500 | 6 | ⏳ |
| M166 | A.4 | ~700 | 7-8 | ⏳ |
| M167 | A.5 | ~700 | 9-10 | ⏳ |
| ... | C | ? | ? | 🔮 |

**Total até A.3:** ~2.700 LOC em 6 sessões (M159-M165)
**Total até A.5:** ~4.000 LOC em 10 sessões (M159-M167)
**Total com C:** indefinido

---

## Critério de done (horizonte A inteiro)

- [ ] `td --help` mostra 22+ subcomandos (igual upstream)
- [ ] `td tui` tem 3 modes (dashboard, timeline, gantt) com keys
- [ ] Schema DB tem `tags`, `deps`, `audit_log`, `started_at`, `completed_at`
- [ ] Cada subcomando tem test (não só smoke)
- [ ] Você usa `td tui` no dia-a-dia (não só em demo)
- [ ] TUI integra com `td chat` (proposta do agent aparece como notificação no TUI)

## Critério de done (horizonte B inteiro)

- [ ] 7 skills rodam diariamente sem erro
- [ ] `td chat` permite planejar Q4 review com base em vault
- [ ] Propostas sempre pedem `--approve`
- [ ] Vault SOT: cada modificação tem entry no vault antes E depois
- [ ] Cache de embeddings do vault hit > 80%

## Riscos

| Risco | Mitigação |
|---|---|
| Schema migration quebra dados existentes | backup automático + smoke test antes de aplicar |
| gantt/optimize têm algoritmo complexo | entregar TUI sem esses primeiro (M163-M165), adicionar depois |
| Cloudflared tunnel continuar falhando | desiste de Studio, mantém `td chat` REPL como interface |
| Vault cache hit rate < 80% | primeiro mede sem cache, vê se precisa |
| Você cansar antes de A terminar | B já entrega 80% do valor diário, A é bônus |

## Out of scope (explícito)

- ❌ Copiar/adaptar código upstream do taskdog (re-escrever do zero)
- ❌ PAV-math reativação (ADR-013, user confirmou FORA)
- ❌ Auto-approval (M155, M158: sempre pede `--approve`)
- ❌ Web UI / Studio bloqueado por CORS (se cloudflared não cooperar)
- ❌ Cross-fork reconciliation (já tem `agent_propagator`)
- ❌ Real-time vault watching (file watcher) — só cron + on-demand

---

## Próximo passo concreto

**M159 — vault embeddings cache (B.4)**

- 30 min
- ~100 LOC em `src/ikigai/src/agents/v2/vault_cache.py`
- ChromaDB PersistentClient (já existe em `data/chroma_db/`)
- mtime-based invalidation
- Wired em `recall_node`
- Tests: cache hit rate, mtime change re-indexa

**Posso começar M159 AGORA?**
