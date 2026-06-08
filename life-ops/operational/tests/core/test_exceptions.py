"""Unit tests for :mod:`operational.core.exceptions`.

The :mod:`operational.core.exceptions` module defines the custom domain
exception hierarchy used across the operational CLI:

* :class:`DomainError` — the base class every business-logic error inherits from.
* Six concrete subclasses, each carrying rich metadata the UI layer
  consumes to render context-aware error panels.

The contract being tested is intentionally narrow:

1. Every error stores ``mensagem`` (str) and ``metadados`` (dict).
2. ``str(exc)`` returns ``exc.mensagem`` so the value round-trips through
   :class:`Exception`'s built-in ``args`` mechanism.
3. Every subclass is catchable as :class:`DomainError` (single base).
4. The metadata keys are stable (UI components depend on them).

Tests follow strict AAA (Arrange / Act / Assert) with explicit section
comments so the contract is obvious at a glance.
"""
from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from operational.core.exceptions import (
    ConfiguracaoInvalidaError,
    DataInvalidaError,
    DomainError,
    FaltaDadosError,
    LimitePomodoroExcedidoError,
    RepositorioVazioError,
    ValorForaRangeError,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_date() -> date:
    """A fixed reference date for any test that needs a :class:`date`."""
    return date(2026, 6, 7)


@pytest.fixture
def basic_domain_error() -> DomainError:
    """A simple :class:`DomainError` carrying no metadata.

    Use as a baseline for hierarchy / ``str()`` round-trip tests.
    """
    return DomainError("baseline message")


# ===========================================================================
# DomainError — base class
# ===========================================================================


def test_domain_error_stores_mensagem_and_defaults_metadados_to_empty_dict() -> None:
    """``DomainError('msg')`` exposes ``.mensagem == 'msg'`` and an empty dict."""
    # Arrange / Act
    e = DomainError("hello")

    # Assert
    assert e.mensagem == "hello"
    assert e.metadados == {}


def test_domain_error_stores_explicit_metadados_dict() -> None:
    """``DomainError(msg, {...})`` keeps the metadata dict intact."""
    # Arrange
    payload: dict[str, Any] = {"k": "v", "n": 42, "flag": True}

    # Act
    e = DomainError("hello", payload)

    # Assert
    assert e.metadados == payload
    assert e.metadados is not payload or e.metadados == payload


def test_domain_error_str_returns_mensagem(basic_domain_error: DomainError) -> None:
    """``str(exc)`` is exactly the mensagem — usable in f-strings and logs."""
    # Arrange
    e = basic_domain_error

    # Act
    rendered = str(e)

    # Assert
    assert rendered == "baseline message"
    assert rendered == e.mensagem


def test_domain_error_args_match_mensagem() -> None:
    """``Exception.args[0]`` equals ``mensagem`` (stdlib round-trip)."""
    # Arrange / Act
    e = DomainError("arg test")

    # Assert
    assert e.args == ("arg test",)
    assert e.args[0] == e.mensagem


def test_domain_error_inherits_from_exception() -> None:
    """``DomainError`` is catchable as stdlib :class:`Exception`."""
    # Arrange / Act
    e = DomainError("x")

    # Assert
    assert isinstance(e, Exception)


def test_domain_error_none_metadata_does_not_share_default_across_instances() -> None:
    """Each instance gets its own dict (no shared mutable default)."""
    # Arrange / Act
    a = DomainError("a")
    b = DomainError("b")

    # Act — mutate a's metadata
    a.metadados["injected"] = 1

    # Assert — b is unaffected
    assert "injected" not in b.metadados
    assert b.metadados == {}


def test_base_class_catches_every_subclass() -> None:
    """A single ``except DomainError`` catches every concrete subclass."""
    # Arrange
    cases: list[DomainError] = [
        FaltaDadosError(campos_ausentes=["x"]),
        DataInvalidaError(data_fornecida="bad", motivo="bad format"),
        ValorForaRangeError(campo="x", valor=99, minimo=0, maximo=10),
        LimitePomodoroExcedidoError(quantidade=30),
        RepositorioVazioError(entidade="sleep_record"),
        ConfiguracaoInvalidaError(parametro="X", valor=1, esperado=">0"),
    ]

    # Act / Assert — each subclass raises and is caught as DomainError
    for err in cases:
        with pytest.raises(DomainError) as excinfo:
            raise err
        assert excinfo.value is err


# ===========================================================================
# FaltaDadosError
# ===========================================================================


def test_falta_dados_message_lists_every_missing_field() -> None:
    """The mensagem mentions every campo_ausente by name."""
    # Arrange
    campos = ["data", "foco", "pomodoros"]

    # Act
    e = FaltaDadosError(campos_ausentes=campos)

    # Assert
    for campo in campos:
        assert campo in e.mensagem
    assert "Dados incompletos" in e.mensagem


def test_falta_dados_message_appends_contexto_when_provided() -> None:
    """When ``contexto`` is given, the message ends with ``(contexto: ...)``."""
    # Arrange / Act
    e = FaltaDadosError(campos_ausentes=["x"], contexto="unit test")

    # Assert
    assert "(contexto: unit test)" in e.mensagem
    assert e.metadados["contexto"] == "unit test"


def test_falta_dados_message_omits_contexto_when_empty_string() -> None:
    """Empty ``contexto`` is treated as absent — no ``(contexto: )`` noise."""
    # Arrange / Act
    e = FaltaDadosError(campos_ausentes=["x"], contexto="")

    # Assert
    assert "contexto" not in e.mensagem
    assert e.metadados["contexto"] == ""


def test_falta_dados_metadata_preserves_list_and_context() -> None:
    """``metadados`` carries both ``campos_ausentes`` (list) and ``contexto``."""
    # Arrange
    campos = ["a", "b", "c"]

    # Act
    e = FaltaDadosError(campos_ausentes=campos, contexto="ctx")

    # Assert
    assert e.metadados["campos_ausentes"] == campos
    assert e.metadados["campos_ausentes"] is campos
    assert e.metadados["contexto"] == "ctx"


def test_falta_dados_with_empty_list_still_produces_valid_error() -> None:
    """An empty list of missing fields is allowed (degenerate but valid)."""
    # Arrange / Act
    e = FaltaDadosError(campos_ausentes=[])

    # Assert
    assert "Dados incompletos" in e.mensagem
    assert e.metadados["campos_ausentes"] == []


# ===========================================================================
# DataInvalidaError
# ===========================================================================


def test_data_invalida_message_and_metadata_carry_date_and_motivo() -> None:
    """Both the mensagem and metadados expose ``data_fornecida`` + ``motivo``."""
    # Arrange / Act
    e = DataInvalidaError(data_fornecida="01/06/2026", motivo="formato incorreto")

    # Assert
    assert "01/06/2026" in e.mensagem
    assert "formato incorreto" in e.mensagem
    assert e.metadados["data_fornecida"] == "01/06/2026"
    assert e.metadados["motivo"] == "formato incorreto"


# ===========================================================================
# ValorForaRangeError
# ===========================================================================


def test_valor_fora_range_message_includes_field_value_and_bounds() -> None:
    """Mensagem mentions the field name, the offending value, and the range."""
    # Arrange / Act
    e = ValorForaRangeError(campo="horas", valor=99, minimo=0, maximo=24)

    # Assert
    for fragment in ("horas", "99", "0", "24"):
        assert fragment in e.mensagem


def test_valor_fora_range_metadata_preserves_all_four_fields() -> None:
    """``metadados`` keeps the original ``campo``/``valor``/``minimo``/``maximo``."""
    # Arrange / Act
    e = ValorForaRangeError(campo="horas", valor=99, minimo=0, maximo=24)

    # Assert
    assert e.metadados == {
        "campo": "horas",
        "valor": 99,
        "minimo": 0,
        "maximo": 24,
    }


def test_valor_fora_range_accepts_non_integer_bounds() -> None:
    """Bounds and value are typed as ``Any`` — floats / strings pass through."""
    # Arrange / Act
    e = ValorForaRangeError(
        campo="temperatura",
        valor=99.9,
        minimo=36.0,
        maximo=42.0,
    )

    # Assert
    assert e.metadados["valor"] == 99.9
    assert e.metadados["minimo"] == 36.0
    assert e.metadados["maximo"] == 42.0


# ===========================================================================
# LimitePomodoroExcedidoError
# ===========================================================================


def test_limite_pomodoro_uses_default_24_when_no_max_given() -> None:
    """Default ``max_limite=24`` is reflected in mensagem and metadata."""
    # Arrange / Act
    e = LimitePomodoroExcedidoError(quantidade=30)

    # Assert
    assert "24" in e.mensagem
    assert e.metadados == {"quantidade": 30, "limite_max": 24}


def test_limite_pomodoro_respects_custom_max() -> None:
    """Explicit ``max_limite`` overrides the default of 24."""
    # Arrange / Act
    e = LimitePomodoroExcedidoError(quantidade=15, max_limite=10)

    # Assert
    assert "10" in e.mensagem
    assert e.metadados == {"quantidade": 15, "limite_max": 10}


# ===========================================================================
# RepositorioVazioError
# ===========================================================================


def test_repositorio_vazio_without_date_uses_generic_message() -> None:
    """With ``data=None`` the message does not mention any date."""
    # Arrange / Act
    e = RepositorioVazioError(entidade="sleep_record")

    # Assert
    assert "sleep_record" in e.mensagem
    assert e.metadados == {"entidade": "sleep_record", "data": None}


def test_repositorio_vazio_with_date_includes_iso_date_in_message(
    sample_date: date,
) -> None:
    """With ``data=<date>`` the message includes the ISO-formatted date."""
    # Arrange
    d = sample_date

    # Act
    e = RepositorioVazioError(entidade="day_context", data=d)

    # Assert
    assert "day_context" in e.mensagem
    assert "2026-06-07" in e.mensagem
    assert e.metadados == {"entidade": "day_context", "data": d}


# ===========================================================================
# ConfiguracaoInvalidaError
# ===========================================================================


def test_configuracao_invalida_metadata_carries_all_three_fields() -> None:
    """``metadados`` includes ``parametro``, ``valor`` and ``esperado``."""
    # Arrange / Act
    e = ConfiguracaoInvalidaError(
        parametro="MAX_POMODOROS",
        valor=100,
        esperado="<= 24",
    )

    # Assert
    assert e.metadados == {
        "parametro": "MAX_POMODOROS",
        "valor": 100,
        "esperado": "<= 24",
    }


def test_configuracao_invalida_message_mentions_param_val_and_expected() -> None:
    """Mensagem embeds parametro, valor (repr) and the expected constraint."""
    # Arrange / Act
    e = ConfiguracaoInvalidaError(
        parametro="MAX_POMODOROS",
        valor=100,
        esperado="<= 24",
    )

    # Assert
    assert "MAX_POMODOROS" in e.mensagem
    assert "100" in e.mensagem
    assert "<= 24" in e.mensagem


# ===========================================================================
# raise / catch semantics
# ===========================================================================


def test_can_raise_and_catch_with_pytest_raises() -> None:
    """Exceptions are raisable and pytest captures their metadata intact."""
    # Arrange / Act / Assert
    with pytest.raises(FaltaDadosError) as excinfo:
        raise FaltaDadosError(campos_ausentes=["a", "b"], contexto="pytest")

    # Assert
    assert excinfo.value.metadados["campos_ausentes"] == ["a", "b"]
    assert excinfo.value.metadados["contexto"] == "pytest"


def test_str_returns_mensagem_for_subclass() -> None:
    """``str(subclass_exc)`` returns the subclass mensagem (no class name leak)."""
    # Arrange / Act
    e = LimitePomodoroExcedidoError(quantidade=99, max_limite=24)

    # Assert
    assert str(e) == e.mensagem
    assert "99" in str(e)
    assert "24" in str(e)
