"""M156 — stub 14 PAV-math prompts by always returning the FAKE_LLM stub.

ADR-013: PAV-math is OUT of scope. We patch each render function to
always return the deterministic stub instead of the LLM call path.
The LLM function bodies are preserved (in case PAV reactivation is
later approved) but never executed.
"""
import re
from pathlib import Path

PROMPTS_DIR = Path(r"src\ikigai\src\agents\v2\prompts")

targets = [
    "h1_energy.py",
    "h2_qhe_composite.py",
    "h3_regime_fsm.py",
    "h4_market_fit.py",
    "h5_skill_velocity.py",
    "h6_severity.py",
    "score_passion_observation.py",
    "score_skill_observation.py",
    "score_market_observation.py",
    "score_revenue_observation.py",
    "score_course_observation.py",
    "score_meta_vector_observation.py",
    "observe_qhe_observation.py",
    "heuristics_regime_observation.py",
    "decompose_rice_observation.py",
    "surface_pav_intentions.py",
]

# Match: if os.environ.get("IKIGAI_FAKE_LLM", "0") == "1":
# Use raw string and single quotes inside to avoid escape hell
pattern = (
    r'if os\.environ\.get\("IKIGAI_FAKE_LLM",\s*"0"\)\s*==\s*"1":'
)

replacement = (
    'if True:  # M156: stub PAV-math, never real LLM (ADR-013 / M70)'
)

for name in targets:
    p = PROMPTS_DIR / name
    if not p.exists():
        print(f"MISSING: {name}")
        continue
    text = p.read_text(encoding="utf-8")
    new_text, n = re.subn(pattern, replacement, text)
    if n == 0:
        print(f"NO MATCH in {name}")
        continue
    # Update docstrings to reflect new behavior
    new_text = new_text.replace(
        "(or deterministic stub in fake mode)",
        "(always stub per ADR-013 / M156)",
    )
    new_text = new_text.replace(
        "(or deterministic stub in FAKE_LLM mode)",
        "(always stub per ADR-013 / M156)",
    )
    p.write_text(new_text, encoding="utf-8")
    print(f"OK: {name} ({n} gate(s) replaced)")
