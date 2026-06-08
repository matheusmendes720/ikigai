"""Unit tests for :mod:`operational.constants`.

Coverage:

* Structure: dataclass flags, field count, names, types, frozen/slots.
* Defaults: every field of :data:`DEFAULT` matches the PAV canonical value.
* Invariants: validation in :meth:`PAVConstants.__post_init__`.
* Domain helpers: ``is_valid_*`` and ``qhe_*`` predicates.
* Parametric tests: per-field, per-category, per-source-document.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass

import pytest

from operational.constants import DEFAULT, PAVConstants


# --- Constants used in parametric tests ----------------------------------

EXPECTED_DEFAULTS: dict[str, object] = {
    "PERIODOS_DIA": ("MANHA", "TARDE", "NOITE"),
    "HORARIO_ACORDAR_MIN": 3,
    "HORARIO_ACORDAR_MAX": 5,
    "HORARIO_DORMIR_MIN": 18,
    "HORARIO_DORMIR_MAX": 21,
    "HORARIO_ULTIMA_REFEICAO_MIN": 15,
    "HORARIO_ULTIMA_REFEICAO_MAX": 18,
    "POMODORO_WORK_MIN": 50,
    "POMODORO_BREAK_MIN": 10,
    "POMODORO_LONG_BREAK_MIN": 30,
    "POMODORO_ROUNDS_MIN": 3,
    "POMODORO_ROUNDS_MAX": 4,
    "SONO_OPCOES_HORAS": (9, 8, 7, 4),
    "LUZ_AZUL_CORTE": 18,
    "AGUA_GLASSES_DIA": 8,
    "POLICY_UPGRADE_DAYS": 3,
    "POLICY_DOWNGRADE_DAYS": 2,
    "POLICY_RECOVER_ENTRY_DAYS": 1,
    "QHE_ALPHA": 0.45,
    "QHE_BETA": 0.35,
    "QHE_GAMMA": 0.20,
    "QHE_PUSH_THRESHOLD": 0.85,
    "QHE_RECOVER_THRESHOLD": 0.60,
    "LAMBDA_LEARNING_DEFAULT": 0.093,
}

TIME_FIELDS: tuple[str, ...] = (
    "HORARIO_ACORDAR_MIN",
    "HORARIO_ACORDAR_MAX",
    "HORARIO_DORMIR_MIN",
    "HORARIO_DORMIR_MAX",
    "HORARIO_ULTIMA_REFEICAO_MIN",
    "HORARIO_ULTIMA_REFEICAO_MAX",
    "LUZ_AZUL_CORTE",
)
POMODORO_FIELDS: tuple[str, ...] = (
    "POMODORO_WORK_MIN",
    "POMODORO_BREAK_MIN",
    "POMODORO_LONG_BREAK_MIN",
    "POMODORO_ROUNDS_MIN",
    "POMODORO_ROUNDS_MAX",
)
POLICY_FIELDS: tuple[str, ...] = (
    "POLICY_UPGRADE_DAYS",
    "POLICY_DOWNGRADE_DAYS",
    "POLICY_RECOVER_ENTRY_DAYS",
)
QHE_FIELDS: tuple[str, ...] = (
    "QHE_ALPHA",
    "QHE_BETA",
    "QHE_GAMMA",
    "QHE_PUSH_THRESHOLD",
    "QHE_RECOVER_THRESHOLD",
)


# =========================================================================
# Structure
# =========================================================================


class TestPAVConstantsStructure:
    """Structural tests: dataclass flags, fields, frozen, slots."""

    def test_is_dataclass(self) -> None:
        """PAVConstants is a dataclass."""
        assert is_dataclass(PAVConstants)

    def test_has_24_fields(self) -> None:
        """PAVConstants declares exactly 24 fields (per PRD-CONSTANTS-EXCEPTIONS)."""
        assert len(fields(PAVConstants)) == 24

    def test_field_count_constant_matches(self) -> None:
        """FIELD_COUNT class constant agrees with dataclass field count."""
        assert PAVConstants.FIELD_COUNT == 24
        assert PAVConstants.FIELD_COUNT == len(fields(PAVConstants))

    def test_all_expected_fields_present(self) -> None:
        """Every documented field exists in the dataclass."""
        actual = {f.name for f in fields(PAVConstants)}
        expected = set(EXPECTED_DEFAULTS.keys())
        assert actual == expected

    @pytest.mark.parametrize("field_name", sorted(EXPECTED_DEFAULTS.keys()))
    def test_each_field_has_type_annotation(self, field_name: str) -> None:
        """Each field has a non-empty type annotation."""
        fld = next(f for f in fields(PAVConstants) if f.name == field_name)
        assert fld.type != "", f"{field_name} has no type annotation"

    def test_frozen_cannot_assign(self) -> None:
        """FrozenInstanceError is raised on attribute assignment."""
        c = PAVConstants()
        with pytest.raises(FrozenInstanceError):
            c.HORARIO_ACORDAR_MIN = 4  # type: ignore[misc]

    def test_frozen_cannot_setattr(self) -> None:
        """Setattr on a frozen instance also raises."""
        c = PAVConstants()
        with pytest.raises(FrozenInstanceError):
            c.HORARIO_ACORDAR_MIN = 4

    def test_slots_prevent_dict(self) -> None:
        """Slots-based instance has no __dict__."""
        c = PAVConstants()
        assert "__dict__" not in dir(c)
        assert not hasattr(c, "__dict__")

    def test_repr_contains_class_name(self) -> None:
        """Default repr includes class name and field values."""
        c = PAVConstants(HORARIO_ACORDAR_MIN=4)
        text = repr(c)
        assert "PAVConstants" in text
        assert "HORARIO_ACORDAR_MIN=4" in text

    def test_equality_is_structural(self) -> None:
        """Two instances with the same values compare equal."""
        a = PAVConstants()
        b = PAVConstants()
        assert a == b

    def test_inequality_on_difference(self) -> None:
        """Two instances with different values compare unequal."""
        a = PAVConstants()
        b = PAVConstants(HORARIO_ACORDAR_MIN=4)
        assert a != b

    def test_no_arg_construction(self) -> None:
        """PAVConstants() works (kw_only + all defaults)."""
        c = PAVConstants()
        assert c.HORARIO_ACORDAR_MIN == 3

    def test_kw_only_construction(self) -> None:
        """Construction works with any subset of kwargs (kw_only)."""
        c = PAVConstants(AGUA_GLASSES_DIA=10)
        assert c.AGUA_GLASSES_DIA == 10
        assert c.HORARIO_ACORDAR_MIN == 3


# =========================================================================
# Defaults
# =========================================================================


class TestPAVConstantsDefaults:
    """Verify the ``DEFAULT`` instance matches the PAV canonical spec."""

    @pytest.mark.parametrize(
        ("field_name", "expected"),
        sorted(EXPECTED_DEFAULTS.items()),
        ids=sorted(EXPECTED_DEFAULTS.keys()),
    )
    def test_default_value_matches_pav(self, field_name: str, expected: object) -> None:
        """Each field of ``DEFAULT`` matches the PAV/PRD-02 value."""
        actual = getattr(DEFAULT, field_name)
        assert actual == expected, f"{field_name}: expected {expected!r}, got {actual!r}"

    def test_pav_section_1_periodos(self) -> None:
        """PERIODOS_DIA matches PAV §1 exactly."""
        assert DEFAULT.PERIODOS_DIA == ("MANHA", "TARDE", "NOITE")

    def test_pav_section_1_wake_window(self) -> None:
        """Wake window matches PAV §1: 3-5 am."""
        assert DEFAULT.HORARIO_ACORDAR_MIN == 3
        assert DEFAULT.HORARIO_ACORDAR_MAX == 5

    def test_pav_section_1_sleep_window(self) -> None:
        """Sleep window matches PAV §1: 18-21 h."""
        assert DEFAULT.HORARIO_DORMIR_MIN == 18
        assert DEFAULT.HORARIO_DORMIR_MAX == 21

    def test_pav_section_1_pomodoro(self) -> None:
        """Pomodoro durations match PAV §1: 50/10 min, 3-4 rounds."""
        assert DEFAULT.POMODORO_WORK_MIN == 50
        assert DEFAULT.POMODORO_BREAK_MIN == 10
        assert DEFAULT.POMODORO_ROUNDS_MIN == 3
        assert DEFAULT.POMODORO_ROUNDS_MAX == 4

    def test_pav_section_1_sleep_options(self) -> None:
        """SONO_OPCOES_HORAS matches PAV §1: (9, 8, 7, 4)."""
        assert DEFAULT.SONO_OPCOES_HORAS == (9, 8, 7, 4)

    def test_pav_section_1_blue_light(self) -> None:
        """LUZ_AZUL_CORTE matches PAV §1: 18 h."""
        assert DEFAULT.LUZ_AZUL_CORTE == 18

    def test_pav_section_9_long_break(self) -> None:
        """POMODORO_LONG_BREAK_MIN matches PAV §9 line 2291: 30 min."""
        assert DEFAULT.POMODORO_LONG_BREAK_MIN == 30

    def test_qhe_weights_match_prd02(self) -> None:
        """QHE weights match PRD-02 §Fórmula QHE: 0.45/0.35/0.20."""
        assert DEFAULT.QHE_ALPHA == pytest.approx(0.45)
        assert DEFAULT.QHE_BETA == pytest.approx(0.35)
        assert DEFAULT.QHE_GAMMA == pytest.approx(0.20)

    def test_qhe_thresholds_match_points_of_premisses(self) -> None:
        """QHE thresholds match Points_of_premisses §4: 0.85 / 0.60."""
        assert DEFAULT.QHE_PUSH_THRESHOLD == pytest.approx(0.85)
        assert DEFAULT.QHE_RECOVER_THRESHOLD == pytest.approx(0.60)

    def test_policy_days_match_points_of_premisses(self) -> None:
        """Policy histerese days match Points_of_premisses §4: 3/2/1."""
        assert DEFAULT.POLICY_UPGRADE_DAYS == 3
        assert DEFAULT.POLICY_DOWNGRADE_DAYS == 2
        assert DEFAULT.POLICY_RECOVER_ENTRY_DAYS == 1

    def test_lambda_matches_adr003(self) -> None:
        """LAMBDA_LEARNING_DEFAULT matches ADR-003 / time-lenghts §9.2: 0.093."""
        assert DEFAULT.LAMBDA_LEARNING_DEFAULT == pytest.approx(0.093)

    def test_default_constructible_twice(self) -> None:
        """``PAVConstants()`` can be called multiple times without state leaks."""
        a = PAVConstants()
        b = PAVConstants()
        assert a == b
        assert a is not b


# =========================================================================
# Invariants (QHE weights, ordering)
# =========================================================================


class TestPAVConstantsInvariants:
    """Mathematical / structural invariants from PAV spec."""

    def test_qhe_weights_sum_to_1(self) -> None:
        """Alpha + beta + gamma = 1.0 (PRD-02 §Fórmula QHE)."""
        total = DEFAULT.QHE_ALPHA + DEFAULT.QHE_BETA + DEFAULT.QHE_GAMMA
        assert total == pytest.approx(1.0)

    def test_qhe_weights_individually_positive(self) -> None:
        """All QHE weights are strictly positive."""
        for weight_name in QHE_FIELDS[:3]:
            weight = getattr(DEFAULT, weight_name)
            assert weight > 0, f"{weight_name} must be > 0, got {weight}"

    def test_sleep_options_contain_9_8_7_4(self) -> None:
        """SONO_OPCOES_HORAS is exactly (9, 8, 7, 4)."""
        assert DEFAULT.SONO_OPCOES_HORAS == (9, 8, 7, 4)
        assert 9 in DEFAULT.SONO_OPCOES_HORAS
        assert 8 in DEFAULT.SONO_OPCOES_HORAS
        assert 7 in DEFAULT.SONO_OPCOES_HORAS
        assert 4 in DEFAULT.SONO_OPCOES_HORAS

    def test_sleep_options_unique(self) -> None:
        """All sleep options are distinct."""
        assert len(set(DEFAULT.SONO_OPCOES_HORAS)) == len(DEFAULT.SONO_OPCOES_HORAS)

    def test_sleep_options_sorted_descending(self) -> None:
        """Sleep options are listed in descending order (semantic ordering)."""
        assert DEFAULT.SONO_OPCOES_HORAS == tuple(sorted(DEFAULT.SONO_OPCOES_HORAS, reverse=True))

    def test_pomodoro_rounds_min_le_max(self) -> None:
        """POMODORO_ROUNDS_MIN <= POMODORO_ROUNDS_MAX."""
        assert DEFAULT.POMODORO_ROUNDS_MIN <= DEFAULT.POMODORO_ROUNDS_MAX

    def test_pomodoro_break_lt_work(self) -> None:
        """POMODORO_BREAK_MIN < POMODORO_WORK_MIN (break must be shorter)."""
        assert DEFAULT.POMODORO_BREAK_MIN < DEFAULT.POMODORO_WORK_MIN

    def test_pomodoro_long_break_gt_short_break(self) -> None:
        """POMODORO_LONG_BREAK_MIN > POMODORO_BREAK_MIN (long > short)."""
        assert DEFAULT.POMODORO_LONG_BREAK_MIN > DEFAULT.POMODORO_BREAK_MIN

    def test_acordar_window_valid(self) -> None:
        """Wake window is well-formed: min < max."""
        assert DEFAULT.HORARIO_ACORDAR_MIN < DEFAULT.HORARIO_ACORDAR_MAX

    def test_dormir_window_valid(self) -> None:
        """Sleep window is well-formed: min < max."""
        assert DEFAULT.HORARIO_DORMIR_MIN < DEFAULT.HORARIO_DORMIR_MAX

    def test_refeicao_window_valid(self) -> None:
        """Last-meal window is well-formed: min < max."""
        assert DEFAULT.HORARIO_ULTIMA_REFEICAO_MIN < DEFAULT.HORARIO_ULTIMA_REFEICAO_MAX

    def test_refeicao_max_equals_blue_light(self) -> None:
        """HORARIO_ULTIMA_REFEICAO_MAX == LUZ_AZUL_CORTE (18h shared boundary)."""
        assert DEFAULT.HORARIO_ULTIMA_REFEICAO_MAX == DEFAULT.LUZ_AZUL_CORTE

    def test_qhe_push_gt_recover(self) -> None:
        """QHE_PUSH_THRESHOLD > QHE_RECOVER_THRESHOLD."""
        assert DEFAULT.QHE_PUSH_THRESHOLD > DEFAULT.QHE_RECOVER_THRESHOLD

    def test_policy_days_positive(self) -> None:
        """All policy histerese days are strictly positive."""
        for name in POLICY_FIELDS:
            value = getattr(DEFAULT, name)
            assert value > 0, f"{name} must be > 0, got {value}"

    def test_lambda_in_unit_interval(self) -> None:
        """LAMBDA_LEARNING_DEFAULT is in (0, 1]."""
        assert 0.0 < DEFAULT.LAMBDA_LEARNING_DEFAULT <= 1.0


# -- Validation: post_init invariants -------------------------------------


class TestPAVConstantsValidation:
    """``__post_init__`` rejects invalid configurations."""

    def test_periodos_dia_wrong_length_rejected(self) -> None:
        """PERIODOS_DIA with != 3 elements raises ValueError."""
        with pytest.raises(ValueError, match="PERIODOS_DIA"):
            PAVConstants(PERIODOS_DIA=("MANHA", "TARDE"))  # type: ignore[arg-type]

    def test_acordar_min_greater_than_max_rejected(self) -> None:
        """HORARIO_ACORDAR_MIN >= HORARIO_ACORDAR_MAX raises ValueError."""
        with pytest.raises(ValueError, match="HORARIO_ACORDAR_MIN"):
            PAVConstants(HORARIO_ACORDAR_MIN=10, HORARIO_ACORDAR_MAX=5)

    def test_acordar_min_equal_to_max_rejected(self) -> None:
        """HORARIO_ACORDAR_MIN == HORARIO_ACORDAR_MAX raises ValueError (strict <)."""
        with pytest.raises(ValueError, match="HORARIO_ACORDAR_MIN"):
            PAVConstants(HORARIO_ACORDAR_MIN=5, HORARIO_ACORDAR_MAX=5)

    def test_dormir_min_greater_than_max_rejected(self) -> None:
        """HORARIO_DORMIR_MIN >= HORARIO_DORMIR_MAX raises ValueError."""
        with pytest.raises(ValueError, match="HORARIO_DORMIR_MIN"):
            PAVConstants(HORARIO_DORMIR_MIN=22, HORARIO_DORMIR_MAX=21)

    def test_refeicao_min_greater_than_max_rejected(self) -> None:
        """HORARIO_ULTIMA_REFEICAO_MIN >= _MAX raises ValueError."""
        with pytest.raises(ValueError, match="HORARIO_ULTIMA_REFEICAO_MIN"):
            PAVConstants(HORARIO_ULTIMA_REFEICAO_MIN=20, HORARIO_ULTIMA_REFEICAO_MAX=18)

    def test_pomodoro_break_ge_work_rejected(self) -> None:
        """POMODORO_BREAK_MIN >= POMODORO_WORK_MIN raises ValueError."""
        with pytest.raises(ValueError, match="POMODORO_BREAK_MIN"):
            PAVConstants(POMODORO_BREAK_MIN=60, POMODORO_WORK_MIN=50)

    def test_pomodoro_rounds_min_gt_max_rejected(self) -> None:
        """POMODORO_ROUNDS_MIN > POMODORO_ROUNDS_MAX raises ValueError."""
        with pytest.raises(ValueError, match="POMODORO_ROUNDS_MIN"):
            PAVConstants(POMODORO_ROUNDS_MIN=5, POMODORO_ROUNDS_MAX=4)

    def test_sleep_options_wrong_length_rejected(self) -> None:
        """SONO_OPCOES_HORAS with != 4 elements raises ValueError."""
        with pytest.raises(ValueError, match="SONO_OPCOES_HORAS"):
            PAVConstants(SONO_OPCOES_HORAS=(9, 8))  # type: ignore[arg-type]

    def test_qhe_weights_not_summing_to_1_rejected(self) -> None:
        """QHE weights not summing to 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="QHE weights"):
            PAVConstants(QHE_ALPHA=0.50, QHE_BETA=0.30, QHE_GAMMA=0.10)

    def test_qhe_push_le_recover_rejected(self) -> None:
        """QHE_PUSH_THRESHOLD <= QHE_RECOVER_THRESHOLD raises ValueError."""
        with pytest.raises(ValueError, match="QHE_PUSH_THRESHOLD"):
            PAVConstants(QHE_PUSH_THRESHOLD=0.50, QHE_RECOVER_THRESHOLD=0.60)

    def test_negative_value_rejected(self) -> None:
        """Negative values for non-negative fields raise ValueError."""
        with pytest.raises(ValueError, match="must be non-negative"):
            PAVConstants(HORARIO_ACORDAR_MIN=-1)

    def test_lambda_out_of_range_rejected(self) -> None:
        """LAMBDA_LEARNING_DEFAULT outside (0, 1] raises ValueError."""
        with pytest.raises(ValueError, match="LAMBDA_LEARNING_DEFAULT"):
            PAVConstants(LAMBDA_LEARNING_DEFAULT=0.0)
        with pytest.raises(ValueError, match="LAMBDA_LEARNING_DEFAULT"):
            PAVConstants(LAMBDA_LEARNING_DEFAULT=1.5)

    def test_valid_custom_values_accepted(self) -> None:
        """A coherent custom config is accepted."""
        c = PAVConstants(
            HORARIO_ACORDAR_MIN=4,
            HORARIO_ACORDAR_MAX=6,
            AGUA_GLASSES_DIA=10,
        )
        assert c.HORARIO_ACORDAR_MIN == 4
        assert c.AGUA_GLASSES_DIA == 10
        # Unchanged fields keep defaults
        assert c.POMODORO_WORK_MIN == 50


# =========================================================================
# Domain helpers
# =========================================================================


class TestPAVConstantsHelpers:
    """Pure helpers on PAVConstants instances."""

    @pytest.mark.parametrize("hour", [3, 4, 5])
    def test_valid_wake_hour_accepted(self, hour: int) -> None:
        """Hours 3-5 are valid wake hours."""
        assert DEFAULT.is_valid_wake_hour(hour) is True

    @pytest.mark.parametrize("hour", [0, 1, 2, 6, 7, 12, 23])
    def test_invalid_wake_hour_rejected(self, hour: int) -> None:
        """Hours outside 3-5 are invalid wake hours."""
        assert DEFAULT.is_valid_wake_hour(hour) is False

    @pytest.mark.parametrize("hour", [18, 19, 20, 21])
    def test_valid_sleep_hour_accepted(self, hour: int) -> None:
        """Hours 18-21 are valid sleep hours."""
        assert DEFAULT.is_valid_sleep_hour(hour) is True

    @pytest.mark.parametrize("hour", [0, 6, 12, 17, 22, 23])
    def test_invalid_sleep_hour_rejected(self, hour: int) -> None:
        """Hours outside 18-21 are invalid sleep hours."""
        assert DEFAULT.is_valid_sleep_hour(hour) is False

    @pytest.mark.parametrize("hours", [9.0, 8.0, 7.0, 4.0, 8.5, 7.4])
    def test_valid_sleep_duration_accepted(self, hours: float) -> None:
        """Durations near 9/8/7/4 (within 0.5h) are valid."""
        assert DEFAULT.is_valid_sleep_duration(hours) is True

    @pytest.mark.parametrize("hours", [3.0, 5.5, 6.0, 10.0, 12.0])
    def test_invalid_sleep_duration_rejected(self, hours: float) -> None:
        """Durations far from 9/8/7/4 are invalid."""
        assert DEFAULT.is_valid_sleep_duration(hours) is False

    @pytest.mark.parametrize("qhe", [0.85, 0.90, 0.95, 1.0])
    def test_qhe_push_active_above_threshold(self, qhe: float) -> None:
        """QHE ≥ 0.85 enables PUSH."""
        assert DEFAULT.qhe_push_active(qhe) is True

    @pytest.mark.parametrize("qhe", [0.0, 0.50, 0.60, 0.84, 0.8499])
    def test_qhe_push_inactive_below_threshold(self, qhe: float) -> None:
        """QHE < 0.85 disables PUSH."""
        assert DEFAULT.qhe_push_active(qhe) is False

    @pytest.mark.parametrize("qhe", [0.0, 0.30, 0.50, 0.59, 0.5999])
    def test_qhe_recover_required_below_threshold(self, qhe: float) -> None:
        """QHE < 0.60 requires RECOVER."""
        assert DEFAULT.qhe_recover_required(qhe) is True

    @pytest.mark.parametrize("qhe", [0.60, 0.70, 0.85, 1.0])
    def test_qhe_recover_not_required_above_threshold(self, qhe: float) -> None:
        """QHE ≥ 0.60 does not require RECOVER."""
        assert DEFAULT.qhe_recover_required(qhe) is False

    def test_helpers_use_instance_state(self) -> None:
        """Helpers read from the instance, not the class defaults."""
        c = PAVConstants(HORARIO_ACORDAR_MIN=4, HORARIO_ACORDAR_MAX=6)
        assert c.is_valid_wake_hour(5) is True
        assert DEFAULT.is_valid_wake_hour(5) is True
        assert c.is_valid_wake_hour(3) is False  # 3 < 4 in custom config


# =========================================================================
# Parametric: per-category coverage
# =========================================================================


class TestPAVConstantsCategories:
    """Group fields by PAV/PRD source and assert presence + types."""

    def test_time_fields_all_int(self) -> None:
        """All time-boundary fields are int."""
        for name in TIME_FIELDS:
            value = getattr(DEFAULT, name)
            assert isinstance(value, int), f"{name} should be int, got {type(value)}"

    def test_pomodoro_fields_all_int(self) -> None:
        """All pomodoro fields are int."""
        for name in POMODORO_FIELDS:
            value = getattr(DEFAULT, name)
            assert isinstance(value, int), f"{name} should be int, got {type(value)}"

    def test_policy_fields_all_int(self) -> None:
        """All policy fields are positive int."""
        for name in POLICY_FIELDS:
            value = getattr(DEFAULT, name)
            assert isinstance(value, int)
            assert value > 0

    def test_qhe_weights_all_float(self) -> None:
        """QHE alpha/beta/gamma are float in (0, 1)."""
        for name in ("QHE_ALPHA", "QHE_BETA", "QHE_GAMMA"):
            value = getattr(DEFAULT, name)
            assert isinstance(value, float)
            assert 0.0 < value < 1.0

    def test_qhe_thresholds_in_unit_interval(self) -> None:
        """QHE thresholds are in (0, 1)."""
        assert 0.0 < DEFAULT.QHE_PUSH_THRESHOLD < 1.0
        assert 0.0 < DEFAULT.QHE_RECOVER_THRESHOLD < 1.0

    def test_periodos_dia_is_tuple(self) -> None:
        """PERIODOS_DIA is an immutable tuple of strings."""
        assert isinstance(DEFAULT.PERIODOS_DIA, tuple)
        assert all(isinstance(p, str) for p in DEFAULT.PERIODOS_DIA)

    def test_sono_opcoes_is_tuple_of_int(self) -> None:
        """SONO_OPCOES_HORAS is an immutable tuple of ints."""
        assert isinstance(DEFAULT.SONO_OPCOES_HORAS, tuple)
        assert all(isinstance(h, int) for h in DEFAULT.SONO_OPCOES_HORAS)

    def test_field_count_per_category(self) -> None:
        """Spot-check field counts per category."""
        assert len(TIME_FIELDS) == 7
        assert len(POMODORO_FIELDS) == 5
        assert len(POLICY_FIELDS) == 3
        assert len(QHE_FIELDS) == 5
        # TIME=7, PERIODOS=1, POMODORO=5, HEALTH=2, POLICY+QHE=9 -> 24
        total = 7 + 1 + 5 + 2 + 9
        assert total == 24


# =========================================================================
# Public surface
# =========================================================================


class TestPAVConstantsExports:
    """Verify ``__all__`` and module-level API."""

    def test_default_is_final_singleton(self) -> None:
        """DEFAULT is a module-level frozen instance."""
        assert isinstance(DEFAULT, PAVConstants)

    def test_default_equals_noarg_construction(self) -> None:
        """DEFAULT and ``PAVConstants()`` are structurally equal."""
        assert DEFAULT == PAVConstants()

    def test_field_count_classvar_is_int(self) -> None:
        """FIELD_COUNT is an int ClassVar (not a dataclass field)."""
        assert isinstance(PAVConstants.FIELD_COUNT, int)
        # ClassVar should not appear in fields()
        field_names = {f.name for f in fields(PAVConstants)}
        assert "FIELD_COUNT" not in field_names
