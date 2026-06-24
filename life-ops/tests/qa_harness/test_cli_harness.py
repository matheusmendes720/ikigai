"""Auto-generated QA tests — produced by tdd_agent."""
"""Auto-generated QA tests — produced by tdd_agent."""
from __future__ import annotations

import pytest
import subprocess
import json
from datetime import date

_ROOT = Path(__file__).resolve().parents[3]


def run_pav(args: str, timeout: int = 30) -> tuple[int, str, str]:
    cmd = ["uv", "run", "--directory", str(_ROOT), "pav", *args.split()]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout or "", r.stderr or ""


def test_habit_list_json() -> None:
    """Test: habit list --json"""\n    exit_code, stdout, stderr = run_pav('habit list --json')
    assert exit_code == 0, f'non-zero exit: {{stderr[:200]}}'
    data = json.loads(stdout)
    assert isinstance(data, (dict, list)), 'expected JSON dict or list'
    assert stdout.strip(), 'expected non-empty output'

def test_routine_list_json() -> None:
    """Test: routine list --json"""\n    exit_code, stdout, stderr = run_pav('routine list --json')
    assert exit_code == 0, f'non-zero exit: {{stderr[:200]}}'
    data = json.loads(stdout)
    assert isinstance(data, (dict, list)), 'expected JSON dict or list'
    assert stdout.strip(), 'expected non-empty output'

def test_metric_list_json() -> None:
    """Test: metric list --json"""\n    exit_code, stdout, stderr = run_pav('metric list --json')
    assert exit_code == 0, f'non-zero exit: {{stderr[:200]}}'
    data = json.loads(stdout)
    assert isinstance(data, (dict, list)), 'expected JSON dict or list'
    assert stdout.strip(), 'expected non-empty output'

def test_policy_decisions_json() -> None:
    """Test: policy decisions --json"""\n    exit_code, stdout, stderr = run_pav('policy decisions --json')
    assert exit_code == 0, f'non-zero exit: {{stderr[:200]}}'
    data = json.loads(stdout)
    assert isinstance(data, (dict, list)), 'expected JSON dict or list'
    assert stdout.strip(), 'expected non-empty output'

def test_state_show_json() -> None:
    """Test: state show --json"""\n    exit_code, stdout, stderr = run_pav('state show --json')
    assert exit_code == 0, f'non-zero exit: {{stderr[:200]}}'
    data = json.loads(stdout)
    assert isinstance(data, (dict, list)), 'expected JSON dict or list'
    assert stdout.strip(), 'expected non-empty output'

def test_report_daily_json() -> None:
    """Test: report daily --json"""\n    exit_code, stdout, stderr = run_pav('report daily --json')
    assert exit_code == 0, f'non-zero exit: {{stderr[:200]}}'
    data = json.loads(stdout)
    assert isinstance(data, (dict, list)), 'expected JSON dict or list'
    assert stdout.strip(), 'expected non-empty output'

def test_report_weekly_json() -> None:
    """Test: report weekly --json"""\n    exit_code, stdout, stderr = run_pav('report weekly --json')
    assert exit_code == 0, f'non-zero exit: {{stderr[:200]}}'
    data = json.loads(stdout)
    assert isinstance(data, (dict, list)), 'expected JSON dict or list'
    assert stdout.strip(), 'expected non-empty output'

def test_demo_show_json() -> None:
    """Test: demo show --json"""\n    exit_code, stdout, stderr = run_pav('demo show --json')
    assert exit_code == 0, f'non-zero exit: {{stderr[:200]}}'
    data = json.loads(stdout)
    assert isinstance(data, (dict, list)), 'expected JSON dict or list'
    assert stdout.strip(), 'expected non-empty output'

def test_reflect_list_json() -> None:
    """Test: reflect list --json"""\n    exit_code, stdout, stderr = run_pav('reflect list --json')
    assert exit_code == 0, f'non-zero exit: {{stderr[:200]}}'
    data = json.loads(stdout)
    assert isinstance(data, (dict, list)), 'expected JSON dict or list'
    assert stdout.strip(), 'expected non-empty output'

def test_lunch_list_json() -> None:
    """Test: lunch list --json"""\n    exit_code, stdout, stderr = run_pav('lunch list --json')
    assert exit_code == 0, f'non-zero exit: {{stderr[:200]}}'
    data = json.loads(stdout)
    assert isinstance(data, (dict, list)), 'expected JSON dict or list'
    assert stdout.strip(), 'expected non-empty output'

def test_doctor_json() -> None:
    """Test: doctor --json"""\n    exit_code, stdout, stderr = run_pav('doctor --json')
    assert exit_code == 0, f'non-zero exit: {{stderr[:200]}}'
    data = json.loads(stdout)
    assert isinstance(data, (dict, list)), 'expected JSON dict or list'
    assert stdout.strip(), 'expected non-empty output'

