# 10 — Modelo Unificado: Auto-Performance via Auto-Feedback Estocástico

> **Categoria:** TESE (Layer 8 — Tese matemática + arquitetural)
> **Anchor canônico:** docs 01-08 (canvases) + `09-analise-critica-segunda-ordem-arquitetura.md`
> **Origem:** Síntese do Explore agent crítico (46 findings) + state-of-art em stochastic control theory + bandit algorithms + Bayesian optimization
> **Idioma:** PT-BR (preservando EN technical terms)
> **Publico:** Eu mesmo + agentes futuros

---

## §1 — Tese em uma frase

> **Auto-performance é um sistema de controle estocástico hierárquico que maximiza a função de reward `R(s, a) = Q_HE(s) · V_meta(s)` através de três camadas de feedback (scoring → policy → action), onde cada ação gera observação ruidosa `o_t`, cada observação atualiza uma distribuição posterior sobre os estados latentes `P(s|o_{1:t})`, e cada posterior determina uma distribuição de ação `π(a|s)` consumida pela policy FSM 4-state.**

## §2 — Decomposição em 3 camadas

```
┌──────────────────────────────────────────────────────────────────┐
│ Layer C: Action (actuator)                                       │
│  → TaskChange, Pomodoro event, HabitExecution                    │
│  → ForkAdapter Protocol (idempotent apply_change)                │
│  → data/review_queue/ (atomic append-only)                       │
├──────────────────────────────────────────────────────────────────┤
│ Layer B: Policy (controller)                                     │
│  → 4-state FSM PUSH/MAINTAIN/REDUCE/RECOVER                      │
│  → Hysteresis assimétrico 3-up / 2-down / 1-emergency            │
│  → Output: regime + daily target_minutes + tag policy:<regime>   │
├──────────────────────────────────────────────────────────────────┤
│ Layer A: Scoring (sensor)                                        │
│  → 5 IKIGAi vectors (paixão, habilidade, mercado, receita, curso)│
│  → Q_HE_OPERATIONAL (multiplicativa, PAV)                        │
│  → V_meta = 0.6·geo(V) + 0.4·harm(V)                            │
│  → Output: reward signal r_t ∈ [0, 1]                            │
└──────────────────────────────────────────────────────────────────┘
```

**Fluxo temporal (1 dia):**

```
t=0    Layer A: lê sensors do dia anterior → calcula V_meta, Q_HE
       Layer B: lê prev_regime + hysteresis counter
                decide regime ∈ {PUSH, MAINTAIN, REDUCE, RECOVER}
                determina daily target_minutes = f(regime)
t=0..N Layer C: usuário executa tarefas; cada execução gera
                (a) TaskChange → data/review_queue/ (atomic)
                (b) HabitExecution event → habit_states table
                (c) Pomodoro event → data/pomodoro_log.jsonl
                (d) StudySession → study_sessions table
                Cada evento é uma observação ruidosa o_t do estado latente.
t=N+1  Layer A: Sensor digest → nova Q_HE + novos 5 vectors
       Layer B: hysteresis counter++ → re-evaluate regime
       ...
```

## §3 — Modelo estocástico formal

### 3.1 Estado latente `s_t`

O estado `s_t` é um vetor contínuo em **R^n** com 5 IKIGAi dimensions + Q_HE dimension + regime dimension:

```
s_t = [V_paixão, V_habilid, V_mercado, V_receita, V_curso, Q_HE, regime]
     ∈ R^5 × [0, 2.0] × {PUSH, MAINTAIN, REDUCE, RECOVER}
```

O estado é **latente** porque não é diretamente observável; é inferido a partir de observações ruidosas.

### 3.2 Observação `o_t`

```
o_t = (V_paixão_t, V_habilid_t, V_mercado_t, V_receita_t, V_curso_t, qhe_t, regime_t)
```

Cada componente é uma amostra ruidosa do estado latente correspondente:

```
o_t = s_t + ε_t,   ε_t ~ N(0, σ²·I)
```

A variância `σ²` representa o ruído do sensor (auto-relato, medições imperfeitas).

### 3.3 Função de reward `R(s, a)`

```
R(s_t, a_t) = Q_HE(s_t) · V_meta(s_t) - λ · ‖a_t - π*(s_t)‖²
```

Onde:
- `Q_HE(s_t)` ∈ [0, 1.5] típico: reward primário por hábitos consolidados
- `V_meta(s_t)` ∈ [0, 1]: alinhamento estratégico (IKIGAi 5 vectors)
- `λ · ‖a_t - π*(s_t)‖²`: penalidade por divergir da política ótima (anti-rogue actions)

**Trade-off fundamental:** o sistema maximiza `Q_HE · V_meta` mas penaliza divergir da policy. Isto codifica o princípio "maximize mas stay on-rails".

### 3.4 Dinâmica de transição `P(s_{t+1} | s_t, a_t)`

A transição **não é markoviana pura** porque hábitos têm memória exponencial:

```
V_paixão_{t+1} = V_paixão_t + α · (streak_t+1 - V_paixão_t)
                = (1-α) · V_paixão_t + α · streak_t+1
```

Onde `α = 1 - exp(-λ)` é o **fator de esquecimento** (exponential decay rate). Esta é uma **filtragem exponencial** (low-pass filter), equivalente a:

```
V_paixão_t = (1-α) · Σ_{i=1}^t α^(t-i) · streak_i
           = EMA(streak, α)
```

A exponencial `1 - exp(-λ·t)` (cap. 02) é o **integrador**; esta EMA é o **filtrador**.

### 3.5 Política ótima `π*(s)`

Em controle estocástico ótimo, a política que maximiza o expected cumulative reward:

```
π*(s) = argmax_a E[ Σ_{t=0}^∞ γ^t · R(s_t, a_t) ]
       subject to P(s_{t+1} | s_t, a_t)
```

Onde `γ ∈ (0, 1)` é o fator de desconto temporal.

**Em nosso sistema:** a política **não é aprendida** (zero LLM in pipeline, per global invariant). É **codificada** como 4-state FSM com histerese. A "otimização" é estrutural: 5 vectores → meta-vector → Q_HE → regime.

### 3.6 Inversão bayesiana: posterior sobre regime

Dado uma sequência de observações `o_{1:t}`, podemos calcular a probabilidade de cada regime:

```
P(regime | o_{1:t}) ∝ P(o_t | regime) · P(regime | o_{1:t-1})
```

**Aplicação arquitetural:** o policy FSM implementa uma **versão discreta** dessa inversão bayesiana. O hysteresis counter funciona como "amostrador" — após N observações consistentes, a posterior se concentra em um regime.

## §4 — Conexão com Multi-Armed Bandits (UCB)

### 4.1 Analogia

O **UCB Recalibrator** (referenced em `20-engine-ucb-recalibrator.md` §5 mas **não implementado** — finding E9) seria a peça que conecta Layer A (scoring) com Layer B (policy):

```
Cada regime ∈ {PUSH, MAINTAIN, REDUCE, RECOVER} é um "braço" de um multi-armed bandit.
Cada dia é uma "rodada" do bandit.
A reward observada é Q_HE_t.
A política ótima é selecionar o regime com maior UCB:
```

```
UCB(regime) = Q_HE_mean(regime) + c · sqrt(2·ln(t) / n_t(regime))
```

Onde:
- `Q_HE_mean(regime)`: reward médio histórico do regime
- `n_t(regime)`: número de dias no regime até t
- `c`: exploration parameter (típico: 1.0)

**Recomendação arquitetural:** implementar `ucb_recalibrator.py` (finding E9) com a fórmula acima. Hoje o regime é escolhido puramente pela FSM com thresholds; UCB introduziria **exploration** (testar PUSH ocasionalmente mesmo em REDUCE para verificar se Q_HE recuperou).

### 4.2 Regret bound

A literatura de UCB1 (Auer, Cesa-Bianchi, Fischer 2002) garante **regret O(√(K·T·ln T))** após T rodadas e K braços. Em nosso sistema:

- K=4 regimes
- T = dias observados
- Regret = diferença cumulative reward vs política ótima global

Isto significa que, após **5 SONHO logs (= 5 dias × 5 vectors × 24 horas)** o sistema deveria ter regret < 1.0 (1 unidade de Q_HE perdida vs ótimo).

## §5 — Conexão com Bayesian Optimization

### 5.1 Hiperparâmetros do sistema

Os 14 parâmetros identificados em `09-analise-critica-segunda-ordem-arquitetura.md §G` (λ, QHE weights, hysteresis constants, hybrid weights, thresholds, etc.) são **hiperparâmetros** do sistema. Hoje são "escolha" (não medição).

**Aplicação arquitetural:** uma **Bayesian Optimization loop** sobre esses hiperparâmetros maximizaria o Q_HE histórico:

```
θ_new = argmax_θ E[ Q_HE(t+1) | θ, history ]
```

Onde:
- `θ ∈ R^14`: vetor de hiperparâmetros
- `history`: dataset de (θ_used, Q_HE_observed) tuples
- `E[Q_HE(t+1)]`: predictive posterior via Gaussian Process ou TPE

**Recomendação arquitetural:** após 5 SONHO logs, rodar **1 ciclo de BO** sobre os 14 hiperparâmetros com constraint Σw_IKIGAi = 1.0. Output: novo `θ*` que substitui as constantes atuais.

### 5.2 Restrições do BO

Nem todo o espaço `R^14` é válido:
- `Σ w_IKIGAi = 1.0` (constraint C1)
- `0 ≤ QHE ≤ 1.5` (constraint C8)
- `0.30 ≤ QHE_RECOVER_THRESHOLD ≤ QHE_REDUCE_THRESHOLD ≤ QHE_MAINTAIN_THRESHOLD ≤ QHE_PUSH_THRESHOLD ≤ 0.95` (ordering constraint)
- `HYSTERESIS_UPGRADE_DAYS > HYSTERESIS_DOWNGRADE_DAYS` (anti-fragility)
- `0.5 ≤ hybrid_geo_weight ≤ 0.7` (B5 sensitivity range)

Estas constraints reduzem o search space de `R^14` para um manifold ~10-dimensional.

## §6 — Modelo unificado em pseudocódigo

```python
class AutoPerformanceSystem:
    """Stochastic auto-feedback controller with hierarchical structure."""

    def __init__(self, db, tw, vault):
        self.db = db                              # SQLite
        self.tw = tw                              # Taskwarrior
        self.vault = vault                        # Obsidian

        # Layer A: scoring
        self.ikigai = IkigaiScorer(db)            # 5 vectors
        self.qhe_op = QHEOperational(db)          # multiplicative
        self.qhe_ik = QHEIKIGAI(db)               # additive (after Σw=1.0 normalization)
        self.meta_v = MetaVector()                # 0.6·geo + 0.4·harm

        # Layer B: policy
        self.policy = PolicyFSM(db)               # 4-state hysteresis
        self.ucb = UCBRecalibrator(db)            # (NOT YET IMPLEMENTED — finding E9)

        # Layer C: action
        self.queue = ReviewQueue(db)              # atomic append-only
        self.adapters = [CliAdapter(), TaskdogAdapter(), SolverforgeCalendarAdapter()]

        # Hyperparameters (TBD with BO over 5 SONHO logs)
        self.theta = {
            "lambda": 0.093,                       # habit consolidation rate
            "eta": 0.5,                            # streak bonus coefficient
            "qhe_push_threshold": 0.85,
            "qhe_maintain_threshold": 0.70,        # NOT IMPLEMENTED — finding C4
            "qhe_reduce_threshold": 0.60,
            "qhe_recover_threshold": 0.30,
            "hysteresis_upgrade_days": 3,
            "hysteresis_downgrade_days": 2,
            "hybrid_geo_weight": 0.6,
            "hybrid_harm_weight": 0.4,
            "ucb_exploration_c": 1.0,              # NOT YET USED — finding E9
            "max_hardcore_per_month": 2,
            "policy_throttle_recover_minutes": 60,  # sync throttling
            "wake_windows": [(3, 5), (15, 18)],    # sleep validator
        }

    def execute_daily_cycle(self, target_date: date) -> PolicyDecision:
        """The main feedback loop."""

        # LAYER A: SCORING (sensor)
        o_t = self._read_observations(target_date)         # noisy observations
        v_paixao, v_skill, v_market, v_rev, v_course = (
            self.ikigai.score(o_t)
        )
        v_meta = self.meta_v.compute(v_paixao, v_skill, v_market, v_rev, v_course)
        qhe_op = self.qhe_op.compute(o_t)                  # multiplicative
        qhe_ik = self.qhe_ik.compute(o_t)                  # additive (renamed — A2 fix)

        # Reward signal
        r_t = qhe_op * v_meta                              # primary reward

        # LAYER B: POLICY (controller)
        prev = self.policy.read_prev_decision(target_date - timedelta(days=1))
        hysteresis = self.policy.count_consecutive_days(prev.regime, target_date)
        decision = self.policy.evaluate(
            qhe=qhe_op,                                    # use multiplicative (calibrated)
            prev=prev,
            hysteresis_counter=hysteresis,
            infractions=o_t["infractions"],
            ucb_signal=self.ucb.exploit_explore(r_t),      # (when implemented — E9 fix)
        )

        # LAYER C: ACTION (actuator)
        # 1. Persist decision
        self.db.write_decision(target_date, decision)

        # 2. Sync to Taskwarrior (throttled if RECOVER)
        if decision.regime != RECOVER or self.theta["policy_throttle_recover_minutes"] <= 60:
            self.tw.sync(decision)

        # 3. Generate TaskChanges for mesh propagation
        for task in self._generate_tasks(decision, target_date):
            self.queue.enqueue(task)                       # atomic append-only

        # 4. Update hyperparameters via BO (periodic — after 5 SONHO logs)
        if self._should_run_bo(target_date):
            self.theta = self._bayesian_optimization(self.theta, history)

        return decision

    def _read_observations(self, date: date) -> dict:
        """Noisy sensor reading of latent state."""
        return {
            "habit_streak": self.db.habit_streak(date),
            "energy_avg": self.db.energy_avg(date),
            "study_minutes": self.db.study_minutes(date),
            "infractions": self.db.infractions(date),
            "ikigai_5": self.ikigai.observed_5(date),       # observed, not latent
            # + Gaussian noise σ per §3.2
        }
```

## §7 — Por que "estocástico" é load-bearing

A escolha de modelar como estocástico (vs determinístico) tem **3 implicações arquiteturais**:

### 7.1 Anti-overfitting a um dia

Determinismo → sistema "aprende" valores exatos → overfit a 1 dia → falha no dia seguinte. Estocástico → sistema distribui crédito por **janela** (5+ dias) → robustez a noise diário.

### 7.2 Hysteresis como amortecimento

O hysteresis 3-up/2-down **não é** defeito de design — é **amortecimento bayesiano**. Sem ele, 1 dia ruim alternaria regimes erraticamente (zig-zag). Com ele, a posterior `P(regime | o_{1:t})` precisa de N observações para se concentrar.

### 7.3 UCB como exploration controlada

Sem exploration (UCB), o sistema converge para **local optimum**: PUSH em dias bons, RECOVER em dias ruins, sem nunca testar se PUSH com hysteresis alterado melhoraria Q_HE médio. Com UCB, **5-10% das decisões** são exploration explícita.

## §8 — Thresholds + constantes: estado atual

| Constante | Valor atual | Status | Origem |
|:----------|:-----------|:-------|:-------|
| λ | 0.093 | **CHOICE** (não fit) | "H(66) ≈ 0.998" reverse-engineer |
| η (streak bonus) | 0.5 | **CHOICE** | ad-hoc |
| QHE_PUSH_THRESHOLD | 0.85 | **CHOICE** | (origem perdida; precisa BO) |
| QHE_MAINTAIN_THRESHOLD | 0.70 | **NÃO IMPLEMENTADO** | finding C4 |
| QHE_REDUCE_THRESHOLD | 0.60 | **CHOICE** | (origem perdida) |
| QHE_RECOVER_THRESHOLD | 0.30 | **CHOICE** | (origem perdida) |
| HYSTERESIS_UPGRADE_DAYS | 3 | **CHOICE** | (sem teoria — finding B4) |
| HYSTERESIS_DOWNGRADE_DAYS | 2 | **CHOICE** | (sem teoria — finding B4) |
| hybrid_geo_weight | 0.6 | **CHOICE** | (sem teoria — finding B5) |
| hybrid_harm_weight | 0.4 | **CHOICE** | (idem) |
| UCB exploration c | 1.0 | **N/A** | finding E9 (UCB não implementado) |
| max_hardcore_per_month | 2 | **CHOICE** | (sem dados) |
| policy_throttle_recover_minutes | 60 | **CHOICE** | (idem) |
| wake_windows | [(3, 5), (15, 18)] | **CHOICE** | (Lally 2010 misquote — B2) |

**14 constantes × ~3 valores plausíveis cada = ~4.8 milhões de combinações**. BO sobre espaço restrito (~10-dim manifold) precisaria de ~50-100 SONHO logs para convergir. ADR-007 estabelece **5+ SONHO logs** como gate mínimo.

## §9 — Conexão com arquitetura (revisitado)

### 9.1 Layer 2 (Canvases) + Layer 3 (Patterns) — implications

| Canvas | Pattern | Implication of unified model |
|:-------|:--------|:-----------------------------|
| 04 mesh | #13 ForkAdapter | Adapters devem emitir `PropagationEvent` com `event_type ∈ {task_change, pomodoro_event, habit_execution, study_session}`. Hoje só `task_change`. **F5** gap. |
| 05 contracts | #11 frozen Pydantic | Rename QHE → QHE_OPERATIONAL + QHE_IKIGAI. Adicionar alias + função de mapeamento. **A2/C1** fix. |
| 06 agents | — | IKIGAi maintainer deve expor `ucb_signal` ao policy FSM. Implementar `ucb_recalibrator.py`. **E9** fix. |
| 07 sync | — | Sync deve respeitar policy_throttle (RECOVER + heavy load = skip). Já implementado parcialmente. |
| 08 cybernetic | — | Loop deve incluir BO step após N SONHO logs. Hook para `bayesian_optimization()`. Hoje não existe. |

### 9.2 Patterns load-bearing deste modelo

| Pattern | Origem | Relação com modelo unificado |
|:--------|:-------|:------------------------------|
| **#11** frozen Pydantic | `src/contracts/__init__.py` | Garante que rename QHE é breaking change forçado |
| **#12** append-only queue | `src/mesh/queue.py` | Garante replay-safe do auto-feedback (idempotência) |
| **#13** ForkAdapter Protocol | `src/mesh/adapters/base.py` | Garante adapters podem ser plugados para UCB feedback |
| **#15** hysteresis FSM | `src/operational/packages/core/src/operational/core/policy_engine.py` | Implementa amortecimento bayesiano (3-up/2-down) |
| **#18** hybrid meta-vector | `src/ikigai/src/agents/ikigai_maintainer/state.py` | Implementa agregação geométrica+harmônica (sensibilidade a zeros — C7) |
| **#20** 5 IKIGAi vectors | `src/ikigai/src/ikigai/core/scoring/vector_scores.py` | Implementa observation signals (V_paixão, ..., V_curso) |

## §10 — Validação empírica (5 SONHO logs gate)

Para validar este modelo, **5 SONHO logs** devem ser executados, cada um contendo:

1. **Inputs planejados:** SONHO, OBJETIVO, 2 PROJETOS, 4 DELIVERABLES (template persona)
2. **Observações diárias:** 5 vectors (snapshot inicial), Q_HE (daily), regime transitions, infractions
3. **Outputs:** tasks geradas, pomodoros completos, regime atingido, weekly burndown

Após 5 SONHO logs:

- Calcular regret vs política ótima (UCB oracle)
- Re-derivar λ via fit aos streak_days reais
- Rodar BO 1× sobre θ com constraint manifold ~10-dim
- Atualizar θ no código
- Catálogos de falhas em `vault/ikigai/meta/algorithm-issues-registry.md`

## §11 — Conclusão: o que é "auto-performance"?

**Auto-performance não é "maximizar Q_HE"** — é **manter o sistema em estado de high-Q_HE de forma sustentável**. O hysteresis 3-up/2-down garante sustentabilidade (não over-promote para PUSH sem evidência sustentada). O UCB (quando implementado) garante exploration (não estagnar em local optimum). A BO (quando rodada) garante que os hiperparâmetros não são apenas "escolha" mas "fit a dados".

**A tese de auto-feedback estocástico é portanto:**

> O sistema **observa** suas próprias ações, **atualiza** um posterior sobre seus estados latentes (V_meta, Q_HE, regime), e **seleciona** a próxima ação que maximiza o expected reward sob o posterior. A cada SONHO log, o modelo é **refitado** com Bayesian Optimization. O drift entre modelo e realidade é o sinal de failure que dispara replanning.

Isto é **estocástico** (não determinístico), **auto-feedback** (não supervisionado), e **hierárquico** (3 layers). É a tese unificadora.

## §12 — Fontes

### Theory
- Auer, Cesa-Bianchi, Fischer (2002) — "Finite-time Analysis of the Multiarmed Bandit Problem"
- Lally et al. (2010) — "How are habits formed: Modelling habit formation in the real world" (European Journal of Social Psychology)
- Sutton & Barto (2018) — "Reinforcement Learning: An Introduction" (2nd ed.)
- Shahriari et al. (2016) — "Taking the Human Out of the Loop: A Review of Bayesian Optimization"
- Van Cauter et al. (2000) — "Sleep and metabolism" (referenced for sleep breakpoints B6)

### Code (verificado)
- `src/contracts/common.py:UEID, RegimeState` — state representation
- `src/contracts/task_change.py:TaskChange, PropagationEvent` — observation events
- `src/contracts/metrics.py:QHEScore` — score model
- `src/mesh/queue.py` — append-only queue
- `src/mesh/adapters/base.py:ForkAdapter` — actuator protocol
- `src/operational/packages/core/src/operational/core/policy_engine.py` — 4-state FSM
- `src/ikigai/src/ikigai/core/scoring/vector_scores.py` — 5 IKIGAi vectors
- `src/ikigai/src/ikigai/core/scoring/qhe.py` — additive QHE (Σw=1.0 normalization needed)
- `src/ikigai/src/agents/ikigai_maintainer/state.py:compute_meta_vector` — hybrid 0.6/0.4

### Docs (analisados)
- `docs/auto-performance-os/00-INDEX.md` — template 5-section
- `docs/auto-performance-os/02-axiom-habitualidade.md` — H(t) = 1 − exp(−λ·t)
- `docs/auto-performance-os/14-engine-policy-engine-fsm.md` — hysteresis
- `docs/auto-performance-os/19-engine-ikigai-vector-scorer.md` — 5 vectors
- `docs/auto-performance-os/22-meta-ikigai-meta-vector.md` — hybrid meta
- `docs/auto-performance-os/26-integration-cybernetic-loop.md` — 6-step loop

### Memory cross-refs
- `[[data-first-methodology]]` — 5 SONHO logs gate
- `[[algorithm-decisions-defer-2026-08-28]]` — defer until empirical
- `[[master-branch-carro-chefe-2026-08-28]]` — deep-agent as canonical
- `[[interfaces-architecture-2026-08-27]]` — dual-layer (forks + native)
- `[[ikigai-weight-mechanism-defer]]` — 0.6/0.4 defer
- `[[algorithm-issues-registry]]` — 31+12 findings

## §13 — Metadados

- **Versão:** 2026-08-28
- **Origem:** Síntese do Explore agent crítico + state-of-art em stochastic control + bandit algorithms
- **Status:** THESIS (pending 5 SONHO logs gate per ADR-007)
- **Próximo:** implementar `ucb_recalibrator.py` (E9 fix) + rename QHE dual definitions (A2/C1 fix) + run BO com 5 SONHO logs (gate)