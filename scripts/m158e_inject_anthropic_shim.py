"""M158e — Inject langchain_anthropic_shim import before all 16 prompts.

Each prompt file has:
    try:
        from langchain_anthropic import ChatAnthropic
        ...

We add BEFORE the try:
    import agents.v2.langchain_anthropic_shim  # noqa: F401
"""
from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(r"C:\Users\mathe\code_space\life-oss\life\src\ikigai\src\agents\v2\prompts")

SHIM_LINE = "        import agents.v2.langchain_anthropic_shim  # noqa: F401  # M158e\n"
TARGET = "        from langchain_anthropic import ChatAnthropic\n"


def patch_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if TARGET not in text:
        return False
    if "langchain_anthropic_shim" in text:
        return False  # already patched
    new = text.replace(TARGET, SHIM_LINE + TARGET, 1)
    path.write_text(new, encoding="utf-8")
    return True


def main() -> None:
    for f in sorted(PROMPTS_DIR.glob("*.py")):
        if patch_file(f):
            print(f"  ✓ {f.name}")
        else:
            pass


if __name__ == "__main__":
    main()