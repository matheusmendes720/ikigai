# 01 — Axioma: Fundamentos de Probabilidade

> **Categoria:** §1 Base axiomática
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** mapa `EnergyLevel` em habit_engine.py, scoring vetorial IKIGAi, modelo de energia do PAV §6

---

## §1 — Intuição em linguagem simples

Algumas medidas são ruidosas. Você reporta "energia ALTA" hoje, mas o sinal subjacente pode estar em qualquer valor entre 70 e 95. Precisamos de uma forma de falar sobre **expectativas** sem conhecer o resultado exato — é isso que o valor esperado oferece. A **variância** então nos diz quanto a resposta pode oscilar.

## §2 — Enunciado formal

Para uma variável aleatória discreta X com valores {xᵢ} e probabilidades {pᵢ}:

```
E[X]   = Σᵢ pᵢ · xᵢ
Var(X) = E[(X − E[X])²] = E[X²] − (E[X])²
```

Para X contínua com densidade f(x):

```
E[X]   = ∫ x · f(x) dx
Var(X) = ∫ (x − E[X])² · f(x) dx
```

Probabilidade condicional: `P(A|B) = P(A ∩ B) / P(B)`.

## §3 — Justificativa não-técnica

Imagine sua energia autorelatada como um medidor ruidoso. Você diz "ALTA" hoje, mas ontem disse "MÉDIA" embora os dois dias tenham parecido semelhantes. O sistema trata ALTA/MÉDIA/BAIXA como faixas discretas mapeadas em razões {1.0, 0.6, 0.3} — isto é um **valor esperado quantizado** sob o ruído do relato. Mesmo uma leitura imprecisa tem uma média útil; a variância apenas nos lembra que a resposta pode oscilar.

É por isso que o sistema consegue agir sobre uma única leitura diária: confiamos que o **valor esperado** esteja próximo do sinal verdadeiro, mesmo sem observá-lo diretamente.

## §4 — Referências cruzadas (consumidores downstream)

- **06-postulado-habit-momentum** — usa E/E_max como termo de energia do Q_HE
- **13-engine-habit-engine** — mapeia o enum `EnergyLevel` em razão via distribuição discreta
- **15-meta-ikigai-5-vector-scoring** — os 5 vetores agregam sinais ruidosos por hábito

## §5 — Fontes

- `src/operational/packages/core/src/operational/core/habit_engine.py` — mapa `EnergyLevel` → razão
- `src/ikigai/src/ikigai/core/scoring/vector_scores.py` — scoring de valor esperado nos 5 vetores
- `src/operational/docs/adr/PRD-CORE-HABIT-ENGINE.md` §4.5 — distribuição do bônus de sequência
- `vibe-ops/base/Produtividade Algorítmica Visual.md` §6 — derivação do modelo de energia
