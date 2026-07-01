"""Next step advisor — pure function.

Computes a single, actionable suggestion for the user based on today's
:func:`operational.cli.services.DaySnapshot`. The output is a 2-line
observation + action (matching the design system's "Next Step v2"
spec in ``docs/design-system/DESIGN-SYSTEM.md`` §4.10).

Anti-fragile: every code path explicitly handles missing data (empty
state) and returns a safe default. No exceptions escape.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from operational.core.budget import classify_quadrant


@dataclass(frozen=True)
class NextStep:
    """Two-line next step: observation + action.

    Wireframe (from DESIGN-SYSTEM §4.10):
        OBSERVACAO: Q1 mantido por 5 dias consecutivos.
        ACAO:       Aumentar pomodoros de 12 para 14 (gradual).
    """

    observation: str
    action: str
    severity: str = "primary"  # one of: primary, success, warning, danger, info


# ---------------------------------------------------------------------------
# Threshold constants (anti-fragile defaults from PAV V3 spec)
# ---------------------------------------------------------------------------

SLEEP_TARGET_H = 8.0
SLEEP_DEBT_THRESHOLD = -1.0  # hours vs target that triggers a warning
POMODORO_META_TYPICAL = 12
ENERGY_LOW_THRESHOLD = 4
FOCUS_LOW_THRESHOLD = 5
HARDWORK_UNDER_PERCENT = 50  # < 50% of orcado triggers "behind" advice


def _empty_step() -> NextStep:
    """Default step when there's no data to base advice on."""
    return NextStep(
        observation="Sem dados para hoje — comece registrando sono e rotinas.",
        action="Rode `pav demo seed` para popular dados de exemplo, ou `pav metric sleep` para começar.",
        severity="info",
    )


def _classify_severity(x: float, y: float) -> str:
    """Map (x, y) to severity used by the NextStep panel border."""
    quad, _, _ = classify_quadrant(x, y)
    return {
        "Q1": "success",
        "Q2": "info",
        "Q3": "danger",
        "Q4": "warning",
    }.get(quad, "primary")


def compute_next_step(snap, today: date | None = None) -> NextStep:
    """Return the best single action for the user given their day.

    Args:
        snap: A :class:`operational.cli.services.DaySnapshot` (or any
            object with the same attributes). May be ``None`` for empty
            state — we return :func:`_empty_step` in that case.
        today: Optional override for the current date (used for
            deterministic testing).

    Returns:
        :class:`NextStep` with observation, action, severity.

    Algorithm (priority order — first match wins):
        1. No sleep record            → "log sleep first"
        2. Sleep debt > 1h            → "wind down earlier / extend sleep"
        3. Energy < 4                 → "take a real break, no deep work"
        4. Pomodoros < 50% of meta    → "focus session now, kill distractions"
        5. Focus < 5                  → "low-attention task, save deep work"
        6. Q3 (critical)              → "review system, identify blockers"
        7. Q2 (optimized but low)     → "more output, raise tempo"
        8. Q4 (productive scattered)  → "reduce distractions"
        9. Q1 (good)                  → "maintain"
    """
    if snap is None:
        return _empty_step()

    # 1. No sleep → log first
    sleep_hours = getattr(snap, "sleep", None)
    sleep_h = getattr(sleep_hours, "duration_hours", None) if sleep_hours else None
    if sleep_h is None:
        return NextStep(
            observation="Sono ainda não registrado hoje.",
            action="Rode `pav metric sleep --quality <1-10>` para fechar o ciclo.",
            severity="info",
        )

    # 2. Sleep debt
    sleep_debt = SLEEP_TARGET_H - sleep_h
    if sleep_debt >= abs(SLEEP_DEBT_THRESHOLD):
        return NextStep(
            observation=f"Débito de sono: -{sleep_debt:.1f}h vs meta de {SLEEP_TARGET_H}h.",
            action="Hoje: deitar 30min mais cedo, sem luz azul após 18h.",
            severity="warning",
        )

    # 3. Energy check
    energia = getattr(snap, "energia", None)
    if energia is not None and energia < ENERGY_LOW_THRESHOLD:
        return NextStep(
            observation=f"Energia baixa ({energia}/10) — corpo pedindo pausa.",
            action="Pule a próxima sessão de foco. Faça uma caminhada de 20min ou durma 30min.",
            severity="warning",
        )

    # 4. Pomodoros behind
    pomo_meta = getattr(snap, "pomodoros_meta", 0) or POMODORO_META_TYPICAL
    pomo_done = getattr(snap, "n_pomodoros", 0) or 0
    pct_done = (pomo_done / pomo_meta * 100) if pomo_meta else 100
    if pomo_meta and pct_done < HARDWORK_UNDER_PERCENT:
        return NextStep(
            observation=f"Pomodoros: {pomo_done}/{pomo_meta} ({pct_done:.0f}%) — abaixo do ritmo.",
            action="Inicie uma sessão de 25min agora. Modo avião + fone + uma única tarefa.",
            severity="primary",
        )

    # 5. Focus check
    foco = getattr(snap, "foco", None)
    if foco is not None and foco < FOCUS_LOW_THRESHOLD:
        return NextStep(
            observation=f"Foco baixo ({foco}/10) — atenção fragmentada.",
            action="Tarefa leve agora (inbox, admin, leitura). Salve deep work para amanhã.",
            severity="info",
        )

    # 6-9. Quadrant-based
    from operational.cli.services import compute_day_quadrant
    quad, x, y = compute_day_quadrant(snap)
    severity = _classify_severity(x, y)

    if quad == "Q3":
        return NextStep(
            observation="Quadrante crítico (Q3) — realizado/orçado baixo e foco disperso.",
            action="Revisão urgente: liste 3 bloqueios sistêmicos. Qual é o gargalo recorrente?",
            severity="danger",
        )
    if quad == "Q2":
        return NextStep(
            observation=f"Otimizado mas pouco output (Q2 — feito {x:.0f}% do orçado, foco {y:.0f}%).",
            action="Aumente o volume: mais 1 sessão de 50min antes do almoço.",
            severity="info",
        )
    if quad == "Q4":
        return NextStep(
            observation="Produtivo mas disperso (Q4 — realizado ok, foco baixo).",
            action="Reduza distrações: feche abas não-essenciais, defina 1 prioridade única.",
            severity="warning",
        )

    # Q1 — default to "maintain"
    return NextStep(
        observation=f"Quadrante Q1: {x:.0f}% produtividade, {y:.0f}% eficiência.",
        action="Mantenha o ritmo. Próxima: continue com a próxima rotina do dia.",
        severity="success",
    )


def get_current_regime(snap=None) -> str:
    """Return the current policy regime from the most recent decision.

    Falls back to ``"MAINTAIN"`` if no decision is found or if no
    snapshot is provided. Pure function — used by both the CLI dashboard
    and the TUI dashboard so they always agree.

    Args:
        snap: Optional snapshot (unused — kept for future expansion
            where regime is computed from the snapshot's metrics rather
            than from the historical decision log).

    Returns:
        One of ``"PUSH"``, ``"MAINTAIN"``, ``"REDUCE"``, ``"RECOVER"``.
    """
    try:
        from operational.cli.state import policy_decisions

        decisions = sorted(
            policy_decisions.list(),
            key=lambda d: getattr(d, "date", None) or getattr(d, "created_at", None) or "",
            reverse=True,
        )
        if decisions:
            state = getattr(decisions[0], "state", None)
            if state:
                return str(state).upper()
    except Exception:
        pass
    return "MAINTAIN"


__all__ = ["NextStep", "compute_next_step", "get_current_regime"]
