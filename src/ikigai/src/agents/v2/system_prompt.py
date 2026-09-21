"""System prompt template assembly (decision #2)."""

from __future__ import annotations

from collections.abc import Iterable

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


def assemble(
    profile: str,
    capabilities: Iterable[str],
    scope: str,
    soul_content: str | None = None,
) -> str:
    """Build the system prompt.

    If ``soul_content`` is provided, use it directly (avoids a redundant
    ``load_soul`` call when the caller has already loaded the soul for
    other purposes — e.g. the chat REPL extracting voice + constraints).
    Otherwise the soul is loaded from disk via ``load_soul(profile)``.
    """
    if soul_content is None:
        soul_content = load_soul(profile)
    cap_lines = "\n".join(f"- {cap}" for cap in capabilities)
    return _TEMPLATE.format(
        soul_content=soul_content,
        capabilities_block=cap_lines,
        scope=scope,
    )
