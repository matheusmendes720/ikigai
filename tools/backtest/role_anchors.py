"""M114e — role_anchors.py

Maps the 73 padded backtest scenarios (M114a + M114d) to the 11 role-anchor
requirements from M113 v2 spec (drawn from strategics/ + algorithm-attribution).

Each scenario touches 1+ anchors. The harness (M114b) checks per-scenario
anchor coverage; the report (M114g) prints the matrix. Coverage targets:

  - All 11 anchors must be exercised by >=3 scenarios each.
  - Every scenario should map to its primary category + 1-2 secondary anchors.
  - Coverage holes trigger synthetic additions at runtime.

This file is the canonical "what does the harness measure" map; future tuning
of which tool fires for which role goes here.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.backtest.seed_q3_scenarios import (  # noqa: E402
    CATEGORY_COUNTS,
    CATEGORY_EXPECTED_TOOLS,
)


@dataclass(frozen=True)
class RoleAnchor:
    id: int
    name: str
    source: str  # file path for traceability
    category_set: tuple[str, ...]  # scenarios tagged with these categories touch this anchor
    description_pt: str = ""
    description_en: str = ""


# 11 anchors from M113 v2 spec sections.
ROLE_ANCHORS: list[RoleAnchor] = [
    RoleAnchor(
        id=1,
        name="constitutional_sot_reader",
        source="strategics/00-INDICE-PROGRESSIVO.md",
        category_set=("daily-plan", "weekly-review"),
        description_pt="Le ./strategics/ PT-BR como regras canonicas (algoritmo-atribuicao sec.1)",
        description_en="Reads ./strategics/ PT-BR markdown as canonical business rules",
    ),
    RoleAnchor(
        id=2,
        name="dual_frame_temporal_tracker",
        source="strategics/Modelagem Operacional.md + Planejamento (E&T).md",
        category_set=("daily-plan", "weekly-review", "decompose"),
        description_pt="Acompanha PAE x Hierarquica (5 dias x 3 semanas x 3 meses)",
        description_en="Tracks PAE x Hierarchical cycles (5 days x 3 weeks x 3 months)",
    ),
    RoleAnchor(
        id=3,
        name="five_level_hierarchy_mapper",
        source="strategics/Modelagem Operacional.md",
        category_set=("decompose", "daily-plan", "weekly-review"),
        description_pt="Mapeia SONHOS -> OBJETIVOS -> METAS -> TAREFAS -> ATIVIDADES",
        description_en="Maps SONHOS -> OBJETIVOS -> METAS -> TAREFAS -> ATIVIDADES",
    ),
    RoleAnchor(
        id=4,
        name="tagging_system_conversant",
        source="strategics/Integracao_Tatica.md",
        category_set=("add-task", "list-tasks", "update-task"),
        description_pt="Usa #supervisao (E), #revisao/#relatorios (T), #narrativa/#to-do (O)",
        description_en="Uses tag conventions: #supervisao (E), #revisao/#relatorios (T), #narrativa/#to-do (O)",
    ),
    RoleAnchor(
        id=5,
        name="time_horizon_aware",
        source="strategics/Analise (Tatico e Operacional).md",
        category_set=("daily-plan", "weekly-review", "complete-task"),
        description_pt="Executa Rotina Inicial + Final; respeita ciclos Day 1/7/15/45/180",
        description_en="Executes Routine Inicial + Final; respects Day 1/7/15/45/180 cycles",
    ),
    RoleAnchor(
        id=6,
        name="vault_write_mcp_enforcer",
        source="docs/superpowers/specs/2026-08-29-algorithm-attribution-design.md sec.7",
        category_set=("add-task", "update-task", "decompose"),
        description_pt="Acessa vault SO via MCP tool; sem escrita direta no filesystem",
        description_en="Vault access strictly via MCP tool; no direct filesystem writes",
    ),
    RoleAnchor(
        id=7,
        name="taskdog_vault_propagation_driver",
        source="user message 2026-09-22 + M114f vault_diff.py",
        category_set=("complete-task", "weekly-review"),
        description_pt="Diferenca diff: vault deve refletir status atual do taskdog (sem auto-mutacao)",
        description_en="Drift diff: vault should reflect current taskdog timeline (no auto-mutation)",
    ),
    RoleAnchor(
        id=8,
        name="plan_update_on_the_fly_reflector",
        source="user message 2026-09-22 + strategics/Planejamento (E&T)#3.2",
        category_set=("update-task", "decompose", "weekly-review"),
        description_pt="Refatora plano mid-cycle; preserva historico append-only",
        description_en="Refactors plans mid-cycle; preserves append-only history",
    ),
    RoleAnchor(
        id=9,
        name="cross_routine_executor",
        source="strategics/Analise (T&O)#Rotina inicial/final",
        category_set=("daily-plan", "complete-task"),
        description_pt="Rotina Inicial (manha) + Final (noite) com checklist + block tracking",
        description_en="Routine Inicial (morning) + Final (evening) with checklist + block tracking",
    ),
    RoleAnchor(
        id=10,
        name="diagnostic_reporter",
        source="strategics/Hierarquia de Objetivos + telemetry hooks",
        category_set=("weekly-review", "list-tasks"),
        description_pt="Reporta qual nivel hierarquico quebrou + impacto telemetry + Correcao do Trajeto",
        description_en="Reports which hierarchy level broke + telemetry impact + Correcao do Trajeto",
    ),
    RoleAnchor(
        id=11,
        name="cultural_voice_compliance",
        source="strategics/00-INDICE-PROGRESSIVO.md + altitude-shifter skill",
        category_set=("daily-plan", "weekly-review", "decompose"),
        description_pt="Responde PT-BR; framing ABT; sem jargao stakeholder untranslated",
        description_en="Responds in PT-BR; ABT framing; no untranslated stakeholder jargon",
    ),
]


# Per-anchor coverage target: minimum scenarios that must exercise each anchor.
COVERAGE_TARGET: dict[int, int] = {
    1: 3, 2: 3, 3: 4, 4: 4, 5: 4, 6: 3, 7: 3, 8: 3, 9: 3, 10: 3, 11: 4,
}


@dataclass
class AnchorScenarioMap:
    """Maps scenarios to their role-anchor IDs.

    Primary anchor = the anchor the scenario primarily exercises (from category).
    Secondary anchors = anchors touched incidentally.
    """
    by_scenario_id: dict[int, list[int]] = field(default_factory=dict)
    by_anchor_id: dict[int, list[int]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenarios": {
                sid: sorted(aids) for sid, aids in sorted(self.by_scenario_id.items())
            },
            "anchors": {
                aid: sorted(sids) for aid, sids in sorted(self.by_anchor_id.items())
            },
        }


def _primary_anchor_for_category(cat: str) -> int:
    """Each scenario category has 1 most-relevant anchor."""
    mapping: dict[str, int] = {
        "add-task": 4,
        "list-tasks": 4,
        "update-task": 8,
        "complete-task": 7,
        "decompose": 3,
        "daily-plan": 2,
        "weekly-review": 10,
    }
    return mapping.get(cat, 1)


def build_scenario_anchor_map(scenarios: list[dict[str, Any]]) -> AnchorScenarioMap:
    """Walk every scenario, derive primary + secondary anchor IDs."""
    m = AnchorScenarioMap()
    cat_to_anchors: dict[str, list[int]] = {}
    for anchor in ROLE_ANCHORS:
        for cat in anchor.category_set:
            cat_to_anchors.setdefault(cat, []).append(anchor.id)

    for i, sc in enumerate(scenarios, 1):
        cat = sc.get("category", "")
        anchors: list[int] = []
        primary = _primary_anchor_for_category(cat)
        if primary and primary not in anchors:
            anchors.append(primary)
        for aid in cat_to_anchors.get(cat, []):
            if aid not in anchors:
                anchors.append(aid)
        m.by_scenario_id[sc.get("day", i)] = sorted(set(anchors))
        for aid in anchors:
            m.by_anchor_id.setdefault(aid, []).append(sc.get("day", i))
    return m


def coverage_report(m: AnchorScenarioMap) -> dict[str, Any]:
    matrix: dict[int, dict[str, Any]] = {}
    for anchor in ROLE_ANCHORS:
        current = len(m.by_anchor_id.get(anchor.id, []))
        target = COVERAGE_TARGET.get(anchor.id, 3)
        matrix[anchor.id] = {
            "name": anchor.name,
            "current": current,
            "target": target,
            "met": current >= target,
        }
    met = sum(1 for v in matrix.values() if v["met"])
    return {
        "total_anchors": len(matrix),
        "met_count": met,
        "unmet": [aid for aid, v in matrix.items() if not v["met"]],
        "matrix": matrix,
    }


def synthesize_gap_scenarios(
    coverage: dict[str, Any],
    cycle_start: str,
    next_day: int,
) -> list[dict[str, Any]]:
    """For each unmet anchor, forge one synthetic scenario."""
    from datetime import date, timedelta
    if not coverage["unmet"]:
        return []
    start = date.fromisoformat(cycle_start)
    out: list[dict[str, Any]] = []
    day = next_day
    for aid in coverage["unmet"]:
        anchor = next(a for a in ROLE_ANCHORS if a.id == aid)
        cat = anchor.category_set[0] if anchor.category_set else "daily-plan"
        tool = CATEGORY_EXPECTED_TOOLS.get(cat, ["taskdog_create_task"])[0]
        out.append({
            "day": day,
            "date": (start + timedelta(days=day - 1)).isoformat(),
            "category": cat,
            "prompt": (
                f"Synthetic scenario for unmet anchor #{aid} ({anchor.name}). "
                f"Source: {anchor.source}. "
                f"Agent should exhibit: {anchor.description_en}"
            ),
            "expected_tools": [tool],
            "expected_args": {
                "cluster": "ikigai/synthetic",
                "tags_any": ["role-anchor", f"anchor-{aid}"],
                "synthetic_for_anchor": aid,
            },
            "synthetic_for_anchor": aid,
        })
        day += 1
    return out


def build_full_role_anchor_corpus(
    scenarios: list[dict[str, Any]],
    cycle_start: str,
) -> dict[str, Any]:
    m = build_scenario_anchor_map(scenarios)
    cov1 = coverage_report(m)
    fillers = synthesize_gap_scenarios(cov1, cycle_start, next_day=len(scenarios) + 100)
    padded = list(scenarios) + fillers
    m2 = build_scenario_anchor_map(padded)
    cov2 = coverage_report(m2)
    return {
        "scenarios": padded,
        "coverage": cov2,
        "anchor_map": m2.to_dict(),
        "gap_fillers_added": len(fillers),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the role-anchor coverage matrix for a backtest scenario corpus.",
    )
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=REPO_ROOT / "vault" / "drafts" / "q3-scenarios.exhaustive.yaml",
        help="Path to padded scenarios YAML (output of M114d).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "vault" / "drafts" / "q3-scenarios.with-anchors.yaml",
        help="Output YAML path for padded corpus with anchor mapping.",
    )
    parser.add_argument(
        "--cycle-start",
        default="2026-09-22",
        help="Cycle start date (ISO YYYY-MM-DD).",
    )
    parser.add_argument("--dry-run", action="store_true", help="print summary, do not write")
    args = parser.parse_args(argv)

    import yaml  # noqa: E402

    if not args.scenarios.exists():
        print(f"# Missing: {args.scenarios}. Run M114d first.", file=sys.stderr)
        return 1
    src = yaml.safe_load(args.scenarios.read_text(encoding="utf-8"))
    scenarios = src.get("scenarios", []) if isinstance(src, dict) else src
    if not scenarios:
        print("# Empty scenarios list.", file=sys.stderr)
        return 1

    result = build_full_role_anchor_corpus(scenarios, args.cycle_start)
    cov = result["coverage"]
    summary = {
        "scenarios_in": len(scenarios),
        "scenarios_out": len(result["scenarios"]),
        "gap_fillers_added": result["gap_fillers_added"],
        "anchors_total": cov["total_anchors"],
        "anchors_met": cov["met_count"],
        "anchors_unmet": cov["unmet"],
    }
    if args.dry_run:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        print("# Coverage matrix:")
        for aid in sorted(cov["matrix"]):
            v = cov["matrix"][aid]
            flag = "OK" if v["met"] else "MISS"
            print(f"  #{aid:2} {v['name']:<40} {v['current']}/{v['target']} {flag}")
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        yaml.safe_dump(result, sort_keys=False, allow_unicode=True, width=120),
        encoding="utf-8",
    )
    print(f"# Wrote {len(result['scenarios'])} scenarios + anchor_map -> {args.out}")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
