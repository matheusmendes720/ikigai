"""System prompt template assembly (decision #2)."""
from __future__ import annotations
from typing import Iterable
from src.ikigai.souls.loader import load_soul

_TEMPLATE = """<SYSTEM>
<SOUL>
{soul_content}
</SOUL>

<CAPABILITIES>
{capabilities_block}
</CAPABILITIES>

<SCOPE>
{scope}
</SCOPE>
</SYSTEM>"""


def assemble(profile: str, capabilities: Iterable[str], scope: str) -> str:
    soul_content = load_soul(profile)
    cap_lines = "\n".join(f"- {cap}" for cap in capabilities)
    return _TEMPLATE.format(soul_content=soul_content, capabilities_block=cap_lines, scope=scope)
