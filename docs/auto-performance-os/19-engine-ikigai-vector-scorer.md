# 19 — Engine: IKIGAi Vector Scorer

> **Categoria:** §3 Engines
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** vector_scores.py, ADR-003 §3, meta-vector (geo + harmônico)

---

## §1 — Intuição em linguagem simples

Implementa os 5 vetores do postulado 09. Cada vetor é uma função pura sobre dados do SONHO/Task/Habit. O meta-vetor (composto geométrico + harmônico) penaliza vetores próximos de zero — não dá pra "compensar" um vetor baixo inflando outros.

## §2 — Enunciado formal

**Os 5 vetores (cada Vᵢ ∈ [0, 100]):**

```
V_paixão  = (1 − e^(−λₛ · sequência)) · fator_alinhamento
V_habilid = Σᵢ velocidade_habilidᵢ · relevância_mercadoᵢ
V_mercado = encaixe_oportunidade · crescimento_mercado
V_receita = Σᵢ receitaᵢ · retençãoᵢ / alvo
V_curso   = 100 · (1 − distância(curso, V_paixão))
```

**Meta-vetor (composto):**

```
geo_médio = (Πᵢ Vᵢ)^(1/5)
harm_médio = 5 / Σᵢ (1/Vᵢ)
meta_vetor = 0.6 · geo_médio + 0.4 · harm_médio
```

Pesos do composto: **0.6 geométrico + 0.4 harmônico** (híbrido; ADR-003 §3.4).

## §3 — Justificativa não-técnica

Por que **híbrido geométrico + harmônico** em vez de só média aritmética: a média geométrica **penaliza vetor zero** (Πᵢ Vᵢ → 0 se algum Vᵢ → 0); a harmônica **penaliza mais ainda** vetores próximos de zero. O híbrido 60/40 garante que um SONHO com vetor_receita=5 (não está ganhando dinheiro) não consegue meta_vetor alto mesmo com outros vetores a 80.

Em bootstrap típico (todos os vetores vazios), `meta_vetor ≈ 39.9`. Subir para 80+ requer que **todos os 5 vetores** estejam ≥ 60 — captura a intuição de IKIGAi como **equilíbrio**, não como otimização de uma dimensão só.

## §4 — Referências cruzadas (consumidores downstream)

- **09-postulado-ikigai-5-vetores** — claim de domínio construído sobre este engine
- **Axioma 02** — vetor paixão usa decaimento exponencial
- **23-meta-ikigai-meta-vector** — composição geométrica + harmônica canônica
- **24-meta-fractal-regime-hierarchy** — propagação fractal SONHO → níveis inferiores

## §5 — Fontes

- `src/ikigai/src/ikigai/core/scoring/vector_scores.py` — 5 vetores + meta-vetor
- `vibe-ops/architecture/ADR-003-ikigai-as-meta-brain.md` §3 — modelo IKIGAi
- `vault/ikigai/meta/cycle-bootstrap-analysis-2026-08-26.md` — análise de bootstrap (meta_vetor ≈ 39.9)
