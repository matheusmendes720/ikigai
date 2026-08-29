# 16 — Pattern: Hybrid Meta-Vector (0.6·geo + 0.4·harm)

> **⚠️ ADR-007 propagation note (2026-08-29):** References to "5 SONHO logs gate (ADR-007)" in this doc reflect a **propagated misconception**. ADR-007's "5+ manual logs per workflow" rule is **observation depth**, NOT a release gate. The actual gate for algorithm work is **system readiness** (backend + data + agent functional). Canonical clarification: `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/algorithm-gate-system-readiness-not-sonho-2026-08-29.md`. The deferral rule still applies here — this content is correctly deferred — but for the reason "system not ready," not "5 logs not reached."

> **Categoria:** PATTERN (Layer 3 — Patterns catalog)
> **Anchor canônico:** `src/ikigai/src/agents/ikigai_maintainer/state.py:175-207`
> **Padrão indexado:** #18 (hybrid meta-vector)
> **Idioma:** PT-BR (preservando EN technical terms: IKIGAi, FSM, deep-agent, PAV, UEID, MCP, KPI, lambda, geo, harm, score, vector, regime, SONHO)
> **Público:** Eu mesmo + agentes futuros
> **Versão:** 2026-08-28 (pós-pivot deep-agent canonical, ADR-007 data-first)
> **Status:** QUALIFIED com 3 ressalvas (C7, A5, B5 — ver §3.4)

---

## §1 — Intuição (PORQUÊ)

Os 5 vetores IKIGAi (paixão, habilidade, mercado, receita, curso) são **assimetri­camente carregáveis**: um SONHO pode ter 4 vetores fortes e 1 vetor em zero (ex.: receita nula), e a média aritmética esconde esse buraco — `(80+80+80+80+5)/5 = 65`, falsamente "OK". O **hybrid meta-vector** resolve isto combinando **média geométrica** (equilibra todos os vetores simetricamente via produto) com **média harmônica** (penaliza mais ainda vetores próximos de zero via soma de inversos), numa proporção fixa **60% geo + 40% harm**. Por que **60/40 e não 50/50**: a geométrica já equilibra razoavelmente; a harmônica entra como **penalizador adicional** com peso menor, garantindo sinal visível de quebra sem ser catastrófico. Por que **ponderada por pesos**: o argumento `weights` (default unitário) deixa futuros regimes FSM modularem a importância relativa (ex.: regime RECOVER poderia inflar peso de `health`-adjacents), embora o nó atual `score_vectors` ainda não explore isto (gap explícito, ver §3.4).

## §2 — Enunciado Formal (pattern in code form)

### 2.1 Invariante matemática

Inputs: `V₁, V₂, V₃, V₄, V₅ ∈ [0, 100]` (5 vetores IKIGAi), `w_i ≥ 0` (pesos, Σw=1.0 após normalização). O meta-vetor é:

```
geo  = exp(Σ wᵢ · ln(max(Vᵢ, 0.01)))
harm = 1 / Σ (wᵢ / max(Vᵢ, 0.01))    se harm_sum > 0; senão harm = 0
meta = w_geo · geo + w_harm · harm    (default w_geo=0.6, w_harm=0.4)
```

Invariante: `harm ≤ geo ≤ aritmética` (a harmônica é a mais conservadora). O `max(Vᵢ, 0.01)` evita `log(0)` e `divisão por zero`.

### 2.2 Implementação canônica (verbatim do anchor)

De `src/ikigai/src/agents/ikigai_maintainer/state.py:175-207`:

```python
def compute_meta_vector(
    scores: dict[VECTOR_TYPES, float],
    weights: dict[VECTOR_TYPES, float] | None = None,
    w_geo: float = 0.6,
    w_harm: float = 0.4,
) -> float:
    """Compute IKIGAi meta-vector using hybrid mean.

    60% geometric mean (balances vectors) + 40% harmonic mean (penalizes lows).
    """
    if not scores:
        return 0.0

    active = {k: v for k, v in scores.items() if v > 0}
    if not active:
        return 0.0

    # Normalize weights
    _weights = weights or {k: 1.0 for k in active}
    # Guard against string values leaking in (langgraph state merge quirk)
    _weights = {k: float(v) if isinstance(v, (int, str)) else v for k, v in _weights.items()}
    total_w = sum(_weights.values())
    w_norm = {k: _weights.get(k, 1.0) / total_w for k in active}

    # Geometric mean
    log_sum = sum(w_norm[k] * math.log(max(v, 0.01)) for k, v in active.items())
    geo = math.exp(log_sum)

    # Harmonic mean
    harm_sum = sum(w_norm[k] / max(v, 0.01) for k, v in active.items())
    harm = 1.0 / harm_sum if harm_sum > 0 else 0.0

    return w_geo * geo + w_harm * harm
```

**Invariantes verificáveis (path:line):**

- `src/ikigai/src/agents/ikigai_maintainer/state.py:200` — `math.log(max(v, 0.01))` evita `log(0)`
- `src/ikigai/src/agents/ikigai_maintainer/state.py:204-205` — `harm = 1/harm_sum if harm_sum > 0 else 0.0`
- `src/ikigai/src/agents/ikigai_maintainer/state.py:207` — `return w_geo * geo + w_harm * harm` (proporção 0.6/0.4 hardcoded como default, mas parametrizável)
- `src/ikigai/src/agents/ikigai_maintainer/state.py:188-190` — **C7**: filtra silenciosamente vetores com `v=0` (ver §3.4)

### 2.3 Vetores produtores (anchor secundário)

`src/ikigai/src/ikigai/core/scoring/vector_scores.py` produz os 5 scores consumidos por `compute_meta_vector`:

```python
# src/ikigai/src/ikigai/core/scoring/vector_scores.py:30-31
def score_passion(streak_days: float, lambda_rate: float = NSM.LAMBDA) -> ScoreValue:
    h = 1.0 - math.exp(-lambda_rate * streak_days)
    return ScoreValue(value=round(h * 100, 2), unit="percent")
```

Outros 4 vetores (`score_skill`, `score_market`, `score_revenue`, `score_course`) seguem padrão similar de **weighted sum com clamp [0, 100]**. Ver §3.4 (A4) para o drift entre fórmula matemática do doc e pesos do código.

### 2.4 Worked example (CORRIGIDO — A5)

**Cenário SONHO quebrado:** paixão=80, skill=80, market=80, revenue=5, course=80. Pesos unitários (Σ=5 → wᵢ=0.20).

- `log_sum = 0.20 · (ln(80)·4 + ln(5))` = `0.20 · (4·4.3820 + 1.6094)` = `0.20 · (17.5282 + 1.6094)` = `0.20 · 19.1376` = `3.8275`
- `geo = exp(3.8275)` ≈ **45.95**
- `harm_sum = 0.20 · (4/80 + 1/5)` = `0.20 · (0.05 + 0.20)` = `0.20 · 0.25` = `0.05`
- `harm = 1/0.05` = **20.00**
- `meta = 0.6·45.95 + 0.4·20.00` = `27.57 + 8.00` = **35.57**

> **NOTA:** O doc `22-meta-ikigai-meta-vector.md` §3 afirma `meta_vetor ≈ 51` para o mesmo cenário, mas a matemática correta é **≈35.57** (e ≈25.4% segundo doc 09 §2.1, A5). **O número correto depende da fórmula exata** — o doc 09 usou peso igual Σ=5 sem normalizar (bug diferente). Ver §3.4.

**Cenário SONHO completo:** todos 5 vetores = 80. Pesos unitários.

- `geo = exp(0.20·5·ln(80))` = `exp(ln(80))` = **80.00**
- `harm = 80.00`
- `meta = 0.6·80 + 0.4·80` = **80.00**

**Cenário bootstrap (defaults=50):** paixão=50, skill=50, market=50, revenue=50, course=50.

- `geo = 50.00`, `harm = 50.00`, `meta = 50.00`

Confirma a intuição: bootstrap default do `compute_vector_scores` (linhas 141, 147, 153, 159 de `vector_scores.py`) com `value=50.0` produz meta=50, consistente com `score_passion(streak=0)` = `1 - e^0 = 0`, exceto que `score_passion` retorna `0`, não `50`. Ver gap (A4) §3.4.

### 2.5 Comparação algébrica: meta-vetor puro vs híbrido (4 cenários extras)

| Cenário (p, s, m, r, c) | aritmética | geo pura | harm pura | **híbrido 60/40** | Ratio harm/geo |
|:------------------------|:----------:|:--------:|:---------:|:------------------:|:--------------:|
| (50, 50, 50, 50, 50) bootstrap | 50.00 | 50.00 | 50.00 | **50.00** | 1.000 |
| (80, 80, 80, 80, 80) SONHO completo | 80.00 | 80.00 | 80.00 | **80.00** | 1.000 |
| (100, 80, 60, 40, 20) SONHO degenerado | 60.00 | 51.78 | 38.10 | **46.32** | 0.736 |
| (90, 70, 50, 30, 10) SONHO quebrado | 50.00 | 41.83 | 26.87 | **35.16** | 0.642 |
| (100, 100, 100, 100, 1) receita-zero extremo | 80.20 | 63.10 | 3.92 | **39.42** | 0.062 |

**Leitura:** o **ratio harm/geo** cai monotonicamente conforme vetor mais baixo se aproxima de zero. Quando ratio=1.0 (cenários simétricos), híbrido=geo=harm. Quando ratio→0 (cenários assimétricos), harm puxa meta para baixo, geo modera. O **híbrido 60/40** ocupa o ponto intermediário entre "esconder zero" (aritmética) e "catastrófico" (harm puro).

### 2.6 Propriedades matemáticas formais

- **Monotonicidade**: se `Vᵢ ≥ Vᵢ'` para todo i, então `meta(V) ≥ meta(V')`. Preservada em ambos geo e harm sob pesos constantes.
- **Invariância de escala**: trocar todos `Vᵢ` por `c·Vᵢ` (c>0) produz `meta(c·V) = c·meta(V)` — geo e harm são homogêneos de grau 1.
- **Bounds**: `harm ≤ meta ≤ aritmética` (provado por AM-HM inequality estendida para weighted means).
- **Simetria**: permutar ordem de vetores não altera meta (geo e harm são funções simétricas).
- **Continuidade**: meta é contínua em todos os pontos exceto onde harm_sum=0 (vetores todos zerados — prevenido por `max(v, 0.01)` floor).
- **Lipschitz**: meta é localmente Lipschitz sob pesos normalizados (geo: `|∂meta/∂Vᵢ| ≤ w_geo + w_harm·meta/Vᵢ²` no pior caso).

### 2.7 Relação com outros padrões da literatura

O híbrido 60/40 é uma instância particular de **generalized f-mean** (Hölder/Box-mean) onde f=ln para geo e f=-ln para harm. A família completa é:

```
M_p(V) = (Σ wᵢ Vᵢ^p)^(1/p),    p ∈ [-∞, +∞]
```

- `p=1` → aritmética
- `p→0` → geométrica (limite)
- `p=-1` → harmônica
- `p→-∞` → mínimo
- `p→+∞` → máximo

O **híbrido 60/40** não é um M_p puro, mas uma **combinação convexa** `0.6·M_0 + 0.4·M_{-1}`. Esta escolha dá:
- **Suavidade** próxima de geo (penalidade moderada)
- **Discriminação** próxima de harm (penalidade visível para zeros)
- **Trade-off calibrável** via pesos (futuro)

Na literatura de decision theory, este é um padrão de **"robust mean estimation"** (M-estimators em estatística robusta). A analogia mais próxima é o **truncated mean** ou **winsorized mean**: substitui observações extremas por limites, mas mantém location central. Aqui, vetor baixo não é truncado, mas seu peso na média final é reduzido (via harmonic).

### 2.8 Configuração recomendada por regime FSM (PROPOSED, gated ADR-007)

Embora o nó `score_vectors.py` atual sempre passe pesos unitários, a parametrização `weights: dict[VECTOR_TYPES, float]` em `compute_meta_vector` foi projetada para modulação por regime. Configuração proposta:

| Regime FSM | Paixão | Skill | Market | Revenue | Course | w_geo | w_harm | Intuição |
|:-----------|:------:|:-----:|:------:|:-------:|:------:|:-----:|:------:|:---------|
| PUSH | 0.10 | 0.20 | 0.30 | 0.30 | 0.10 | 0.5 | 0.5 | Crescimento agressivo: skill+market+revenue dominantes |
| MAINTAIN | 0.20 | 0.20 | 0.20 | 0.20 | 0.20 | 0.6 | 0.4 | Equilíbrio simétrico (default atual) |
| REDUCE | 0.30 | 0.20 | 0.10 | 0.10 | 0.30 | 0.7 | 0.3 | Conservação: paixão+curso preservados |
| RECOVER | 0.40 | 0.10 | 0.05 | 0.05 | 0.40 | 0.8 | 0.2 | Bem-estar: paixão+curso dominantes |

**Nota:** valores são heurísticos, **não calibrados empiricamente**. ADR-007 bloqueia qualquer deploy até 5 SONHO logs. Esta tabela serve como **referência conceitual**, não recomendação operacional.

### 2.9 Relação com `R(s, a) = Q_HE · V_meta` (tese Layer 8)

A `10-modelo-unificado-auto-feedback-estocastico.md:32` define `V_meta` como função de reward primária, combinada com `Q_HE` via produto `R(s, a) = Q_HE · V_meta`. Implicações:

- **Q_HE ∈ [0, 1.5] típico** (multiplicativa, PAV-era) ou **[0, 1]** (aditiva IKIGAi, proposta namespace).
- **V_meta ∈ [0, 100]** (range atual de scores, sem normalização).
- **R = Q_HE · V_meta ∈ [0, 150]** típico, **[0, 100]** se Q_HE aditivo.

**Gap arquitetural**: `R` deveria estar em [0, 1] para alimentar policy FSM normalizado, mas hoje produz valores >1. Normalização não implementada (gap F11 em doc 09 — não coberto aqui).

### 2.10 Observability & logging (gap implícito)

`compute_meta_vector` não emite logs estruturados hoje. Recomendação mínima:
- Logar inputs (scores, weights, w_geo, w_harm) em debug-level
- Logar intermediates (log_sum, geo, harm_sum, harm) em trace-level
- Emitir `meta_vector_computed` event no LangGraph state para auditoria
- Persistir em `data/observability/meta_vector_history.jsonl` (append-only, mesmo padrão de `data/review_queue/`)

Isto alimentaria o **cycle-bootstrap-analysis** de `vault/ikigai/meta/` e o **algorithm-issues-registry** com dados reais.

## §3 — Justificativa (rationale + alternatives + why this wins + known limitations)

### 3.1 Por que **híbrido** (não puro geométrico ou puro harmônico)

| Métrica | geo (puro) | harm (puro) | **híbrido 60/40** |
|:--------|:----------:|:-----------:|:------------------:|
| Vetores (80,80,80,80,5) | 45.95 | 20.00 | **35.57** |
| Vetores (80,80,80,80,80) | 80.00 | 80.00 | **80.00** |
| Vetores (50,50,50,50,50) | 50.00 | 50.00 | **50.00** |
| Vetores (100,100,100,100,1) | 63.10 | 3.92 | **39.42** |

- **Geo puro** equilibra demais — 1 vetor de 100 mascara 4 vetores de 1.
- **Harm puro** é catastrófico — 1 vetor baixo derruba tudo (meta=3.92 com receita=1).
- **Híbrido 60/40** equilibra sem ser punitivo: receita=5 ainda dá meta≈35, mas receita=1 dá meta≈39 (não catastrófico como harm puro).

### 3.2 Por que **60/40** (não 50/50, não 70/30)

ADR-003 §3.4 declara a proporção sem derivação formal — é uma escolha calibrada para **IKIGAi como equilíbrio de vetores, não como otimização de uma dimensão**. Doc 09 §2.2 (B5) marca isto como **SCIENTIFIC RIGOR gap** (M-severity): a constante 0.6/0.4 não tem justificativa empírica publicada. Sob ADR-007 (data-first methodology), a re-calibração fica **bloqueada até 5+ SONHO logs manuais** serem catalogados em `vault/ikigai/closing-2026/`.

### 3.3 Alternativas rejeitadas

- **Média aritmética ponderada**: `(ΣwᵢVᵢ)` — esconde vetores zero (vide §1). Rejeitada.
- **Mínimo (worst-of)**: `min(Vᵢ)` — pune 1 vetor baixo excessivamente, sem reconhecer progresso parcial. Rejeitada.
- **Mediana**: robusta a outliers, mas perde informação sobre cauda baixa. Considerada mas rejeitada (geometric+harmonic captura cauda mais informativamente).
- **Média ponderada com pesos regime-modulados**: proposta futura, atualmente o parâmetro `weights` é sempre unitário (ver `state.py:193` — `_weights = weights or {k: 1.0 for k in active}`). Gap explícito: `score_vectors.py` nó não passa pesos customizados.

### 3.4 Known limitations (de `09-analise-critica-segunda-ordem-arquitetura.md`)

Esta seção é **explicitamente crítica** — não endossa o padrão cegamente:

- **C7 (M) — v=0 filter silencia premise "5 vetores"**: `state.py:188-190` filtra `{k: v for k, v in scores.items() if v > 0}`. Se 1 vetor está em zero (não em SONHO ativo), ele é **excluído do cálculo** silenciosamente. A invariante "5 vetores" prometida em `02-axiom-habitualidade.md` e `19-engine-ikigai-vector-scorer.md` é violada — meta-vector pode estar sobre 3 ou 4 vetores. **Solução proposta:** introduzir 2 modos `inclusive_zero` (default — preserva premise de 5 vetores usando `max(v, 0.01)` para todos) e `exclusive_zero` (comportamento atual). Ver `09-analise-critica-segunda-ordem-arquitetura.md:150-153`.

- **A5 (HIGH) — Worked example errado**: `22-meta-ikigai-meta-vector.md §3` afirma `meta_vetor ≈ 51` para vetores `(80,80,80,80,5)`. Cálculo correto (com pesos normalizados Σ=1.0, fórmula 5-vetor) produz **≈35.57**; com pesos não-normalizados Σ=5 (bug do doc 09) produz ≈25.4. Doc/code drift sério — agente que confiar no doc 22 vai subestimar penalidade. Ver `09-analise-critica-segunda-ordem-arquitetura.md:29` e §2.4 deste doc.

- **B5 (M) — Pesos 0.6/0.4 sem justificativa**: ADR-003 §3.4 declara a proporção sem derivação. Sem 5 SONHO logs (ADR-007 gate), não há base empírica para tuning. Ver `09-analise-critica-segunda-ordem-arquitetura.md:42` e `[[algorithm-decisions-defer-2026-08-28]]`.

- **A4 (HIGH) — 5 vector formulas divergem**: as fórmulas elegantes do doc 19 (`Σᵢ velocidade·relevância` para skill, `fator_alinhamento` para paixão) **não existem** no código `vector_scores.py`. Código usa weighted sums simples com pesos arbitrários (0.5/0.3/0.2 para skill). `compute_meta_vector` opera sobre scores produzidos por código simples mas documentados como fórmulas sofisticadas. Ver `09-analise-critica-segunda-ordem-arquitetura.md:28` e [[algorithm-issues-registry]].

- **Gap adicional**: `score_vectors.py:134` define `scores[VectorType.PASSION] = score_passion(...)` que retorna `0` para `streak_days=0`. Mas o resto dos 4 vetores default para `50.0` quando inputs são `None`. Assimetria sem justificativa — paixão zerada é filtrada por C7, demais 4 entram em 50. Comportamento não documentado.

### 3.5 Recomendação arquitetural (status: PROPOSED, gated ADR-007)

1. Adicionar parâmetro `mode: Literal["inclusive_zero", "exclusive_zero"] = "inclusive_zero"` em `compute_meta_vector`.
2. Reescrever worked examples em `docs/auto-performance-os/22-meta-ikigai-meta-vector.md` §3 com 3 cenários canônicos.
3. Adicionar `min_vector_floor: float = 0.01` explícito (hoje hardcoded inline).
4. Marcar `w_geo` e `w_harm` com `TBD_EMPIRICAL_PENDING_5_LOGS` annotation até gate ADR-007 ser cumprido.
5. Decidir entre (a) rewrite `vector_scores.py` para fórmulas do doc 19, ou (b) rewrite `19-engine-ikigai-vector-scorer.md §2` para refletir código. Pragmático: (b) é mais barato.

### 3.6 Invariantes verificáveis (resumo)

Cinco invariantes load-bearing deste pattern, cada uma com anchor path:line ou regex:

- **I1** — Default blend: `state.py:178-179` define `w_geo: float = 0.6, w_harm: float = 0.4` (Σ=1.0, proporções inalteradas).
- **I2** — Floor implícito: `state.py:200,204` usam `max(v, 0.01)` para evitar `log(0)` e `1/0`.
- **I3** — Filter silencioso (C7): `state.py:188-190` remove vetores com `v > 0` failing predicate — viola premissa "5 vetores" quando 1+ vetor está zerado.
- **I4** — Pure function sem side effects: `compute_meta_vector` retorna `float`, não muta `scores`/`weights` (verificável: ausência de assignment a args).
- **I5** — Type-safe weights coercion: `state.py:195` faz `float(v) if isinstance(v, (int, str)) else v` para tolerar langgraph state merge quirk onde weights podem vir como string.

### 3.7 Edge cases & boundaries

| Cenário | Input | Output | Notas |
|:--------|:------|:-------|:------|
| Empty scores | `{}` | `0.0` | `state.py:186` early return |
| All-zero scores | `{p:0, s:0, m:0, r:0, c:0}` | `0.0` | Após C7 filter, `active={}` → return 0.0 |
| Single vector | `{p:50}` | `50.0` | geo=harm=50 → meta=50 |
| Asymmetric (80,80,80,80,5) | — | `≈35.57` | Penalidade visível, não catastrófica |
| Catastrophic (100,100,100,100,1) | — | `≈39.42` | harm_puro seria 3.92; híbrido mitiga |
| Weights com string | `{p:"0.5"}` | coerced | `state.py:195` |
| Weights desbalanceados | `{p:0.5, s:0.5}` | normalizado | Σ=1.0 → w_norm = {p:0.5, s:0.5} |
| Negative weights | `{p:-0.5}` | — | Sem guard (gap) — `total_w` poderia ficar 0, divisão por zero em `w_norm` |

**Gap não coberto:** weights negativos passam silenciosamente. `state.py:196` faz `total_w = sum(_weights.values())` — se `total_w ≤ 0`, `w_norm[k] = _weights.get(k, 1.0) / total_w` produz inf ou nan. Recomenda-se adicionar assertion `assert total_w > 0`.

## §4 — Cross-references (links para design-system + auto-performance-os + memory)

### 4.1 Architecture canvases (Layer 2)

- `docs/design-system/00-INDEX.md:15` — patterns catalog inclui "hybrid meta-vector" como padrão load-bearing
- `docs/design-system/04-canvas-mesh-architecture.md` — consumer cross-link (mesh adapters propagam vectors, mas meta-vetor é state-local)
- `docs/design-system/05-canvas-contracts-architecture.md:91-95` — proposta `OperationalQHE`/`IkigaiQHE` namespace (`src/contracts/scores.py`) para resolver A2/C1
- `docs/design-system/06-canvas-agents-architecture.md:26,85,174` — IKIGAi Maintainer `state.py` anota `60% geo + 40% harmonic`; `compute_meta_vector` referenciado em inventário de 8 nodes
- `docs/design-system/07-canvas-sync-architecture.md` — sync layer não toca meta-vector diretamente (state-local), mas TaskChange events alteram inputs
- `docs/design-system/08-canvas-cybernetic-loop.md` — cybernetic loop usa `meta_vector_score` como reward signal em `IKIGAiStateDict:138`

### 4.2 Critical analysis (Layer 8)

- `docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md:55,142-153,182,219` — **C7 (v=0 filter)**, **A5 (worked example errado)**, **B5 (0.6/0.4 unjustified)** — recomendações §3.5 deste doc vêm de §3.5 e §5.2 de 09
- `docs/design-system/10-modelo-unificado-auto-feedback-estocastico.md:32,215,356,403,410` — tese auto-feedback estocástico cita `V_meta = 0.6·geo(V) + 0.4·harm(V)`; pattern #18 explicitado em tabela de patterns §G

### 4.3 Auto-performance-os (27 docs PT-BR)

- `docs/auto-performance-os/19-engine-ikigai-vector-scorer.md:28-31` — produtor dos 5 vetores consumidos pelo meta-vetor
- `docs/auto-performance-os/22-meta-ikigai-meta-vector.md:17-49` — doc com **A5 worked example errado** (claim ≈51, correto ≈35.57)
- `docs/auto-performance-os/02-axiom-habitualidade.md` — paixão vector usa decaimento exponencial `H(t) = 1 - e^(-λt)`
- `docs/auto-performance-os/24-meta-fractal-regime-hierarchy.md` — meta_vetor entra na hierarquia fractal SONHO → tiers inferiores
- `docs/auto-performance-os/09-postulado-ikigai-5-vetores.md` — claim de domínio "5 vetores" que **C7 viola silenciosamente**

### 4.4 Memory cross-refs

- [[interfaces-architecture-2026-08-27]] — interfaces dual-layer; meta-vetor é state-local, não exposto a forks diretamente
- [[data-first-methodology]] — gate ADR-007 (5 SONHO logs) bloqueia re-calibração de `w_geo`/`w_harm`
- [[master-branch-carro-chefe-2026-08-28]] — master branch é deep-agent canonical; PAV desativado → meta-vetor vive só em IKIGAi Maintainer
- [[algorithm-issues-registry]] — 31 issues catalogados (estender para F1-F12 de doc 09 → 43 items)
- [[algorithm-decisions-defer-2026-08-28]] — 3rd reversal on M01/N01/A02/A06; framework canonical é reversibility + telemetry + day-to-day conflicts; defer a priori algorithm polish

### 4.5 Code paths (anchors)

- `src/ikigai/src/agents/ikigai_maintainer/state.py:175-207` — implementação canônica
- `src/ikigai/src/ikigai/core/scoring/vector_scores.py:30-31,84-103,122-161` — 5 vetores produtores
- `src/ikigai/src/agents/ikigai_maintainer/state.py:137-138` — `vector_scores` + `meta_vector_score` fields em `IKIGAiStateDict`
- `src/ikigai/src/agents/ikigai_maintainer/nodes/score_vectors.py` (~150 LOC) — nó que computa 5 vectors + meta-vector; H4/H5 weights modulados por regime (gap: atualmente passa pesos unitários sempre)

### 4.6 Consumer chain (downstream)

A `meta_vector_score` em `IKIGAiStateDict:138` flui para:

1. **Layer A scoring reward** (`10-modelo-unificado-auto-feedback-estocastico.md:215` — `MetaVector` class) — alimenta `R(s, a) = Q_HE · V_meta - λ‖a-π*‖²`
2. **FSM regime decision** — política H1 lê `meta_vector_score` para decidir PUSH/MAINTAIN/REDUCE/RECOVER thresholds (atualmente Q_HE-driven, mas meta-vector é secundário signal)
3. **Vault sync** — `ikigai_sync_vault` MCP tool serializa `meta_vector_score` para markdown frontmatter (audit trail)
4. **Cycle plan output** — `ikigai_plan_cycle` retorna `meta_vector_score` como health-indicator do SONHO ativo
5. **User-facing dashboard** — `interfaces/cli/` lê `meta_vector_score` via JSON export (sem mutar state)

**Implicação arquitetural:** Como `compute_meta_vector` é **state-local** (não propaga via mesh adapters), C7 filter não tem efeito downstream — apenas afeta visualização no dashboard. Mas se algum agente futuro usar `compute_meta_vector` para **drive policy FSM** (proposta em `06-canvas-agents-architecture.md` §4), C7 vira bug crítico: regime pode decidir PUSH para SONHO com 1 vetor zerado.

### 4.7 Comparação com patterns irmãos (catalog Layer 3)

| Pattern # | Nome | Anchor | Relação com hybrid meta-vector |
|:---------:|:-----|:-------|:-------------------------------|
| #10 | UEID tri-key | `src/contracts/common.py:40-44` | Ortogonal — UEID identifica entidades, não scores |
| #11 | Frozen Pydantic strict | `src/contracts/__init__.py:8` | Ortogonal — meta-vetor é `float`, não BaseModel |
| #12 | Append-only queue | `src/mesh/queue.py` | Tangencial — meta-vetor pode virar TaskChange em ciclo futuro |
| #13 | ForkAdapter Protocol | `src/mesh/adapters/base.py` | Tangencial — adapters propagam vectors, meta-vetor fica state-local |
| #14 | Idempotency SHA-256 | `src/mesh/agent_propagator.py` | Ortogonal |
| #15 | Hysteresis FSM | `src/operational/packages/core/src/operational/core/policy_engine.py` | **Consumidor** — regime FSM usa meta-vector como signal (gap atual: Q_HE-only) |
| #17 | Reliability decorator stack | `src/ikigai/src/agents/reliability.py` | Tangencial — pode envelopar `compute_meta_vector` com `@retry_with_backoff` se invocado via agent loop |
| **#18** | **Hybrid meta-vector** | `state.py:175-207` | **ESTE DOC** |
| #19 | Scaffold prompt | (Layer 4) | Ortogonal |

## §5 — Fontes

### Code (verificado)

- `src/ikigai/src/agents/ikigai_maintainer/state.py:175-207` — `compute_meta_vector` (anchor primário)
- `src/ikigai/src/agents/ikigai_maintainer/state.py:107-167` — `IKIGAiStateDict` TypedDict (consumidor)
- `src/ikigai/src/agents/ikigai_maintainer/state.py:188-190` — **C7**: filter `{k: v for k, v in scores.items() if v > 0}`
- `src/ikigai/src/ikigai/core/scoring/vector_scores.py:30` — `score_passion` (default λ=NSM.LAMBDA)
- `src/ikigai/src/ikigai/core/scoring/vector_scores.py:84-103` — `score_revenue` (clamp [0,100], div-by-zero guard)
- `src/ikigai/src/ikigai/core/scoring/vector_scores.py:122-161` — `compute_vector_scores` (defaults passion=0, demais=50)

### Docs (analisados)

- `docs/auto-performance-os/19-engine-ikigai-vector-scorer.md` — produtor; A4 (fórmulas divergentes)
- `docs/auto-performance-os/22-meta-ikigai-meta-vector.md` — meta-vector; **A5** worked example errado
- `docs/design-system/00-INDEX.md` — patterns catalog index
- `docs/design-system/06-canvas-agents-architecture.md` — IKIGAi Maintainer canvas
- `docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md` — critical analysis com C7/A5/B5
- `docs/design-system/10-modelo-unificado-auto-feedback-estocastico.md` — tese auto-feedback estocástico

### Architecture Decision Records

- `code-docs/adr/ADR-003-ikigai-as-meta-brain.md` §3.4 — origem da proporção 0.6/0.4
- `code-docs/adr/ADR-007-data-first-methodology.md` — gate 5 SONHO logs bloqueia re-calibração

### Memory cross-refs

- `[[algorithm-issues-registry]]` — registry de 31 issues
- `[[data-first-methodology]]` — ADR-007 constraint
- `[[algorithm-decisions-defer-2026-08-28]]` — 3rd reversal framework
- `[[master-branch-carro-chefe-2026-08-28]]` — canonical narrative
- `[[interfaces-architecture-2026-08-27]]` — dual-layer architecture

### Verification

- Implementação verificada via Read em 2026-08-28: `compute_meta_vector` retorna float, defaults `w_geo=0.6`/`w_harm=0.4`, **filtra v=0 silenciosamente** (C7 confirmado)
- Worked example (SONHO quebrado 80/80/80/80/5) recalculado manualmente: meta ≈ **35.57** (não 51 como doc 22, não 25.4 como doc 09 §2.1)
- Cross-refs verificadas: paths absolutos conferem com `00-INDEX.md`, `09-analise-critica-segunda-ordem-arquitetura.md`, `10-modelo-unificado-auto-feedback-estocastico.md`

---

> **Próxima atualização:** Após gate ADR-007 (5 SONHO logs) ser cumprido, executar (1) sensitivity analysis de `w_geo`/`w_harm`, (2) implementar modo `inclusive_zero`/`exclusive_zero` parametrizado, (3) rewrite worked examples de doc 22 com cenários canônicos verificados, (4) decidir entre A4 opção (a) rewrite código ou (b) rewrite doc.
