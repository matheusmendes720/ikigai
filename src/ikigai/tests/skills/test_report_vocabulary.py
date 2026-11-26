"""PASS 1 — the Report step speaks the owner's levels, not the DOM kinds.

The owner reads Sonho / Objetivo / Meta / Tarefa / Atividade (router.md §4). The
Report step of a cadence skill must name those levels, never a lowercase DOM
kind. Case-sensitive: the capitalized level "Tarefa" is not the kind "tarefa".
Scoped to the Report step only — the search steps legitimately name kinds.

Falsification: add `kinds=(plano, onda)` to a Report step and this fails.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]

_DOM_KINDS = (
    "sonho",
    "plano",
    "onda",
    "fase",
    "revisao",
    "nota",
    "kpi",
    "desc",
    "okr",
    "tarefa",
)


def _report_step(skill_text: str) -> str:
    lines = skill_text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^\d+\.\s", line) and "Render the report per the Response Contract" in line:
            start = i
            break
    assert start is not None, "the skill has no Report step rendering the Response Contract"
    block = [lines[start]]
    for line in lines[start + 1 :]:
        if re.match(r"^\d+\.\s", line) or line.startswith("#"):
            break
        block.append(line)
    return "\n".join(block)


@pytest.mark.parametrize("skill", ["weekly-review", "daily-note"])
def test_the_report_step_names_no_dom_kind(skill: str) -> None:
    text = (REPO_ROOT / "specs" / "harness" / "skills" / skill / "SKILL.md").read_text(
        encoding="utf-8"
    )
    step = _report_step(text)
    offenders = [kind for kind in _DOM_KINDS if re.search(rf"\b{kind}\b", step)]
    assert not offenders, f"{skill} Report step names DOM kinds {offenders}; use the five levels"
