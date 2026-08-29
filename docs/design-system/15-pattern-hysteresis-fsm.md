# 15 — Pattern: Hysteresis FSM (Policy Engine 4-state)

> **⚠️ ADR-007 propagation note (2026-08-29):** References to "5 SONHO logs gate (ADR-007)" in this doc reflect a **propagated misconception**. ADR-007's "5+ manual logs per workflow" rule is **observation depth**, NOT a release gate. The actual gate for algorithm work is **system readiness** (backend + data + agent functional). Canonical clarification: `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/algorithm-gate-system-readiness-not-sonho-2026-08-29.md`. The deferral rule still applies here — this content is correctly deferred — but for the reason "system not ready," not "5 logs not reached."

> **Categoria:** Pattern #15 (Layer 3 — Patterns Catalog)
> **Anchor canônico:** `src/operational/packages/core/src/operational/core/policy_engine.py`
> **Anchor secundário:** `src/ikigai/src/ikigai/core/heuristics/regime.py` (versão IKIGAi 5-band)
> **Origem:** Síntese PRD-06 + Points_of_premisses §4 + análise crítica segunda ordem (findings C4, C5, C6, B4)
> **Idioma:** PT-BR prose + EN technical terms (FSM, Q_HE, hysteresis, IKIGAi, PAV, deep-agent, emergency threshold, regime, infractions, PUSH, MAINTAIN, REDUCE, RECOVER)
> **Público:** Eu mesmo + agentes futuros

---

## §1 — Intuição

A **Hysteresis FSM** é o controlador (Layer B do modelo unificado em `docs/design-system/10-modelo-unificado-auto-feedback-estocastico.md`) que decide **quão agressivamente** carregar o dia operacional. Sua intuição central é **assimetria intencional**: promover intensidade (upgrade) exige **3 dias consecutivos** acima do threshold, mas reduzir (downgrade) exige apenas **2 dias** — e entrar em modo de emergência (RECOVER) é **imediato** (1 dia) se `Q_HE < 0.30` ou `infractions >= 3`. A assimetria embute um **viés conservador para upgrade** (anti-overfit a um dia bom anômalo) e um **gatilho rápido para proteção** (anti-dano em fadiga real). O hysteresis counter funciona como **amortecimento bayesiano discreto**: após N observações consistentes, a posterior sobre o regime latente se concentra o suficiente para merecer uma transição; sem ele, 1 dia ruidoso alternaria regimes erraticamente (zig-zag). A escolha dos 3 valores (3-up / 2-down / 1-emergency) é **CHOICE** sem derivação teórica formal — flagged no finding B4 (`docs/auto-performance-os/09-analise-critica-segunda-ordem-arquitetura.md` §3.4), pendente de fit empírico via Bayesian Optimization após gate de 5 SONHO logs (ADR-007).

---

## §2 — Enunciado Formal

### 2.1 Estados e orçamento canônico

Quatro estados finitos, com **orçamento de tempo** determinado por regime (canônico em `RegimeType` docstring, `src/ikigai/src/ikigai/enums.py:86-89`):

| Estado | hardwork | pause | sleep target | Q_HE target |
|:-------|---------:|:-----:|:------------:|:-----------:|
| `PUSH` | 4.0 h | 10 min | 7.5 h | 0.85 |
| `MAINTAIN` | 2.5 h | 15 min | 8.0 h | 0.65 |
| `REDUCE` | 1.5 h | 20 min | 8.5 h | 0.45 |
| `RECOVER` | 0.5 h | 30 min | 9.0 h | 0.25 |

Orçamento **decresce monotonicamente** com proteção crescente — REDUCE é 3× mais leve que PUSH, RECOVER é 8× mais leve. **Invariante load-bearing:** `RegimeState` em `src/contracts/common.py:150-156` declara os 4 valores como `StrEnum` canônico cross-layer.

### 2.2 Thresholds e constantes (single source of truth aspiracional)

Operacional (`src/operational/packages/core/src/operational/core/policy_engine.py:99-105`):

```python
_RECOVER_QHE_CRITICAL: Final[float] = 0.30  # emergência
_RECOVER_INFRACTION_THRESHOLD: Final[int] = 3  # emergência
_PUSH_EARLY_WARNING_INFRACTIONS: Final[int] = 2  # canal secundário
```

IKIGAi hybrid (`src/ikigai/src/ikigai/constants.py:42-52`):

```python
Q_HE_PUSH: float = 0.85      # banda superior
Q_HE_REDUCE: float = 0.65    # banda intermediária (gap com doc 21 §2)
Q_HE_RECOVER: float = 0.60   # hard floor
HYSTERESIS_UPGRADE_DAYS: int = 3
HYSTERESIS_DOWNGRADE_DAYS: int = 2
```

**Gap documentado (finding C4, doc 09 §3.4):** `docs/auto-performance-os/21-meta-qhe-policy-mapping.md` §2 promete **4 bandas canônicas** (`[0.85, 1.0]` PUSH, `[0.70, 0.85)` MAINTAIN, `[0.60, 0.70)` REDUCE, `[0.0, 0.60)` RECOVER), mas o código operacional só implementa **3 thresholds efetivos** (PUSH ≥ 0.85, RECOVER < 0.60, e o intervalo `[0.60, 0.85)` é decidido por `compute_regime` IKIGAi em duas etapas, não pelo FSM). A banda `[0.70, 0.85)` MAINTAIN é derivada, não armazenada — single source of truth ausente.

### 2.3 Transições com histerese assimétrica (snippet verbatim)

Regras de transição implementadas em `src/operational/packages/core/src/operational/core/policy_engine.py:399-632` (função `evaluate_policy`), prioridade fixa:

```python
def evaluate_policy(
    current_state: PolicyState | None,
    qhe_metrics: QHEMetrics,
    history: list[PolicyDecision] | tuple[PolicyDecision, ...] = (),
    infraction_count: int = 0,
) -> PolicyEvaluation:
    qhe = qhe_metrics.qhe
    days_in_state = _count_days_in_state(history, current_state) if current_state is not None else 0

    # 1. Emergency RECOVER entry (highest priority, no histerese).
    if current_state != PolicyState.RECOVER and is_recover_entry_condition(qhe, infraction_count):
        return PolicyEvaluation(
            new_state=PolicyState.RECOVER,
            severity=Severity.CRITICAL,
            rationale=(f"RECOVER entry: qhe={qhe:.3f}, infractions={infraction_count}"),
            days_in_state=days_in_state,
            is_transition=True,
            previous_state=current_state,
        )

    # 5. PUSH transitions (early-warning downgrade on infractions).
    if current_state == PolicyState.PUSH:
        days_below_recover = consecutive_days_below_threshold(history, DEFAULT.QHE_RECOVER_THRESHOLD)
        if days_below_recover >= DEFAULT.POLICY_DOWNGRADE_DAYS:
            return PolicyEvaluation(
                new_state=PolicyState.MAINTAIN,
                severity=Severity.WARNING,
                rationale=(f"PUSH->MAINTAIN: qhe < {DEFAULT.QHE_RECOVER_THRESHOLD} "
                           f"for {days_below_recover} days"),
                days_in_state=days_in_state,
                is_transition=True,
                previous_state=current_state,
            )
        if infraction_count >= _PUSH_EARLY_WARNING_INFRACTIONS:
            return PolicyEvaluation(
                new_state=PolicyState.REDUCE,
                severity=Severity.WARNING,
                rationale=(f"PUSH->REDUCE: early warning, {infraction_count} infractions"),
                days_in_state=days_in_state,
                is_transition=True,
                previous_state=current_state,
            )
        ...
```

A versão IKIGAi (`src/ikigai/src/ikigai/core/heuristics/regime.py:113-189`, função `apply_hysteresis`) implementa **lógica equivalente** com `HYSTERESIS_UPGRADE_DAYS=3` / `HYSTERESIS_DOWNGRADE_DAYS=2`, mas tem um **canal adicional** — `hard floor: RECOVER if qhe < 0.60 + sleep_debt > 2h` (linha 54) — que combina sinais de Q_HE e dívida de sono antes de disparar.

### 2.4 Tabela de transições (consolidada)

| De → Para | Dias sustentados | Condição extra | Severidade | Snippet |
|:----------|:---------------:|:---------------|:-----------|:--------|
| `PUSH` → `MAINTAIN` | 2 | Q_HE < 0.60 sustentado | WARNING | `evaluate_policy` PUSH block, `policy_engine.py:587-602` |
| `PUSH` → `REDUCE` | 0 (imediato) | `infractions >= 2` (early warning) | WARNING | `policy_engine.py:603-611` |
| `MAINTAIN` → `PUSH` | 3 | Q_HE ≥ 0.85 sustentado | INFO | `policy_engine.py:551-562` |
| `MAINTAIN` → `REDUCE` | 2 | Q_HE < 0.60 sustentado | WARNING | `policy_engine.py:563-574` |
| `REDUCE` → `MAINTAIN` | 3 | Q_HE ≥ 0.85 sustentado | INFO | `policy_engine.py:510-521` |
| `REDUCE` → `RECOVER` | 2 | Q_HE < 0.60 sustentado | WARNING | `policy_engine.py:522-533` |
| `RECOVER` → `REDUCE` | 3 (exit) | Q_HE ≥ 0.60 sustentado | INFO | `policy_engine.py:480-492` |
| `*` → `RECOVER` | 0 (imediato) | Q_HE < 0.30 **ou** `infractions >= 3` | CRITICAL | `is_recover_entry_condition`, `policy_engine.py:261-287` |
| `None` → `MAINTAIN` | — | initial seed | INFO | `policy_engine.py:624-631` |

### 2.5 Invariantes load-bearing

| # | Invariante | Verificável |
|:--|:-----------|:-----------|
| **I1** | Upgrade (PUSH/MAINTAIN→higher) exige **N≥3** dias consecutivos acima do threshold | `consecutive_days_above_threshold(history, DEFAULT.QHE_PUSH_THRESHOLD) >= DEFAULT.POLICY_UPGRADE_DAYS` (`policy_engine.py:510, 551`) |
| **I2** | Downgrade (PUSH/MAINTAIN→lower) exige **N≥2** dias consecutivos abaixo | `consecutive_days_below_threshold(history, DEFAULT.QHE_RECOVER_THRESHOLD) >= DEFAULT.POLICY_DOWNGRADE_DAYS` (`policy_engine.py:522, 563, 591`) |
| **I3** | Emergency entry é **imediato e sem histerese** se `qhe < 0.30` ou `infractions >= 3` | `is_recover_entry_condition` retorna True (`policy_engine.py:287`) — curto-circuita ANTES de qualquer hysteresis counter |
| **I4** | Severity é determinística por transição: `INFO` (upgrade/stay), `WARNING` (qualquer entrada em REDUCE), `CRITICAL` (qualquer entrada em RECOVER) | Atribuição literal em cada branch de `evaluate_policy` (`policy_engine.py:212-214` + cada return) |
| **I5** | `RegimeDecision.hysteresis_applied` é `True` quando histerese reteve mudança proposta | Campo obrigatório do dataclass `RegimeDecision` em `regime.py:23` |

---

## §3 — Justificativa

### 3.1 Por que 3-up / 2-down / 1-emergência

**Por que assimetria (3 ≠ 2):** promover intensidade é mais arriscado do que reduzir. Se Q_HE sobe para 0.86 por um único dia (anomalia estatística), promover para PUSH imediatamente causaria sobrecarga injustificada nos 2 dias seguintes. Mas se cai para 0.55 (fadiga real), esperar 3 dias seria prejudicial — o usuário já está em espiral negativa e precisa de alívio rápido. A assimetria embute viés conservador para upgrade.

**Por que emergência em 1 dia:** crises reais (burnout agudo, infractions graves) precisam de resposta imediata. Esperar histerese em `infractions >= 3` (já são 3 violações) ou em `Q_HE < 0.30` (sinal extremo) seria negligência. A válvula de segurança é instantânea.

**Por que `Q_HE < 0.30` e não `< 0.60` na emergência:** a entrada em RECOVER por histerese usa 0.60 (sustentado 2 dias), mas a entrada de emergência usa 0.30 porque queremos distinguir **fadiga sustentada** (REDUCE após 2 dias) de **colapso agudo** (RECOVER imediato). Os dois thresholds são complementares, não redundantes.

### 3.2 Por que IKIGAi tem 5 bandas mas operacional tem 3

A versão IKIGAi (`src/ikigai/src/ikigai/core/heuristics/regime.py:27-41`) computa **regime bruto** por 5 bandas:
- `[0.85, ∞)` → PUSH (com Q_HE ≥ 0.85 + c_comp ≥ 0.90 + 0 infractions)
- `[0.70, 0.85)` → MAINTAIN
- `[0.60, 0.70)` → REDUCE (band explícita no IKIGAi; **ausente no operacional**)
- hard floor: RECOVER se Q_HE < 0.60 + sleep_debt > 2h
- default: RECOVER (conservador)

A versão operacional (`src/operational/packages/core/src/operational/core/policy_engine.py:399-632`) só distingue **3 thresholds efetivos**: PUSH (≥0.85), RECOVER (<0.60 sustentado), e emergency (<0.30 ou 3 infrações). O intervalo `[0.60, 0.85)` é decidido por `evaluate_policy` em duas etapas (compute_regime IKIGAi → apply_hysteresis), não por um threshold armazenado.

**Veredito:** o IKIGAi regime é **mais granular** (5 bandas explícitas) e **mais conservador** (default = RECOVER); o operacional é **mais simples** (3 thresholds) e **mais reativo** (emergency threshold 0.30). Ambos implementam a mesma FSM, mas com **granularidade de classificação diferente** — gap documentado em finding C4.

### 3.3 Por que `Q_HE_TARGET` é diferente em IKIGAi (`0.65` MAINTAIN) vs docs (`0.70-0.85` MAINTAIN)

`RegimeType` docstring (`src/ikigai/src/ikigai/enums.py:87`) lista MAINTAIN como `Q_HE_target=0.65`. `docs/auto-performance-os/21-meta-qhe-policy-mapping.md` §2 promete MAINTAIN como `[0.70, 0.85)`. Doc/code drift no coração da FSM — IKIGAi MAINTAIN é `[0.65, 0.85)` por código, mas doc 21 diz `[0.70, 0.85)`. Não há reconciliação.

### 3.4 Limitações conhecidas (citadas honestamente de doc 09)

| Finding | Sev | Limitação | Recomendação |
|:--------|:---:|:----------|:-------------|
| **B4** | M | Hysteresis constants 3-up/2-down **injustificados** (sem teoria de controle subjacente) | BO sobre `θ ∈ {2, 3, 4, 5}` após 5 SONHO logs |
| **C4** | M | Doc 21 4-band mapping **não implementado** — banda REDUCE `[0.60, 0.70)` ausente no operacional | Introduzir `policy_thresholds.py` com 4 constantes nomeadas |
| **C5** | M | Doc 14 §2 invariante "REDUCE nunca é escolhido por Q_HE sozinho" — código operacional permite MAINTAIN→REDUCE puramente por Q_HE (`policy_engine.py:563-574`) | Atualizar doc 14 OU introduzir infractions como pré-condição para entrar em REDUCE |
| **C6** | M | Doc 14 §2 invariante "PUSH→RECOVER direto proibido" — emergency check **bypassa** a proibição (`policy_engine.py:467-475`) | Atualizar doc 14 para explicitar que emergency é exceção constitucional |

### 3.5 Trade-offs

- **Prós:** determinístico (idempotência perfeita), testável (função pura), audit-friendly (decision log frozen Pydantic), anti-zig-zag (hysteresis bayesiano discreto).
- **Contras:** parameter-free of empirical content (todas constantes são CHOICE — finding B4), não explora alternativas (UCB exploration ausente — finding E9), gap entre doc 21 (4-band) e operacional (3-band) é silencioso até runtime.

### 3.6 Por que este padrão vence alternativas

| Alternativa | Por que rejeitada |
|:------------|:------------------|
| **Single threshold (não FSM)** | Não distingue fadiga sustentada (REDUCE) de colapso agudo (RECOVER) — mesma resposta para sinais qualitativamente diferentes |
| **Symmetric hysteresis (3-up/3-down)** | Burlaria o viés conservador — 3 dias de fadiga sustentada antes de downgrade é longo demais para fadiga real |
| **ML-based regime classifier** | Viola global invariant "zero LLM in pipeline" — pure arithmetic only (`CLAUDE.md` §1, repo root) |
| **Continuous control (não discreto)** | Orçamento por regime precisa ser discreto (8h vs 6h vs 4h vs 2h) para alocação de tempo humano — controle contínuo (e.g., PID) seria semanticamente errado |

---

## §4 — Cross-references

### Design System (camadas 1-3)

- `docs/design-system/00-INDEX.md` — index navegável do docset (Layer 0)
- `docs/design-system/04-canvas-mesh-architecture.md` — mesh como actuator do regime (forks recebem `policy:<regime>` tag)
- `docs/design-system/05-canvas-contracts-architecture.md` — `RegimeState` em `src/contracts/common.py:150-156` + `PolicyDecision` em `src/contracts/task_change.py`
- `docs/design-system/06-canvas-agents-architecture.md` — IKIGAi maintainer expõe regime via deep-agent
- `docs/design-system/07-canvas-sync-architecture.md` — sync throttle em RECOVER (`policy_throttle_recover_minutes=60`)
- `docs/design-system/08-canvas-cybernetic-loop.md` — ADJUSTER step = `PolicyEngine.evaluate()`; §4.3 cita este pattern por referência
- `docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md` §3.4 — qualificação do pattern (C4, C5, C6); §G lista 14 constantes como CHOICE
- `docs/design-system/10-modelo-unificado-auto-feedback-estocastico.md` §3.5 — política ótima π*(s) **codificada** como 4-state FSM (não aprendida); §3.6 inversão bayesiana discreta via hysteresis counter; §7.2 hysteresis como amortecimento bayesiano

### Auto-performance-os (matemática)

- `docs/auto-performance-os/03-axiom-finite-state-machines.md` — base matemática de FSMs
- `docs/auto-performance-os/04-axiom-ordering-relations.md` — assimetria = ordem parcial
- `docs/auto-performance-os/14-engine-policy-engine-fsm.md` §2 — tabela de transição (3-up/2-down/1-emergência); §3 justificativa não-técnica
- `docs/auto-performance-os/21-meta-qhe-policy-mapping.md` §2 — **4-band mapping que NÃO está implementado** (finding C4)

### Code anchors

- `src/operational/packages/core/src/operational/core/policy_engine.py:399-632` — `evaluate_policy` (coração do FSM)
- `src/operational/packages/core/src/operational/core/policy_engine.py:261-287` — `is_recover_entry_condition`
- `src/operational/packages/core/src/operational/core/policy_engine.py:290-364` — `consecutive_days_*_threshold` (hysteresis helpers)
- `src/operational/packages/core/src/operational/core/policy_engine.py:99-109` — constantes `_RECOVER_QHE_CRITICAL`, `_RECOVER_INFRACTION_THRESHOLD`, `_PUSH_EARLY_WARNING_INFRACTIONS`
- `src/operational/packages/core/src/operational/core/policy_engine.py:170-213` — `Severity` enum (3-tier subset: INFO/WARNING/CRITICAL)
- `src/ikigai/src/ikigai/core/heuristics/regime.py:27-110` — `compute_regime` (versão IKIGAi 5-band)
- `src/ikigai/src/ikigai/core/heuristics/regime.py:113-189` — `apply_hysteresis` (versão IKIGAi 3-up/2-down)
- `src/ikigai/src/ikigai/constants.py:42-52` — `NSM.Q_HE_PUSH=0.85`, `NSM.Q_HE_REDUCE=0.65`, `NSM.Q_HE_RECOVER=0.60`, hysteresis constants
- `src/ikigai/src/ikigai/enums.py:82-94` — `RegimeType` enum + orçamento por regime
- `src/contracts/common.py:150-156` — `RegimeState` (canônico cross-layer)

### Memory cross-refs

- `[[algorithm-issues-registry]]` — 31 issues + 12 novos (F1-F12); A02 debate sobre emergency threshold 0.30 vs 0.60
- `[[algorithm-decisions-defer-2026-08-28]]` — defer algorithm polish (incluindo hysteresis constants) até dado empírico
- `[[data-first-methodology]]` — gate de 5 SONHO logs antes de qualquer BO sobre θ
- `[[master-branch-carro-chefe-2026-08-28]]` — regime agora é decisão do deep-agent, não do FSM isolado
- `[[interfaces-architecture-2026-08-27]]` — regime propaga para forks via `policy:<regime>` tag em tasks
- `[[prioritize-backend-over-algorithm-refinement]]` — build backend antes de refinar thresholds (3-up/2-down ficam CHOICE)

---

## §5 — Fontes

### Code (verificado)

- `src/operational/packages/core/src/operational/core/policy_engine.py` — 4-state FSM (operational, 3-threshold)
- `src/ikigai/src/ikigai/core/heuristics/regime.py` — `compute_regime` + `apply_hysteresis` (IKIGAi, 5-band)
- `src/ikigai/src/ikigai/constants.py:42-52` — NSM constants
- `src/ikigai/src/ikigai/enums.py:82-94` — `RegimeType` (orçamento por regime)
- `src/contracts/common.py:150-156` — `RegimeState` (cross-layer canonical)

### Docs (analisados)

- `docs/auto-performance-os/03-axiom-finite-state-machines.md` — base FSM
- `docs/auto-performance-os/04-axiom-ordering-relations.md` — ordem parcial
- `docs/auto-performance-os/14-engine-policy-engine-fsm.md` — doc canônico (com drift C5/C6)
- `docs/auto-performance-os/21-meta-qhe-policy-mapping.md` — 4-band mapping (não implementado, finding C4)
- `docs/design-system/08-canvas-cybernetic-loop.md` — ADJUSTER step
- `docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md` §3.4 — qualificação + findings B4/C4/C5/C6
- `docs/design-system/10-modelo-unificado-auto-feedback-estocastico.md` §3.5/§7.2 — π*(s) codificada + amortecimento bayesiano

### Memory

- `[[algorithm-issues-registry]]` — 43 issues total (31 + F1-F12); A02 emergency threshold
- `[[data-first-methodology]]` — ADR-007 5 SONHO logs gate
- `[[algorithm-decisions-defer-2026-08-28]]` — 3rd reversal M01/N01/A02/A06; defer θ
- `[[prioritize-backend-over-algorithm-refinement]]` — backend > algorithm polish
- `[[interfaces-architecture-2026-08-27]]` — regime tag propaga para forks-prontas
- `[[master-branch-carro-chefe-2026-08-28]]` — deep-agent como canonical, regime como decisão do agent

### Theory

- Auer, Cesa-Bianchi, Fischer (2002) — UCB1 finite-time analysis (conexão com `ucb_recalibrator.py` ausente — finding E9)
- Sutton & Barto (2018) — Reinforcement Learning cap. 3 (finite MDPs), cap. 6 (TD learning) — base para hysteresis como amortecimento bayesiano
- Shahriari et al. (2016) — Bayesian Optimization (gate para refit θ após 5 SONHO logs)

---

## §6 — Metadados

- **Versão:** 2026-08-28
- **Origem:** Pattern doc 15 do design system híbrido (Layer 3 — Patterns Catalog)
- **Anchor primário:** `src/operational/packages/core/src/operational/core/policy_engine.py` (coração do FSM)
- **Cross-refs principais:** doc 09 §3.4 (qualificação), doc 10 §3.5/§7.2 (modelo unificado), doc 14 §2 (canônico), doc 21 §2 (drift C4)
- **Status:** DRAFT (5 invariantes verificáveis, 2 findings ativos C4/C5/C6/B4, gate BO pendente ADR-007)
- **Próximo:** implementar `policy_thresholds.py` (proposta doc 09 §3.4) OU rewrite doc 21 §2 para refletir 3-band real
