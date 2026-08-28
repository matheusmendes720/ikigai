# 09 — Postulado: IKIGAi 5-Vetores

> **Categoria:** §2 Primitivos de domínio
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** ADR-003 §3, vector_scores.py, IKIGAi meta-cérebro

---

## §1 — Intuição em linguagem simples

IKIGAi significa "razão de ser" em japonês. O framework clássico propõe 4 círculos sobrepostos (paixão / missão / profissão / vocação), mas no nosso sistema usamos um modelo de **5 vetores**: paixão, habilidade, mercado, receita e curso (trilha de aprendizado).

## §2 — Enunciado formal

Os 5 vetores (ADR-003 §3):

```
V_paixão  = (1 − e^(−λₛ · sequência)) · fator_alinhamento
V_habilid = Σᵢ velocidade_habilidadeᵢ · relevância_mercadoᵢ
V_mercado = encaixe_oportunidade · crescimento_mercado
V_receita = Σᵢ receitaᵢ · retençãoᵢ / alvo
V_curso   = 100 · (1 − distância(curso, V_paixão))
```

Cada Vᵢ ∈ [0, 100]. O meta-vetor é o híbrido geométrico + harmônico (ver 23-meta-ikigai-meta-vector).

**Pesos canônicos (Opção C deferida):**

| Vetor   | Peso padrão |
|:-------:|:-----------:|
| Paixão  | 0.20        |
| Habilidade | 0.20     |
| Mercado | 0.20        |
| Receita | 0.20        |
| Curso   | 0.20        |

Pesos simétricos até ≥5 SONHOs manuais (regra dos 5 logs, ADR-007).

## §3 — Justificativa não-técnica

Por que **5 vetores** em vez de 4: receita entra como vetor de primeira classe porque sustentabilidade financeira **habilita** os outros. Uma paixão que não paga é um hobby; uma paixão que paga é uma vocação. O modelo de 5 vetores captura essa distinção sem a qual o sistema não consegue distinguir sonho-realista de sonho-impossível.

Por que pesos simétricos por padrão: a regra dos 5 logs (ADR-007) diz que cada entidade só vira código depois de 5 logs manuais. Sem evidência empírica sobre qual vetor pesa mais para o usuário, pesos simétricos evitam vieses escondidos. O slot `_intent_vector` informal (custom block) permite capturar intenção sem validar prematuramente.

**Conflito registrado (memória `user-revenue-weight-preference`):** o usuário declarou que receita deveria carregar o peso mais alto, mas isso conflita com pesos simétricos e com a regra de deferir até evidência empírica. Aguardando decisão explícita.

## §4 — Referências cruzadas (consumidores downstream)

- **15-meta-ikigai-5-vector-scoring** — implementação dos 5 vetores
- **23-meta-ikigai-meta-vector** — composição geométrica + harmônica
- **24-meta-fractal-regime-hierarchy** — propagação fractal SONHO→TRIMESTRE→ONDA→SEMANA→DIA
- **Axioma 02** — vetor paixão usa decaimento exponencial

## §5 — Fontes

- `src/ikigai/src/ikigai/core/scoring/vector_scores.py` — implementação dos 5 vetores
- `vibe-ops/architecture/ADR-003-ikigai-as-meta-brain.md` §3 — modelo de 5 vetores
- `vault/ikigai/meta/perspective-log-2026-07-03.md` — decisão Opção C (pesos simétricos deferidos)
- `vault/ikigai/meta/algorithm-issues-registry.md` — debate N01 (4 vs 5 vetores)
