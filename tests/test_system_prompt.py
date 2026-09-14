import sys
sys.path.insert(0, "src/ikigai/src/agents/v2")
import system_prompt


def test_assemble_includes_soul_content():
    out = system_prompt.assemble("ikigai-planner", ["tool: read"], "scope: strict")
    assert "<SOUL>" in out
    assert "<CAPABILITIES>" in out
    assert "<SCOPE>" in out


def test_assemble_includes_capabilities():
    out = system_prompt.assemble("ikigai-critic", ["tool: ask", "tool: probe"], "")
    assert "tool: ask" in out


def test_assemble_includes_scope():
    out = system_prompt.assemble("ikigai-stoic", [], "never panic")
    assert "never panic" in out


def test_assemble_uses_soul_loader():
    out = system_prompt.assemble("ikigai-planner", [], "")
    assert len(out) > 200
