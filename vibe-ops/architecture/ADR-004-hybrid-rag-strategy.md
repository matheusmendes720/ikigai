# ADR-004: Estratégia de RAG Híbrido (SQLite + ChromaDB + Obsidian)

**Status:** Proposta
**Data:** 2026-06-05
**Autores:** Matheus + AI Agent
**Contexto:** `life/vibe-ops/`

---

## 1. Contexto

O workspace tem **3 tipos de dados** que coexistem:

1. **Structured (relacional):** status, story points, timestamps, FKs
   → melhor em SQLite
2. **Unstructured (semântico):** notes Markdown, commit messages, journals
   → melhor em vector store
3. **Graph (relacional-com-links):** `Topic → Prerequisite`, `Task → Task`, `StudyNote → Project`
   → melhor em grafo (Neo4j) ou em Markdown links

O problema é: **como indexar e consultar todos esses tipos de dados
sem duplicação e sem LLM obrigatório?**

**Restrição do usuário:** *"nao tera nada de nlp .. processar apenas usando aritmetica"*.
Mas o sistema precisa permitir retrieval semântico de notes (a longo prazo),
e o framework já tem `vibe-ops/src/pipeline/rag_indexer.py` (3.7K) que
usa embeddings locais.

---

## 2. Decisão

Adotar a estratégia **Hybrid RAG** definida em [`vibe-ops/specs/SPEC-05-cybernetic-epistemic-mesh.md`](../specs/SPEC-05-cybernetic-epistemic-mesh.md):

### 2.1. Camadas (3 layers)

| Layer | Engine | Conteúdo | Schema |
|---|---|---|---|
| **1. Relacional (SoT)** | SQLite (local) | `study_topics`, `dev_projects`, `planning_entities`, `roadmap_sync`, `policy_decisions` | [`vibe-ops/src/storage/schema.sql`](../src/storage/schema.sql) |
| **2. Vector (semântico)** | ChromaDB (local) ou sqlite-vec (fallback) | Obsidian notes, commit messages, daily journals, study session notes | [`vibe-ops/src/storage/chroma_adapter.py`](../src/storage/chroma_adapter.py) |
| **3. Graph (relacional-com-links)** | Obsidian (Markdown links) + Neo4j (opcional) | `Topic → Prerequisite`, `Task → Task`, `StudyNote → Project/Task` | Wiki-links em `.md` + `vibe-ops/src/parsers/code_parser.py` |

### 2.2. Modelo de Embedding

- **Default:** SBERT local (sentence-transformers)
- **Alternativa:** OpenAI API (configurável via `vibe-ops/src/embeddings/provider.py`)
- **NÃO usar:** LLMs no pipeline diário (apenas retrieval, não geração)

### 2.3. Pipeline de Indexação

```
[Source: Obsidian .md] → [Frontmatter Parser] → [Pydantic validation] → [SQLite INSERT]
                                                                              ↓
                                                                 [Chunker (1500 tokens, 100 overlap)]
                                                                              ↓
                                                                 [SBERT Embedding]
                                                                              ↓
                                                                 [ChromaDB upsert]
```

### 2.4. Pipeline de Retrieval (futuro)

```
[Query] → [Vector search top-k] → [Filter by FK/SQL] → [Re-rank by IKIGAi]
                                                                  ↓
                                                          [Return chunks + paths]
```

**Otimizações futuras:**
- Re-rank por `ikigai_score` (vetores relevantes primeiro)
- Filter por `wave` (só notes da wave atual)
- Filter por `vector` (só notes alinhadas com vetor IKIGAi ativo)

---

## 3. Alternativas Consideradas

### 3.1. Alternativa A: Apenas SQLite (sem vector store) — Rejeitada

**Motivos da Rejeição:**
- Notes Markdown perdem retrieval semântico
- "Buscar 'JWT validation' em 1000 notes" não funciona
- Falsa economia (esforço de busca manual > economia de storage)

### 3.2. Alternativa B: Apenas ChromaDB (sem SQLite) — Rejeitada

**Motivos da Rejeição:**
- Status, FK, timestamps exigem SQL
- Atomicidade de updates (study_sessions + study_topics)
- Vector store não é bom para relational queries
- Difícil fazer JOINs (que é o que mais precisa)

### 3.3. Alternativa C: Apenas Obsidian + Dataview — Parcialmente aceita

**Descrição:** Plugin Dataview do Obsidian para queries em YAML.

**Motivos da Aceitação Parcial:**
- 🟢 Read-only, sem sync necessário
- 🟢 Útil para dashboards locais do Obsidian
- 🔴 Read-only — não pode injetar dados no TW
- 🔴 Performance degrada com vaults grandes
- 🔴 Não suporta JOINs TW ↔ Markdown

**Veredito:** Mantido como **camada de visualização leve**, mas rejeitado como motor de pipeline.

### 3.4. Alternativa D: Neo4j (graph database full) — Rejeitada

**Motivos da Rejeição:**
- Overhead (precisa daemon rodando)
- Single-user não justifica
- Wiki-links do Obsidian já cobrem 80% dos casos

---

## 4. Consequências

### 4.1. Positivas

- **Cada layer com seu papel claro** (SQLite=SoT, ChromaDB=search, Obsidian=graph)
- **Append-Only** respeitado (vector store cresce, nunca apaga)
- **Idempotente** — re-indexar é seguro
- **Local** — sem dependência cloud

### 4.2. Negativas / Riscos Aceitos

- **Custo de storage** — ChromaDB cresce indefinidamente
- **SBERT local** é mais lento que API OpenAI
- **3 layers = 3 schemas** para manter sincronizados
- **Vector search não é exato** — pode perder notas relevantes

### 4.3. Mitigações

- Periodic garbage collection em ChromaDB (a cada PHASE)
- Config de modelo via `vibe-ops/src/embeddings/config.py`
- `triagem.md` para notas que escapam do indexer
- `hybrid_search` em `vibe-ops/src/vibe_cli.py` (já existe)

---

## 5. Implementação

### Sprint 1 (esta semana)
- [ ] **NÃO implementar Hybrid RAG** ainda (foco em inputs manuais)
- [ ] Validar que `vibe-ops/src/pipeline/rag_indexer.py` é importável
- [ ] Documentar schema ChromaDB no `ikigai_propagation.md` (já feito)

### Sprint 2-4
- [ ] Adicionar migration para `chroma_collections` table em SQLite
- [ ] Implementar `HybridRAGIndexer` completo
- [ ] Integrar com `AI Harness` (epistemic + metrics)

### Q4 2026+
- [ ] Neo4j opcional para grafo de dependencies
- [ ] Re-rank por IKIGAi score (futuro)

---

## 6. Referências

### Specs & Architecture

- [`vibe-ops/specs/SPEC-05-cybernetic-epistemic-mesh.md`](../specs/SPEC-05-cybernetic-epistemic-mesh.md) — Cybernetic mesh (Hybrid RAG definition)
- [`vibe-ops/architecture/ADR-001-data-flow-topology.md`](ADR-001-data-flow-topology.md) — Topologia
- [`vibe-ops/architecture/ADR-005-data-mesh-topology.md`](ADR-005-data-mesh-topology.md) — Data mesh

### Implementação

- [`vibe-ops/src/pipeline/rag_indexer.py`](../src/pipeline/rag_indexer.py) — RAG indexer
- [`vibe-ops/src/pipeline/knowledge_tree.py`](../src/pipeline/knowledge_tree.py) — Knowledge graph
- [`vibe-ops/src/storage/chroma_adapter.py`](../src/storage/chroma_adapter.py) — ChromaDB adapter
- [`vibe-ops/src/storage/sqlite_vec_integration.py`](../src/storage/sqlite_vec_integration.py) — sqlite-vec fallback
- [`vibe-ops/src/storage/vector_store.py`](../src/storage/vector_store.py) — Vector store
- [`vibe-ops/src/embeddings/provider.py`](../src/embeddings/provider.py) — Embeddings provider
- [`vibe-ops/src/embeddings/config.py`](../src/embeddings/config.py) — Config
- [`vibe-ops/src/integration/obsidian_parser.py`](../src/integration/obsidian_parser.py) — Obsidian parser
- [`vibe-ops/src/integration/semantic_engine.py`](../src/integration/semantic_engine.py) — Semantic engine

### Doc

- [`vibe-ops/doc/01.5-data-contracts-and-pipelines.md`](../doc/01.5-data-contracts-and-pipelines.md) — Contratos + pipelines
- [`vibe-ops/doc/03-data-mesh-enrichment.md`](../doc/03-data-mesh-enrichment.md) — Enrichment

### Cluster docs

- [`../../CLUSTER_STUDY.md`](../CLUSTER_STUDY.md) — Cluster 3 (PKM)
- [`../../life-ops/planner/ikigai_planning/ikigai_propagation.md`](../life-ops/planner/ikigai_planning/ikigai_propagation.md) — Data flow

---

*ADR-004 — v1.0 — 2026-06-05 — Estratégia de RAG Híbrido (SQLite + ChromaDB + Obsidian)*
