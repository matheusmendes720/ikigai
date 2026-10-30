import re
from typing import Any

from models import ChangelogEntry

_PASSED_RE = re.compile(r"(\d+)\s+passed")
_FAILED_RE = re.compile(r"(\d+)\s+failed")
_COVERAGE_RE = re.compile(r"Coverage:\s*(\d+(?:\.\d+)?)%")


def _as_int(value: Any, pattern: re.Pattern[str], blob: str) -> int:
    """Extrai um inteiro de uma chave direta ou, na falta, do texto agregado."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        match = pattern.search(value)
        if match:
            return int(match.group(1))
    match = pattern.search(blob)
    return int(match.group(1)) if match else 0


def _as_float(value: Any, pattern: re.Pattern[str], blob: str) -> float | None:
    """Extrai um float de uma chave direta ou, na falta, do texto agregado."""
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = pattern.search(value)
        if match:
            return float(match.group(1))
    match = pattern.search(blob)
    return float(match.group(1)) if match else None


class MetricsHarness:
    """
    Extrai métricas de qualidade e progresso a partir de logs e changelogs.
    """

    @staticmethod
    def extract_test_metrics(changelog: ChangelogEntry) -> dict[str, Any]:
        """Extrai taxa de sucesso de testes e cobertura do campo test_results.

        `ChangelogEntry.test_results` é um dicionário livre. São aceitos tanto
        chaves numéricas diretas (`passed`, `failed`, `coverage_pct`) quanto
        valores textuais no formato legado ("12 passed, 1 failed, Coverage: 84%").
        """
        results = changelog.test_results or {}
        blob = " ".join(str(value) for value in results.values())

        return {
            "passed": _as_int(results.get("passed"), _PASSED_RE, blob),
            "failed": _as_int(results.get("failed"), _FAILED_RE, blob),
            "coverage_pct": _as_float(results.get("coverage_pct"), _COVERAGE_RE, blob),
        }

    @staticmethod
    def analyze_stack_trace(changelog: ChangelogEntry) -> bool:
        """Verifica se há erros críticos no stack trace.

        `ChangelogEntry` não expõe `stack_trace` como campo dedicado; o texto
        fica nos dicionários livres `test_results` / `code_metrics`.
        """
        stack_trace = changelog.test_results.get("stack_trace") or changelog.code_metrics.get(
            "stack_trace"
        )
        if not isinstance(stack_trace, str) or not stack_trace:
            return False
        critical_keywords = ["MemoryError", "RecursionError", "Segmentation fault"]
        return any(kw in stack_trace for kw in critical_keywords)
