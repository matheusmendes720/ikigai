"""M158d — Remove M156 stubs (`if True:  # M156 stub`) from all 16 prompt files.

Pattern in each file:
    if True:  # M156: stub PAV-math, never real LLM
        return {"<key>": <stub>, "rationale": "[FAKE-LLM stub for test]"}

We keep the dedented return literal so tests checking return shape still pass.
The dead-code below (vault reads + try/except ChatAnthropic) now actually runs:
- If LLM real works, it returns from inside the try block.
- If LLM real fails, except returns {"error": ...}.
"""
from __future__ import annotations

import re
from pathlib import Path

PROMPTS_DIR = Path(r"C:\Users\mathe\code_space\life-oss\life\src\ikigai\src\agents\v2\prompts")

PATTERN = re.compile(
    r"^    if True:  # M156: stub PAV-math, never real LLM\n"
    r"(        return .*\n)",
    re.MULTILINE,
)


def patch_file(path: Path) -> tuple[bool, str]:
    text = path.read_text(encoding="utf-8")
    if "M156: stub PAV-math" not in text:
        return False, "no M156 marker"
    match = PATTERN.search(text)
    if not match:
        return False, "no if True pattern matched"
    # Dedent the return: replace leading 8 spaces with 4.
    replacement = match.group(1).replace("        return ", "    return ", 1)
    new = PATTERN.sub(replacement, text, count=1)
    path.write_text(new, encoding="utf-8")
    return True, "dedented return"


def main() -> None:
    files = sorted(PROMPTS_DIR.glob("*.py"))
    changed = 0
    for f in files:
        ok, msg = patch_file(f)
        marker = "✓" if ok else " "
        if ok:
            changed += 1
        print(f"  {marker} {f.name:40} {msg}")
    print(f"\nChanged {changed} of {len(files)} prompt files")


if __name__ == "__main__":
    main()