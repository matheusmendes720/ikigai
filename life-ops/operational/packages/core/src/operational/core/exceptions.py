"""Custom domain exceptions for the operational CLI.

These exceptions carry rich metadata so the UI layer can produce
context-aware error panels. All inherit from a single ``DomainError``
base class so callers can catch everything with a single ``except`` if
they want to.
"""
from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Base class for all business-logic errors in the operational CLI.

    Carries a human-readable message AND a metadata dict that the UI
    layer can inspect to build a context-aware error panel.
    """

    def __init__(self, mensagem: str, metadados: dict[str, Any] | None = None) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.metadados = metadados or {}

    def __str__(self) -> str:
        return self.mensagem


class FaltaDadosError(DomainError):
    """Required data is missing (column, field, repository)."""

    def __init__(self, *, campos_ausentes: list[str], contexto: str = "") -> None:
        msg = f"Dados incompletos. Campos ausentes: {', '.join(campos_ausentes)}."
        if contexto:
            msg = f"{msg} (contexto: {contexto})"
        super().__init__(msg, {"campos_ausentes": campos_ausentes, "contexto": contexto})


class DataInvalidaError(DomainError):
    """A date string is malformed or out of range."""

    def __init__(self, *, data_fornecida: str, motivo: str) -> None:
        msg = f"Data inválida '{data_fornecida}'. Motivo: {motivo}."
        super().__init__(msg, {"data_fornecida": data_fornecida, "motivo": motivo})


class ValorForaRangeError(DomainError):
    """A numeric value is outside its allowed range."""

    def __init__(self, *, campo: str, valor: Any, minimo: Any, maximo: Any) -> None:
        msg = f"'{campo}'={valor} fora do range [{minimo}, {maximo}]."
        super().__init__(msg, {"campo": campo, "valor": valor, "minimo": minimo, "maximo": maximo})


class LimitePomodoroExcedidoError(DomainError):
    """A pomodoro count exceeds the physiological maximum per day."""

    def __init__(self, quantidade: int, max_limite: int = 24) -> None:
        msg = f"Quantidade de Pomodoros absurda ({quantidade}). Limite diário: {max_limite}."
        super().__init__(msg, {"quantidade": quantidade, "limite_max": max_limite})


class RepositorioVazioError(DomainError):
    """A repository that should have data is empty (e.g. demo not seeded)."""

    def __init__(self, *, entidade: str, data: date | None = None) -> None:
        if data:
            msg = f"Nenhum registro de '{entidade}' para a data {data.isoformat()}."
        else:
            msg = f"Nenhum registro de '{entidade}' encontrado."
        super().__init__(msg, {"entidade": entidade, "data": data})


class ConfiguracaoInvalidaError(DomainError):
    """Configuration is missing or wrong (constants out of range, etc)."""

    def __init__(self, *, parametro: str, valor: Any, esperado: str) -> None:
        msg = f"Configuração inválida: '{parametro}'={valor!r}. Esperado: {esperado}."
        super().__init__(msg, {"parametro": parametro, "valor": valor, "esperado": esperado})


__all__ = [
    "DomainError",
    "FaltaDadosError",
    "DataInvalidaError",
    "ValorForaRangeError",
    "LimitePomodoroExcedidoError",
    "RepositorioVazioError",
    "ConfiguracaoInvalidaError",
]
