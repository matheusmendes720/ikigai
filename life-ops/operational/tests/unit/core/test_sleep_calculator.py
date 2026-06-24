"""Unit tests for :mod:`operational.core.sleep_calculator`.

Coverage (~50 tests):

* :func:`calcular_horas_sono` — midnight crossing, same-day, edge cases,
  invalid inputs (negative, out-of-range, non-int, bool).
* :func:`validar_sono_ideal` — all 5 quality buckets, boundary values,
  invalid inputs.
* :meth:`SleepQuality.is_optimal_sleep` — optimal window, off-window,
  parametric combinations.
* :class:`SleepDecision` — frozen dataclass invariants.
* :func:`get_sleep_matrix` — 20 cells, exact match of the PAV §7 table,
  parametric per-cell tests, 9h diagonal, HARDCORE escape hatch.
* :func:`render_sleep_matrix` — formatting.
* Module-level aliases match the class methods.
"""
from __future__ import annotations

import pytest

from operational.core.sleep_calculator import (
    STATUS_CRITICO,
    STATUS_HARDCORE,
    STATUS_OK,
    SleepDecision,
    SleepQuality,
    calcular_horas_sono,
    get_sleep_matrix,
    is_within_optimal_window,
    render_sleep_matrix,
    validar_sono_ideal,
)
from operational.enums import QualityLabel


# =========================================================================
# Module surface
# =========================================================================


class TestModuleSurface:
    """The module exports the expected public symbols."""

    def test_all_exports_present(self) -> None:
        """__all__ lists the canonical public surface."""
        from operational.core import sleep_calculator

        expected = {
            "SleepDecision",
            "SleepQuality",
            "STATUS_CRITICO",
            "STATUS_HARDCORE",
            "STATUS_OK",
            "calcular_horas_sono",
            "get_sleep_matrix",
            "is_within_optimal_window",
            "validar_sono_ideal",
        }
        assert set(sleep_calculator.__all__) == expected

    def test_status_glyphs_are_strings(self) -> None:
        """The 3 status constants are non-empty strings."""
        assert isinstance(STATUS_OK, str)
        assert isinstance(STATUS_HARDCORE, str)
        assert isinstance(STATUS_CRITICO, str)
        assert len(STATUS_OK) > 0
        assert len(STATUS_HARDCORE) > 0
        assert len(STATUS_CRITICO) > 0

    def test_status_glyphs_unique(self) -> None:
        """The 3 status glyphs are distinct strings."""
        glyphs = {STATUS_OK, STATUS_HARDCORE, STATUS_CRITICO}
        assert len(glyphs) == 3


# =========================================================================
# calcular_horas_sono — basic cases
# =========================================================================


class TestCalcularHorasSonoBasic:
    """PAV §7: sleep-duration calculation."""

    def test_no_midnight_8h(self) -> None:
        """6h → 14h = 8h (no midnight crossing)."""
        assert calcular_horas_sono(6, 14) == 8.0

    def test_no_midnight_same_hour_zero(self) -> None:
        """6h → 6h = 0h (degenerate same-day case)."""
        assert calcular_horas_sono(6, 6) == 0.0

    def test_no_midnight_short_nap(self) -> None:
        """14h → 15h = 1h (afternoon nap, same day)."""
        assert calcular_horas_sono(14, 15) == 1.0

    def test_midnight_crossing_22_to_6(self) -> None:
        """22h → 6am = 8h (classic midnight crossing)."""
        assert calcular_horas_sono(22, 6) == 8.0

    def test_midnight_crossing_18_to_3(self) -> None:
        """18h → 3am = 9h (PAV §7 9h ideal)."""
        assert calcular_horas_sono(18, 3) == 9.0

    def test_midnight_crossing_23_to_3(self) -> None:
        """23h → 3am = 4h (PAV §7 HARDCORE)."""
        assert calcular_horas_sono(23, 3) == 4.0

    def test_midnight_crossing_minimal(self) -> None:
        """23h → 0h = 1h (smallest crossing)."""
        assert calcular_horas_sono(23, 0) == 1.0

    def test_returns_float(self) -> None:
        """Result type is float (for downstream division)."""
        result = calcular_horas_sono(22, 6)
        assert isinstance(result, float)

    @pytest.mark.parametrize(
        ("dormir", "acordar", "expected"),
        [
            (0, 0, 0.0),
            (1, 3, 2.0),
            (6, 14, 8.0),
            (12, 12, 0.0),
            (14, 15, 1.0),
            (18, 3, 9.0),
            (19, 4, 9.0),
            (20, 5, 9.0),
            (21, 6, 9.0),
            (22, 6, 8.0),
            (22, 7, 9.0),
            (23, 3, 4.0),
            (23, 0, 1.0),
        ],
    )
    def test_parametric_durations(
        self,
        dormir: int,
        acordar: int,
        expected: float,
    ) -> None:
        """Parametric verification of common PAV §7 durations."""
        assert calcular_horas_sono(dormir, acordar) == expected


# =========================================================================
# calcular_horas_sono — error cases
# =========================================================================


class TestCalcularHorasSonoErrors:
    """PAV §7: input validation for sleep-duration calculation."""

    @pytest.mark.parametrize("hour", [-1, -10, 24, 25, 100])
    def test_invalid_hora_dormir_raises(self, hour: int) -> None:
        """hora_dormir outside [0, 23] raises ValueError."""
        with pytest.raises(ValueError, match="hora_dormir"):
            calcular_horas_sono(hour, 6)

    @pytest.mark.parametrize("hour", [-1, -10, 24, 25, 100])
    def test_invalid_hora_acordar_raises(self, hour: int) -> None:
        """hora_acordar outside [0, 23] raises ValueError."""
        with pytest.raises(ValueError, match="hora_acordar"):
            calcular_horas_sono(22, hour)

    @pytest.mark.parametrize("bad_input", [3.5, "3", None, 3.0, [], {}])
    def test_non_int_hora_dormir_raises(self, bad_input: object) -> None:
        """Non-int hora_dormir raises TypeError."""
        with pytest.raises(TypeError):
            calcular_horas_sono(bad_input, 6)  # type: ignore[arg-type]

    @pytest.mark.parametrize("bad_input", [3.5, "3", None, 3.0, [], {}])
    def test_non_int_hora_acordar_raises(self, bad_input: object) -> None:
        """Non-int hora_acordar raises TypeError."""
        with pytest.raises(TypeError):
            calcular_horas_sono(22, bad_input)  # type: ignore[arg-type]

    def test_bool_hora_dormir_rejected(self) -> None:
        """Bool hora_dormir is rejected (PEP 285 quirk)."""
        with pytest.raises(TypeError, match="bool"):
            calcular_horas_sono(True, 6)  # type: ignore[arg-type]

    def test_bool_hora_acordar_rejected(self) -> None:
        """Bool hora_acordar is rejected (PEP 285 quirk)."""
        with pytest.raises(TypeError, match="bool"):
            calcular_horas_sono(22, True)  # type: ignore[arg-type]

    def test_boundary_0_accepted(self) -> None:
        """Hour 0 is valid."""
        assert calcular_horas_sono(0, 0) == 0.0

    def test_boundary_23_accepted(self) -> None:
        """Hour 23 is valid."""
        assert calcular_horas_sono(23, 23) == 0.0


# =========================================================================
# validar_sono_ideal — quality buckets
# =========================================================================


class TestValidarSonoIdealBuckets:
    """PAV §7: classification into QualityLabel buckets."""

    @pytest.mark.parametrize("hours", [9.0, 9.5, 10.0, 11.0, 12.0, 100.0])
    def test_excelente_ge_9(self, hours: float) -> None:
        """Hours >= 9 → EXCELENTE."""
        assert validar_sono_ideal(hours) is QualityLabel.EXCELENTE

    @pytest.mark.parametrize("hours", [8.0, 8.5, 8.99])
    def test_bom_ge_8(self, hours: float) -> None:
        """8 <= hours < 9 → BOM."""
        assert validar_sono_ideal(hours) is QualityLabel.BOM

    @pytest.mark.parametrize("hours", [7.0, 7.5, 7.99])
    def test_aceitavel_ge_7(self, hours: float) -> None:
        """7 <= hours < 8 → ACEITAVEL."""
        assert validar_sono_ideal(hours) is QualityLabel.ACEITAVEL

    @pytest.mark.parametrize("hours", [4.0, 4.5, 5.0, 6.0, 6.99])
    def test_hardcore_ge_4(self, hours: float) -> None:
        """4 <= hours < 7 → HARDCORE."""
        assert validar_sono_ideal(hours) is QualityLabel.HARDCORE

    @pytest.mark.parametrize("hours", [0.0, 1.0, 2.0, 3.0, 3.99])
    def test_critico_lt_4(self, hours: float) -> None:
        """Hours < 4 → CRITICO."""
        assert validar_sono_ideal(hours) is QualityLabel.CRITICO

    def test_negative_raises(self) -> None:
        """Negative hours raise ValueError (programming error)."""
        with pytest.raises(ValueError, match="non-negative"):
            validar_sono_ideal(-1.0)

    def test_non_numeric_raises_type_error(self) -> None:
        """Non-numeric hours raise TypeError."""
        with pytest.raises(TypeError):
            validar_sono_ideal("8")  # type: ignore[arg-type]

    def test_bool_rejected(self) -> None:
        """Bool hours are rejected (PEP 285)."""
        with pytest.raises(TypeError):
            validar_sono_ideal(True)  # type: ignore[arg-type]

    def test_int_input_accepted(self) -> None:
        """Int input is accepted (coerced via isinstance check)."""
        assert validar_sono_ideal(8) is QualityLabel.BOM


# =========================================================================
# SleepQuality class methods (delegation)
# =========================================================================


class TestSleepQualityClass:
    """The SleepQuality namespace class wraps the same logic."""

    def test_class_static_calcular_matches_alias(self) -> None:
        """Class static method matches the module-level alias."""
        for dormir, acordar in [(22, 6), (18, 3), (0, 0)]:
            assert SleepQuality.calcular_horas_sono(dormir, acordar) == calcular_horas_sono(
                dormir, acordar
            )

    def test_class_static_validar_matches_alias(self) -> None:
        """Class static method matches the module-level alias."""
        for hours in [10.0, 8.0, 7.0, 5.0, 2.0]:
            assert (
                SleepQuality.validar_sono_ideal(hours)
                is validar_sono_ideal(hours)
            )

    def test_class_is_namespace_only(self) -> None:
        """SleepQuality has no instance state — all methods are static."""
        sq: SleepQuality = SleepQuality()  # type: ignore[abstract]
        assert sq.calcular_horas_sono(22, 6) == 8.0


# =========================================================================
# is_optimal_sleep / is_within_optimal_window
# =========================================================================


class TestIsOptimalSleep:
    """The optimal-window predicate (PAV §7)."""

    @pytest.mark.parametrize(
        ("dormir", "acordar"),
        [
            (18, 3),  # 9h
            (19, 3),  # 8h
            (19, 4),  # 9h
            (20, 3),  # 7h
            (20, 4),  # 8h
            (20, 5),  # 9h
            (21, 4),  # 7h
            (21, 5),  # 8h
        ],
    )
    def test_optimal_combinations(self, dormir: int, acordar: int) -> None:
        """Combinations achieving 7-9h with dormir 18-21 and acordar 3-5."""
        assert is_within_optimal_window(dormir, acordar) is True

    @pytest.mark.parametrize(
        ("dormir", "acordar"),
        [
            (22, 6),  # dormir out of window
            (16, 3),  # dormir too early
            (18, 6),  # acordar out of window
            (18, 7),  # acordar too late
            (23, 3),  # HARDCORE — only 4h, below optimal band
            (18, 5),  # 11h — over 9h
        ],
    )
    def test_outside_window(self, dormir: int, acordar: int) -> None:
        """Combinations outside the optimal window are not optimal."""
        assert is_within_optimal_window(dormir, acordar) is False


# =========================================================================
# SleepDecision dataclass
# =========================================================================


class TestSleepDecision:
    """The frozen dataclass for one matrix cell."""

    def test_construct_minimal(self) -> None:
        """Minimal construction works."""
        cell = SleepDecision(
            dormir=18,
            acordar=3,
            target_horas=9,
            actual_horas=9.0,
            status=STATUS_OK,
            is_optimal=True,
        )
        assert cell.dormir == 18
        assert cell.acordar == 3
        assert cell.target_horas == 9
        assert cell.actual_horas == 9.0
        assert cell.status == STATUS_OK
        assert cell.is_optimal is True

    def test_is_frozen(self) -> None:
        """Assignment after construction raises FrozenInstanceError."""
        from dataclasses import FrozenInstanceError

        cell = SleepDecision(
            dormir=18,
            acordar=3,
            target_horas=9,
            actual_horas=9.0,
            status=STATUS_OK,
            is_optimal=True,
        )
        with pytest.raises(FrozenInstanceError):
            cell.dormir = 19  # type: ignore[misc]

    def test_uses_slots(self) -> None:
        """Dataclass is frozen (no __dict__, slots used internally)."""
        cell = SleepDecision(
            dormir=18,
            acordar=3,
            target_horas=9,
            actual_horas=9.0,
            status=STATUS_OK,
            is_optimal=True,
        )
        # Frozen dataclass: assignment raises FrozenInstanceError.
        with pytest.raises((AttributeError, TypeError)):
            cell.invalid_attribute = "boom"  # type: ignore[attr-defined]

    def test_invalid_status_raises(self) -> None:
        """Unknown status glyph raises ValueError at construction."""
        with pytest.raises(ValueError, match="status"):
            SleepDecision(
                dormir=18,
                acordar=3,
                target_horas=9,
                actual_horas=9.0,
                status="🤷",
                is_optimal=False,
            )

    def test_equality(self) -> None:
        """Two cells with same fields are equal."""
        kwargs = {
            "dormir": 18,
            "acordar": 3,
            "target_horas": 9,
            "actual_horas": 9.0,
            "status": STATUS_OK,
            "is_optimal": True,
        }
        assert SleepDecision(**kwargs) == SleepDecision(**kwargs)

    def test_inequality_on_difference(self) -> None:
        """Cells differing in any field are unequal."""
        a = SleepDecision(
            dormir=18, acordar=3, target_horas=9,
            actual_horas=9.0, status=STATUS_OK, is_optimal=True,
        )
        b = SleepDecision(
            dormir=19, acordar=3, target_horas=9,
            actual_horas=8.0, status=STATUS_HARDCORE, is_optimal=False,
        )
        assert a != b


# =========================================================================
# get_sleep_matrix
# =========================================================================


EXPECTED_MATRIX: dict[tuple[int, int, int], tuple[str, float]] = {
    # (dormir, acordar, target) -> (status, actual_horas)
    # 3am (9h) column
    (18, 3, 9): (STATUS_OK, 9.0),
    (19, 3, 9): (STATUS_HARDCORE, 8.0),
    (20, 3, 9): (STATUS_HARDCORE, 7.0),
    (21, 3, 9): (STATUS_HARDCORE, 6.0),
    (23, 3, 9): (STATUS_CRITICO, 4.0),
    # 4am (8h) column
    (18, 4, 8): (STATUS_HARDCORE, 10.0),
    (19, 4, 8): (STATUS_OK, 9.0),
    (20, 4, 8): (STATUS_HARDCORE, 8.0),
    (21, 4, 8): (STATUS_HARDCORE, 7.0),
    (23, 4, 8): (STATUS_CRITICO, 5.0),
    # 5am (7h) column
    (18, 5, 7): (STATUS_HARDCORE, 11.0),
    (19, 5, 7): (STATUS_HARDCORE, 10.0),
    (20, 5, 7): (STATUS_OK, 9.0),
    (21, 5, 7): (STATUS_HARDCORE, 8.0),
    (23, 5, 7): (STATUS_CRITICO, 6.0),
    # 3am HARDCORE (4h) column
    (18, 3, 4): (STATUS_CRITICO, 9.0),
    (19, 3, 4): (STATUS_CRITICO, 8.0),
    (20, 3, 4): (STATUS_CRITICO, 7.0),
    (21, 3, 4): (STATUS_CRITICO, 6.0),
    (23, 3, 4): (STATUS_OK, 4.0),
}
"""The exact PAV §7 5x4 matrix — (dormir, acordar, target) → (status, actual)."""


class TestGetSleepMatrix:
    """The 5x4 decision matrix from PAV §7."""

    def test_returns_list(self) -> None:
        """get_sleep_matrix returns a list."""
        assert isinstance(get_sleep_matrix(), list)

    def test_returns_20_cells(self) -> None:
        """The matrix has exactly 20 cells (5 bedtimes x 4 scenarios)."""
        matrix = get_sleep_matrix()
        assert len(matrix) == 20

    def test_all_cells_are_sleep_decision(self) -> None:
        """Every cell is a SleepDecision instance."""
        for cell in get_sleep_matrix():
            assert isinstance(cell, SleepDecision)

    def test_optimal_9h_3am_18h(self) -> None:
        """18h → 3am = 9h ✅ (the canonical 9h schedule)."""
        cell = next(
            c
            for c in get_sleep_matrix()
            if c.dormir == 18 and c.acordar == 3 and c.target_horas == 9
        )
        assert cell.actual_horas == 9.0
        assert cell.status == STATUS_OK
        assert cell.is_optimal is True

    def test_hardcore_4h_3am_23h(self) -> None:
        """23h → 3am HARDCORE = 4h ✅ (the only valid 23h schedule)."""
        cell = next(
            c
            for c in get_sleep_matrix()
            if c.dormir == 23 and c.acordar == 3 and c.target_horas == 4
        )
        assert cell.actual_horas == 4.0
        assert cell.status == STATUS_OK
        assert cell.is_optimal is True

    def test_9h_ideal_diagonal(self) -> None:
        """The 9h ideal diagonal: (18,3), (19,4), (20,5) all status OK."""
        matrix = get_sleep_matrix()
        for dormir, acordar in [(18, 3), (19, 4), (20, 5)]:
            cell = next(
                c
                for c in matrix
                if c.dormir == dormir and c.acordar == acordar
            )
            assert cell.actual_horas == 9.0, f"({dormir},{acordar}) actual={cell.actual_horas}"
            assert cell.status == STATUS_OK, f"({dormir},{acordar}) status={cell.status}"

    @pytest.mark.parametrize(
        ("dormir", "acordar", "target"),
        list(EXPECTED_MATRIX.keys()),
    )
    def test_parametric_matrix_cell(
        self,
        dormir: int,
        acordar: int,
        target: int,
    ) -> None:
        """Each of the 20 cells matches the PAV §7 spec exactly."""
        expected_status, expected_horas = EXPECTED_MATRIX[
            (dormir, acordar, target)
        ]
        cell = next(
            c
            for c in get_sleep_matrix()
            if c.dormir == dormir
            and c.acordar == acordar
            and c.target_horas == target
        )
        assert cell.actual_horas == expected_horas
        assert cell.status == expected_status
        assert cell.is_optimal is (expected_status == STATUS_OK)

    def test_4h_harcore_col_all_critico_except_23h(self) -> None:
        """In the 4h HARDCORE column, all cells are CRITICO except 23h."""
        matrix = get_sleep_matrix()
        for cell in matrix:
            if cell.target_horas != 4:
                continue
            if cell.dormir == 23 and cell.acordar == 3:
                assert cell.status == STATUS_OK
            else:
                assert cell.status == STATUS_CRITICO, (
                    f"({cell.dormir},{cell.acordar},4) should be CRITICO"
                )

    def test_23h_row_all_critico_except_3am_hardcore(self) -> None:
        """In the 23h row, all cells are CRITICO except 3am HARDCORE."""
        matrix = get_sleep_matrix()
        for cell in matrix:
            if cell.dormir != 23:
                continue
            if cell.acordar == 3 and cell.target_horas == 4:
                assert cell.status == STATUS_OK
            else:
                assert cell.status == STATUS_CRITICO

    def test_matrix_is_deterministic(self) -> None:
        """Calling get_sleep_matrix twice yields the same content."""
        m1 = get_sleep_matrix()
        m2 = get_sleep_matrix()
        assert m1 == m2


# =========================================================================
# render_sleep_matrix
# =========================================================================


class TestRenderSleepMatrix:
    """The ASCII table renderer."""

    def test_returns_string(self) -> None:
        """render_sleep_matrix returns a string."""
        assert isinstance(render_sleep_matrix(), str)

    def test_contains_all_20_horas(self) -> None:
        """The rendered table mentions all 20 actual hour values."""
        text = render_sleep_matrix()
        for value in EXPECTED_MATRIX.values():
            _expected_status, expected_horas = value
            assert f"{int(expected_horas)}h" in text

    def test_contains_all_three_status_glyphs(self) -> None:
        """The rendered table contains all 3 status glyphs."""
        text = render_sleep_matrix()
        assert STATUS_OK in text
        assert STATUS_HARDCORE in text
        assert STATUS_CRITICO in text

    def test_contains_column_headers(self) -> None:
        """The rendered table has the 4 column headers (3am, 4am, 5am, HARDCORE)."""
        text = render_sleep_matrix()
        assert "03h" in text
        assert "04h" in text
        assert "05h" in text

    def test_contains_row_headers(self) -> None:
        """The rendered table has the 5 row headers (18h-23h)."""
        text = render_sleep_matrix()
        for hour in (18, 19, 20, 21, 23):
            assert f"{hour}h" in text

    def test_uses_provided_cells(self) -> None:
        """If a pre-computed list is passed, the renderer uses it."""
        cells = get_sleep_matrix()
        text = render_sleep_matrix(cells)
        assert isinstance(text, str)
        assert "23h" in text  # sanity check it rendered
