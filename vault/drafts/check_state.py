"""Check actual state of 5 supposed-updated files."""
from pathlib import Path

STRATEGICS_DIR = Path(r"C:\Users\mathe\code_space\life-oss\life\strategics")

files = [
    "Planejamento (Estratégico e Tático).md",
    "Hierarquia de Objetivos.md",
    "Desempenho Subjacente.md",
    "Integracao_Tatica.md",
    "Análise (Tático e Operacional).md",
]

for filename in files:
    path = STRATEGICS_DIR / filename
    if not path.exists():
        print(f"MISSING: {filename}")
        continue
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"ERROR reading {filename}: {e}")
        continue
    # Find the first heading
    lines = content.split("\n")
    head = "\n".join(lines[:8])
    has_central = "Central Engine" in content
    print(f"=== {filename} ===")
    print(f"  Has 'Central Engine': {has_central}")
    print(f"  Length: {len(content)} chars, {len(lines)} lines")
    print(f"  First 5 lines:")
    for line in lines[:5]:
        print(f"    {line!r}")
    print()