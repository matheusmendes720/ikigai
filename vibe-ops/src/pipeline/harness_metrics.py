import re
from typing import Dict, Any
from models import ChangelogEntry

class MetricsHarness:
    """
    Extrai métricas de qualidade e progresso a partir de logs e changelogs.
    """
    
    @staticmethod
    def extract_test_metrics(changelog: ChangelogEntry) -> Dict[str, Any]:
        """Extrai taxa de sucesso de testes e cobertura do campo test_results."""
        passed = re.search(r'(\d+) passed', changelog.test_results)
        failed = re.search(r'(\d+) failed', changelog.test_results)
        coverage = re.search(r'Coverage:\s*(\d+)%', changelog.test_results)
        
        return {
            "passed": int(passed.group(1)) if passed else 0,
            "failed": int(failed.group(1)) if failed else 0,
            "coverage_pct": float(coverage.group(1)) if coverage else None
        }

    @staticmethod
    def analyze_stack_trace(changelog: ChangelogEntry) -> bool:
        """Verifica se há erros críticos no stack trace."""
        if not changelog.stack_trace:
            return False
        critical_keywords = ["MemoryError", "RecursionError", "Segmentation fault"]
        return any(kw in changelog.stack_trace for kw in critical_keywords)
