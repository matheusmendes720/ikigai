from src.contracts.common import PaeCyclePhase, PlanTier, VectorKey


def test_pae_cycle_phase_is_literal():
    assert PaeCyclePhase.__args__ == ("plan", "adjust", "evaluate")


def test_plan_tier_is_literal():
    assert PlanTier.__args__ == ("SONHO", "QUARTERLY", "ONDA", "WEEKLY", "DAILY")


def test_vector_key_is_literal():
    assert VectorKey.__args__ == ("passion", "skill", "market", "revenue", "course")
