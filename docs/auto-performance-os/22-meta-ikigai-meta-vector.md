# 22 — Meta: Composição IKIGAi Meta-Vetor

> **Categoria:** §4 Meta-orquestração
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** ADR-003 §3.4, vector_scores.py, meta_vector.py

---

## §1 — Intuição em linguagem simples

Combina os 5 vetores IKIGAi (paixão/habilidade/mercado/receita/curso) em um único score que captura **equilíbrio**. Um SONHO com 4 vetores a 80 e um a 5 (receita zero) tem meta-vetor baixo — não dá pra "compensar" um vetor baixo inflando outros.

## §2 — Enunciado formal

**Inputs:** V₁, V₂, V₃, V₄, V₅ ∈ [0, 100].

**Composição geométrica:**

```
geo_médio = (V₁ · V₂ · V₃ · V₄ · V₅)^(1/5)
```

**Composição harmônica:**

```
harm_médio = 5 / (1/V₁ + 1/V₂ + 1/V₃ + 1/V₄ + 1/V₅)
```

**Meta-vetor (composto híbrido):**

```
meta_vetor = 0.6 · geo_médio + 0.4 · harm_médio
```

**Relação invariante:**

```
harm_médio ≤ geo_médio ≤ arit_médio
```

(a harmônica é a mais conservadora, a aritmética a mais permissiva).

## §3 — Justificativa não-técnica

Por que **híbrido geométrico + harmônico** em vez de só aritmética: a média aritmética **esconde** vetores próximos de zero. Se V_receita=5 (não está ganhando dinheiro), média aritmética com outros vetores=80 dá 65 — falsamente OK. Já `geo_médio` com V_receita=5 e outros=80 cai para 51, e `harm_médio` para 22. O híbrido 0.6/0.4 garante **penalidade visível** sem ser catastrófica.

Por que **0.6/0.4 e não 0.5/0.5**: a geométrica já equilibra razoavelmente; a harmônica entra com peso menor como **penalizador adicional** para vetores muito baixos. Isso bate com a intuição de que IKIGAi deve recompensar equilíbrio mas **não ser punitivo** quando há 1 vetor baixo e 4 bons.

Em **bootstrap** (todos os vetores vazios, ~ valor default 50): `geo_médio ≈ 50`, `harm_médio ≈ 50`, `meta_vetor ≈ 50`. Em SONHO ativo (vetores 80/80/80/80/80): `meta_vetor = 80`. Em SONHO quebrado (80/80/80/80/5): `meta_vetor ≈ 51` — sinaliza problema mas não desmotiva.

## §4 — Referências cruzadas (consumidores downstream)

- **09-postulado-ikigai-5-vetores** — definição dos 5 vetores
- **19-engine-ikigai-vector-scorer** — produtor dos 5 vetores
- **Axioma 02** — vetor paixão usa decaimento exponencial
- **24-meta-fractal-regime-hierarchy** — meta_vetor entra na hierarquia

## §5 — Fontes

- `vibe-ops/architecture/ADR-003-ikigai-as-meta-brain.md` §3.4 — escolha de 0.6/0.4
- `src/ikigai/src/ikigai/core/scoring/meta_vector.py` — implementação `compute_meta_vector(v1, v2, v3, v4, v5)`
- `vault/ikigai/meta/cycle-bootstrap-analysis-2026-08-26.md` — análise do bootstrap
- `vault/ikigai/meta/ikigai-vector-weight-mechanism-defer.md` — Opção C deferida (pesos simétricos w=0.20)