"""AI-slop and quality scan for PAE source + tests."""
import re
import pathlib

PATTERNS = [
    "TODO",
    "FIXME",
    "HACK",
    "XXX",
    "console.log",
    ": any",
    " as any",
    "pass  # stub",
    "NotImplementedError",
    "raise NotImplementedError",
    "stub",
    "placeholder",
    "@ts-ignore",
]
EXCLUDE_LINE_CONTAINING = ["# reason"]  # comments explaining remain


def scan(file_path: pathlib.Path) -> dict[str, list[tuple[int, str]]]:
    out: dict[str, list[tuple[int, str]]] = {}
    if not file_path.exists():
        return {"MISSING": [(0, "file not found")]}
    txt = file_path.read_text(encoding="utf-8")
    for i, line in enumerate(txt.splitlines(), start=1):
        for p in PATTERNS:
            for m in re.finditer(re.escape(p), line):
                out.setdefault(p, []).append((i, line.strip()))
    return out


def show(name: str, hits: dict) -> None:
    if not hits:
        print(f"  {name}: CLEAN")
        return
    print(f"  {name}: {len(hits)} pattern(s) found")
    for p, lines in hits.items():
        print(f"    [{p}] {len(lines)} occurrence(s):")
        for ln, content in lines[:3]:
            print(f"      L{ln}: {content[:140]}")
        if len(lines) > 3:
            print(f"      ... +{len(lines) - 3} more")


print("=== SOURCE: vibe-ops/src/agents/pae_maintainer/ ===")
src_files = [
    pathlib.Path("vibe-ops/src/agents/pae_maintainer/state.py"),
    pathlib.Path("vibe-ops/src/agents/pae_maintainer/nodes.py"),
    pathlib.Path("vibe-ops/src/agents/pae_maintainer/channels.py"),
    pathlib.Path("vibe-ops/src/agents/pae_maintainer/graph.py"),
    pathlib.Path("vibe-ops/src/agents/pae_maintainer/main.py"),
    pathlib.Path("vibe-ops/src/agents/pae_maintainer/__init__.py"),
    pathlib.Path("vibe-ops/src/agents/pae_maintainer/__main__.py"),
]
for f in src_files:
    show(f.name, scan(f))

print()
print("=== TESTS: vibe-ops/tests (PAE-related) ===")
test_files = [
    pathlib.Path("vibe-ops/tests/test_pae_state.py"),
    pathlib.Path("vibe-ops/tests/test_pae_nodes.py"),
    pathlib.Path("vibe-ops/tests/test_pae_cli.py"),
    pathlib.Path("vibe-ops/tests/integration/test_pae_channels.py"),
    pathlib.Path("vibe-ops/tests/integration/test_pae_graph.py"),
    pathlib.Path("vibe-ops/tests/property/test_pae_balancer.py"),
    pathlib.Path("vibe-ops/tests/e2e/test_pae_q1_2026.py"),
]
for f in test_files:
    show(f.name, scan(f))
