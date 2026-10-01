"""reflection — agent self-review layer.

Stores every agent decision in vault/ikigai/decisions/<date>.jsonl and
periodically reflects on the decision log to surface patterns and
suggested adjustments.

Per ADR-013 the agent is planner-only — this is observational memory, not
policy execution. Patterns detected here become Proposals the human
adjudicates (analogous to taskdog_triage / vault_intent_extract skills).
"""