from pipeline.policy_engine import PolicyEngine
from schemas.pydantic_v2 import PolicyState
from datetime import date

def test_policy_transitions():
    engine = PolicyEngine()
    
    # 1. Test: Critical Severity -> RECOVER
    metrics_critical = {"infractions": 3, "consistency": 0.4}
    decision = engine.evaluate(metrics_critical)
    print(f"Metrics: {metrics_critical} -> Policy: {decision.policy}")
    assert decision.policy == PolicyState.RECOVER

    # 2. Test: High Severity from PUSH -> MAINTAIN
    metrics_high = {"infractions": 1, "consistency": 0.8}
    # Create a dummy previous decision in PUSH
    prev_push = engine.evaluate({"infractions": 0, "consistency": 0.95})
    prev_push.policy = PolicyState.PUSH
    prev_push.days_in_current_policy = 5
    
    decision = engine.evaluate(metrics_high, prev_decision=prev_push)
    print(f"Metrics (High) from PUSH -> Policy: {decision.policy}")
    assert decision.policy == PolicyState.MAINTAIN

    # 3. Test: Low Severity + High Consistency -> PUSH (after 3 days)
    metrics_low = {"infractions": 0, "consistency": 0.95, "hours_deviation": 0.0}
    prev_maintain = engine.evaluate(metrics_low)
    prev_maintain.policy = PolicyState.MAINTAIN
    prev_maintain.days_in_current_policy = 3
    
    decision = engine.evaluate(metrics_low, prev_decision=prev_maintain)
    print(f"Metrics (Low/Consist) from MAINTAIN (3d) -> Policy: {decision.policy}")
    assert decision.policy == PolicyState.PUSH

    print("\nTodos os testes de transição de política passaram!")

if __name__ == "__main__":
    test_policy_transitions()
