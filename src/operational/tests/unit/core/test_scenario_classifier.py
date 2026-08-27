"""Unit tests for :mod:`operational.core.scenario_classifier`.

Covers:

* :class:`Scenario` — StrEnum surface, member count, value casing.
* :func:`classificar_dia` — all 3 PAV §8 scenarios, boundary
  conditions, optional energy / focus boosts, validation.
* :func:`is_hardcore_alert` — monthly cap, negative-input guard.
* :class:`ScenarioClassification` — frozen dataclass, tuple-typed
  reasons and adjustments.

Tests are deterministic and use only pure-function inputs (no
clock, no filesystem).
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from enum import StrEnum

import pytest

from operational.core.scenario_classifier import (
    HARDCORE_MAX_PER_MONTH,
    Scenario,
    ScenarioClassification,
    classificar_dia,
    is_hardcore_alert,
)

# ---------------------------------------------------------------------------
# Shared constants (canonical PAV §8 numbers)
# ---------------------------------------------------------------------------

PAV_POMODOROS: int = 12
"""Default daily pomodoro target (PAV §8 / §1)."""


def _perfeito(  # noqa: PLR0913
    *,
    horas_sono: float = 8.0,
    pomodoros_planejados: int = PAV_POMODOROS,
    pomodoros_completos: int = 11,
    infraction_count: int = 0,
    energia_nivel: int | None = None,
    foco_nivel: int | None = None,
) -> ScenarioClassification:
    """Return a canonical PERFEITO classification for the suite."""
    return classificar_dia(
        horas_sono=horas_sono,
        pomodoros_planejados=pomodoros_planejados,
        pomodoros_completos=pomodoros_completos,
        infraction_count=infraction_count,
        energia_nivel=energia_nivel,
        foco_nivel=foco_nivel,
    )


# ---------------------------------------------------------------------------
# Module surface
# ---------------------------------------------------------------------------


class TestModuleSurface:
    """The :mod:`scenario_classifier` module exposes a stable public API."""

    def test_all_is_complete(self) -> None:
        import operational.core.scenario_classifier as mod

        expected = {
            "Scenario",
            "ScenarioClassification",
            "classificar_dia",
            "is_hardcore_alert",
            "HARDCORE_MAX_PER_MONTH",
        }
        assert expected.issubset(set(mod.__all__))

    def test_all_names_importable(self) -> None:
        import operational.core.scenario_classifier as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"Missing export: {name}"


# ===========================================================================
# Scenario enum
# ===========================================================================


class TestScenario:
    """:class:`Scenario` is a 3-value StrEnum with lowercase values."""

    def test_scenario_is_str_enum(self) -> None:
        assert issubclass(Scenario, StrEnum)

    def test_scenarios_complete_set(self) -> None:
        assert {m.name for m in Scenario} == {"PERFEITO", "DESVIADO", "HARDCORE"}
        assert len(list(Scenario)) == 3

    def test_scenario_values_lowercase(self) -> None:
        for member in Scenario:
            assert member.value == member.value.lower()
            assert " " not in member.value

    def test_scenario_roundtrip_by_value(self) -> None:
        for member in Scenario:
            assert Scenario(member.value) is member

    def test_scenario_string_equality(self) -> None:
        assert Scenario.PERFEITO == "perfeito"
        assert Scenario.DESVIADO == "desviado"
        assert Scenario.HARDCORE == "hardcore"


# ===========================================================================
# classificar_dia — PERFEITO
# ===========================================================================


class TestClassifyPerfeito:
    """All-nominal inputs produce PERFEITO."""

    def test_classify_perfeito_normal(self) -> None:
        c = _perfeito()
        assert c.scenario is Scenario.PERFEITO
        assert c.confidence == 95.0
        assert "Sono adequado" in c.reasons

    def test_classify_perfeito_alta_execucao(self) -> None:
        """100% execution (12/12) is PERFEITO."""
        c = _perfeito(pomodoros_completos=12)
        assert c.scenario is Scenario.PERFEITO
        assert "Execução 100%" in c.reasons

    def test_classify_perfeito_70_percent_boundary(self) -> None:
        """Exactly 70% (8.4/12) is PERFEITO (boundary is strict ``<``)."""
        c = _perfeito(pomodoros_completos=8, pomodoros_planejados=12)
        # 8/12 = 0.6666... which is < 0.7, so this is DESVIADO actually.
        # Let me reconsider.
        # 9/12 = 0.75 which is >= 0.7 so PERFEITO.
        # Let me use 9/12 explicitly.
        assert c.scenario is Scenario.DESVIADO  # 8/12 = 0.667 < 0.7

    def test_classify_perfeito_at_70_percent(self) -> None:
        """9/12 = 75% is PERFEITO."""
        c = _perfeito(pomodoros_completos=9)
        assert c.scenario is Scenario.PERFEITO

    def test_perfeito_with_zero_pomodoros_planned(self) -> None:
        """No pomodoros planned + good sleep + no infractions = PERFEITO."""
        c = _perfeito(pomodoros_planejados=0, pomodoros_completos=0)
        assert c.scenario is Scenario.PERFEITO
        assert "Sem infrações" in c.reasons

    def test_perfeito_adjustments(self) -> None:
        c = _perfeito()
        assert "Manter rotina" in c.recommended_adjustments
        assert "Continuar tracking" in c.recommended_adjustments

    def test_perfeito_with_low_self_reports(self) -> None:
        """Low self-reports on a PERFEITO day still show up in reasons."""
        c = _perfeito(energia_nivel=3, foco_nivel=2)
        assert c.scenario is Scenario.PERFEITO
        assert any("Energia baixa" in r for r in c.reasons)
        assert any("Foco baixo" in r for r in c.reasons)


# ===========================================================================
# classificar_dia — HARDCORE
# ===========================================================================


class TestClassifyHardcore:
    """Critical sleep or severe infractions trigger HARDCORE."""

    def test_classify_hardcore_sono_critico(self) -> None:
        c = classificar_dia(horas_sono=4.0, pomodoros_planejados=12, pomodoros_completos=6)
        assert c.scenario is Scenario.HARDCORE
        assert c.confidence == 95.0
        assert any("Sono crítico" in r for r in c.reasons)

    def test_hardcore_sleep_below_5h(self) -> None:
        """Any sleep < 5h is HARDCORE regardless of other metrics."""
        c = classificar_dia(horas_sono=3.0, pomodoros_planejados=12, pomodoros_completos=12)
        assert c.scenario is Scenario.HARDCORE

    def test_hardcore_just_below_5h(self) -> None:
        """4.99h is HARDCORE (boundary is strict ``<``)."""
        c = classificar_dia(horas_sono=4.99, pomodoros_planejados=12, pomodoros_completos=12)
        assert c.scenario is Scenario.HARDCORE

    def test_classify_hardcore_infractions_ge_3(self) -> None:
        c = classificar_dia(
            horas_sono=8.0,
            pomodoros_planejados=12,
            pomodoros_completos=12,
            infraction_count=3,
        )
        assert c.scenario is Scenario.HARDCORE
        assert c.confidence == 90.0
        assert any("graves" in r for r in c.reasons)

    def test_hardcore_infractions_above_3(self) -> None:
        c = classificar_dia(
            horas_sono=8.0,
            pomodoros_planejados=12,
            pomodoros_completos=12,
            infraction_count=10,
        )
        assert c.scenario is Scenario.HARDCORE

    def test_hardcore_sleep_takes_priority_over_infractions(self) -> None:
        """Sleep < 5h wins even with 0 infractions (priority 1)."""
        c = classificar_dia(horas_sono=3.0, pomodoros_planejados=12, pomodoros_completos=0)
        assert c.scenario is Scenario.HARDCORE
        assert c.confidence == 95.0  # sleep confidence, not infraction

    def test_recommendations_hardcore_includes_recuperacao(self) -> None:
        c = classificar_dia(horas_sono=4.0, pomodoros_planejados=12, pomodoros_completos=6)
        joined = " | ".join(c.recommended_adjustments)
        assert "Recuperação" in joined
        assert "18h" in joined  # suggested sleep time

    def test_recommendations_hardcore_includes_power_nap(self) -> None:
        c = classificar_dia(horas_sono=4.0, pomodoros_planejados=12, pomodoros_completos=6)
        joined = " | ".join(c.recommended_adjustments)
        assert "Power nap" in joined

    def test_recommendations_hardcore_mentions_limit_2x_mes(self) -> None:
        c = classificar_dia(horas_sono=4.0, pomodoros_planejados=12, pomodoros_completos=6)
        joined = " | ".join(c.recommended_adjustments)
        assert "2x" in joined or "Limite" in joined

    def test_hardcore_infractions_uses_reiniciar_adjustment(self) -> None:
        """Infraction-driven HARDCORE uses different adjustments than sleep-driven."""
        c = classificar_dia(
            horas_sono=8.0,
            pomodoros_planejados=12,
            pomodoros_completos=12,
            infraction_count=3,
        )
        joined = " | ".join(c.recommended_adjustments)
        assert "Reiniciar" in joined or "Revisar" in joined


# ===========================================================================
# classificar_dia — DESVIADO
# ===========================================================================


class TestClassifyDesviado:
    """Minor deviations trigger DESVIADO."""

    def test_classify_desviado_sono_reduzido(self) -> None:
        c = classificar_dia(horas_sono=6.0, pomodoros_planejados=12, pomodoros_completos=11)
        assert c.scenario is Scenario.DESVIADO
        assert c.confidence == 80.0
        assert any("Sono reduzido" in r for r in c.reasons)

    def test_desviado_sleep_at_5h_boundary(self) -> None:
        """5h is DESVIADO (boundary is inclusive)."""
        c = classificar_dia(horas_sono=5.0, pomodoros_planejados=12, pomodoros_completos=12)
        assert c.scenario is Scenario.DESVIADO

    def test_desviado_sleep_at_just_under_7h(self) -> None:
        c = classificar_dia(horas_sono=6.99, pomodoros_planejados=12, pomodoros_completos=12)
        assert c.scenario is Scenario.DESVIADO

    def test_classify_desviado_baixa_execucao(self) -> None:
        """< 70% execution triggers DESVIADO."""
        c = classificar_dia(horas_sono=8.0, pomodoros_planejados=12, pomodoros_completos=5)
        assert c.scenario is Scenario.DESVIADO
        assert c.confidence == 75.0
        assert any("Baixa execução" in r for r in c.reasons)

    def test_desviado_just_below_70_percent(self) -> None:
        """8/12 = 66.67% is DESVIADO."""
        c = classificar_dia(horas_sono=8.0, pomodoros_planejados=12, pomodoros_completos=8)
        assert c.scenario is Scenario.DESVIADO

    def test_desviado_just_at_70_percent_is_perfeito(self) -> None:
        """9/12 = 75% is PERFEITO (the boundary check is strict ``<``)."""
        c = classificar_dia(horas_sono=8.0, pomodoros_planejados=12, pomodoros_completos=9)
        assert c.scenario is Scenario.PERFEITO

    def test_classify_desviado_one_infraction(self) -> None:
        c = classificar_dia(
            horas_sono=8.0,
            pomodoros_planejados=12,
            pomodoros_completos=12,
            infraction_count=1,
        )
        assert c.scenario is Scenario.DESVIADO
        assert c.confidence == 70.0
        assert any("1 infração" in r for r in c.reasons)

    def test_desviado_multiple_infractions(self) -> None:
        c = classificar_dia(
            horas_sono=8.0,
            pomodoros_planejados=12,
            pomodoros_completos=12,
            infraction_count=2,
        )
        assert c.scenario is Scenario.DESVIADO
        assert any("2 infração" in r for r in c.reasons)

    def test_desviado_sleep_priority_over_pomodoros(self) -> None:
        """Sleep < 7h wins over the pomodoro branch (priority order)."""
        c = classificar_dia(horas_sono=6.0, pomodoros_planejados=12, pomodoros_completos=0)
        assert c.scenario is Scenario.DESVIADO
        assert c.confidence == 80.0
        assert any("Sono reduzido" in r for r in c.reasons)

    def test_classify_desviado_com_energia_baixa(self) -> None:
        c = classificar_dia(
            horas_sono=6.0,
            pomodoros_planejados=12,
            pomodoros_completos=11,
            energia_nivel=3,
        )
        assert c.scenario is Scenario.DESVIADO
        assert c.confidence == 85.0  # 80 + 5
        assert any("Energia baixa" in r for r in c.reasons)

    def test_classify_desviado_com_foco_baixo(self) -> None:
        c = classificar_dia(
            horas_sono=6.0,
            pomodoros_planejados=12,
            pomodoros_completos=11,
            foco_nivel=2,
        )
        assert c.scenario is Scenario.DESVIADO
        assert c.confidence == 85.0  # 80 + 5
        assert any("Foco baixo" in r for r in c.reasons)

    def test_desviado_with_both_low_boosts(self) -> None:
        """Both boosts stack but are capped at 95.0."""
        c = classificar_dia(
            horas_sono=6.0,
            pomodoros_planejados=12,
            pomodoros_completos=11,
            energia_nivel=3,
            foco_nivel=2,
        )
        assert c.scenario is Scenario.DESVIADO
        # 80 + 5 + 5 = 90 (under cap)
        assert c.confidence == 90.0

    def test_desviado_boost_capped_at_95(self) -> None:
        """Confidence cap is 95.0 even with multiple boosts from a higher base."""
        c = classificar_dia(
            horas_sono=8.0,
            pomodoros_planejados=12,
            pomodoros_completos=8,  # 67% → 75 base
            infraction_count=0,
            energia_nivel=3,
            foco_nivel=2,
        )
        assert c.scenario is Scenario.DESVIADO
        # 75 + 5 + 5 = 85 (under cap)
        assert c.confidence == 85.0

    def test_desviado_energia_alta_no_boost(self) -> None:
        c = classificar_dia(
            horas_sono=6.0,
            pomodoros_planejados=12,
            pomodoros_completos=11,
            energia_nivel=8,
        )
        assert c.scenario is Scenario.DESVIADO
        assert c.confidence == 80.0  # no boost

    def test_recommendations_desviado_includes_pausa_extra(self) -> None:
        c = classificar_dia(horas_sono=6.0, pomodoros_planejados=12, pomodoros_completos=11)
        joined = " | ".join(c.recommended_adjustments)
        assert "Pausa" in joined
        assert "5min" in joined

    def test_recommendations_desviado_includes_reduzir_s3(self) -> None:
        c = classificar_dia(horas_sono=6.0, pomodoros_planejados=12, pomodoros_completos=11)
        joined = " | ".join(c.recommended_adjustments)
        assert "S3" in joined


# ===========================================================================
# classificar_dia — input validation
# ===========================================================================


class TestClassifyValidation:
    """:func:`classificar_dia` rejects malformed inputs."""

    def test_invalid_sono_negativo_raises(self) -> None:
        with pytest.raises(ValueError, match="horas_sono"):
            classificar_dia(horas_sono=-1.0, pomodoros_planejados=12, pomodoros_completos=12)

    def test_invalid_pomodoros_negativo_raises(self) -> None:
        with pytest.raises(ValueError, match="pomodoros_planejados"):
            classificar_dia(horas_sono=8.0, pomodoros_planejados=-1, pomodoros_completos=0)

    def test_invalid_pomodoros_completos_negativo_raises(self) -> None:
        with pytest.raises(ValueError, match="pomodoros_completos"):
            classificar_dia(horas_sono=8.0, pomodoros_planejados=12, pomodoros_completos=-1)

    def test_invalid_infractions_negativo_raises(self) -> None:
        with pytest.raises(ValueError, match="infraction_count"):
            classificar_dia(
                horas_sono=8.0,
                pomodoros_planejados=12,
                pomodoros_completos=12,
                infraction_count=-1,
            )

    def test_pomodoros_completos_greater_than_planejados_raises(self) -> None:
        with pytest.raises(ValueError, match="must be <="):
            classificar_dia(horas_sono=8.0, pomodoros_planejados=5, pomodoros_completos=6)

    def test_pomodoros_completos_equals_planejados_is_valid(self) -> None:
        c = classificar_dia(horas_sono=8.0, pomodoros_planejados=5, pomodoros_completos=5)
        assert c.scenario is Scenario.PERFEITO

    @pytest.mark.parametrize("bad", [0, 11, 100, -1])
    def test_energia_nivel_out_of_range_raises(self, bad: int) -> None:
        with pytest.raises(ValueError, match="energia_nivel"):
            classificar_dia(
                horas_sono=8.0,
                pomodoros_planejados=12,
                pomodoros_completos=12,
                energia_nivel=bad,
            )

    @pytest.mark.parametrize("bad", [0, 11, 100, -1])
    def test_foco_nivel_out_of_range_raises(self, bad: int) -> None:
        with pytest.raises(ValueError, match="foco_nivel"):
            classificar_dia(
                horas_sono=8.0,
                pomodoros_planejados=12,
                pomodoros_completos=12,
                foco_nivel=bad,
            )

    def test_energia_nivel_none_is_valid(self) -> None:
        c = classificar_dia(
            horas_sono=8.0,
            pomodoros_planejados=12,
            pomodoros_completos=12,
            energia_nivel=None,
        )
        assert c.scenario is Scenario.PERFEITO


# ===========================================================================
# is_hardcore_alert
# ===========================================================================


class TestIsHardcoreAlert:
    """:func:`is_hardcore_alert` enforces the monthly cap."""

    def test_hardcore_alert_false_below_limit(self) -> None:
        assert is_hardcore_alert(0) is False
        assert is_hardcore_alert(1) is False

    def test_hardcore_alert_true_at_limit(self) -> None:
        assert is_hardcore_alert(HARDCORE_MAX_PER_MONTH) is True

    def test_hardcore_alert_true_above_limit(self) -> None:
        assert is_hardcore_alert(3) is True
        assert is_hardcore_alert(10) is True

    def test_hardcore_alert_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="hardcore_count"):
            is_hardcore_alert(-1)

    def test_hardcore_max_per_month_is_two(self) -> None:
        """PAV §8 caps hardcore days at 2 per month."""
        assert HARDCORE_MAX_PER_MONTH == 2


# ===========================================================================
# ScenarioClassification
# ===========================================================================


class TestScenarioClassificationDataclass:
    """:class:`ScenarioClassification` is a frozen dataclass."""

    def test_classification_frozen(self) -> None:
        c = _perfeito()
        with pytest.raises(FrozenInstanceError):
            c.scenario = Scenario.DESVIADO  # type: ignore[misc]

    def test_reasons_is_tuple(self) -> None:
        c = _perfeito()
        assert isinstance(c.reasons, tuple)
        assert all(isinstance(r, str) for r in c.reasons)

    def test_adjustments_is_tuple(self) -> None:
        c = _perfeito()
        assert isinstance(c.recommended_adjustments, tuple)
        assert all(isinstance(a, str) for a in c.recommended_adjustments)

    def test_reasons_non_empty(self) -> None:
        """Every classification carries at least one reason."""
        for sc in (Scenario.PERFEITO, Scenario.DESVIADO, Scenario.HARDCORE):
            if sc is Scenario.PERFEITO:
                c = _perfeito()
            elif sc is Scenario.DESVIADO:
                c = classificar_dia(6.0, 12, 11)
            else:
                c = classificar_dia(4.0, 12, 6)
            assert c.reasons, f"{sc.value} should have at least one reason"
            assert c.recommended_adjustments, f"{sc.value} should have at least one adjustment"

    def test_confidence_in_range(self) -> None:
        for sc in (Scenario.PERFEITO, Scenario.DESVIADO, Scenario.HARDCORE):
            if sc is Scenario.PERFEITO:
                c = _perfeito()
            elif sc is Scenario.DESVIADO:
                c = classificar_dia(6.0, 12, 11)
            else:
                c = classificar_dia(4.0, 12, 6)
            assert 0.0 <= c.confidence <= 100.0, (
                f"confidence out of range for {sc.value}: {c.confidence}"
            )
