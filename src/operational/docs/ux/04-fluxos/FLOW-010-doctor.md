# FLOW-010 — Diagnosticar Problemas (doctor)

> **Wireflow ASCII:** ver bloco "Fluxo principal" abaixo. Notação: oval = início/fim, retângulo = tela, losango = decisão, paralelogramo = input, tracejada = exceção.

**Objetivo do usuário:** "Algo quebrou. Em menos de 1 minuto eu descobri se é: Python desatualizado, pacotes faltando, state dir corrompido, ou um bug de dados."

**Ponto de entrada:**
- `operational home` → `10` (Sistema) — opção 10 mostra info estática, **não** doctor. UX-009: incoerência.
- Comando direto: `operational doctor` (forma comum)
- Comando direto: `operational doctor --json` (CI)

**Pré-condições:**
- Nenhuma. Doctor é read-only — não altera state.

**Telas envolvidas:**
- SCR-021 Doctor Panel (7 checks com ícone OK/FAIL)
- SCR-022 Doctor Issues (se algum check falhar)

**Componentes críticos:**
- CMP-019 Doctor Panel — `cli/commands/doctor_cmd.py:213-250` (Panel custom com Table.grid)
- CMP-004 error_panel (se exception durante checks)

**Duração típica:** 1s (7 checks, todos in-memory ou leitura de arquivos pequenos)

**Taxa de abandono estimada:** 0% (read-only, sem side effects)

---

## Fluxo principal (happy path)

1. User digita `operational doctor` (forma comum) ou `operational doctor --json` (CI).
2. `doctor_cmd.doctor_cmd` (`cli/commands/doctor_cmd.py:191-250`):
   - Cria dict `results` com 7 checks:
     1. `python` — `sys.version_info >= (3, 10)` (`_check_python`, linhas 33-40)
     2. `packages` — Typer, Rich, Pydantic instalados (`_check_packages`, linhas 43-56)
     3. `state_dir` — `~/.time-tasker/` existe, writable, 14 JSONs parseáveis (`_check_state_dir`, linhas 59-100)
     4. `datasets` — env var `TIME_TASKER_DATASET` + CSVs disponíveis (`_check_datasets`, linhas 103-131)
     5. `constants` — PAV constants com valores esperados (`_check_constants`, linhas 134-155)
     6. `console` — `is_captured()`, encoding, TTY (`_check_console`, linhas 158-166)
     7. `files_sanity` — UTF-8 (sem BOM), LF (sem CRLF) (`_check_files_sanity`, linhas 169-188)
   - `all_ok = all(c.get("ok", True) for c in checks.values())` (linha 208)
3. **Se `--json`:** `typer.echo(format_as_json(results))` (linha 211).
4. **Senão:** renderiza Panel custom:
   - Border `green` se `all_ok`, `red` senão
   - Title `DOCTOR - OK` ou `DOCTOR - ISSUES`
   - Table.grid com 7 rows: `[OK] python`, `[OK] packages`, etc.
   - Cada check tem summary (e.g. `v3.11.5`, `typer=0.9.0, rich=13.0, pydantic=2.0`)
5. Se `!all_ok`: imprime lista de issues (linhas 252-256).
6. User lê, age conforme necessário.

### Wireflow ASCII (FLOW-010)

```text
       ╭───────────────╮
       │ ◯  user digita│
       │  "operational │
       │   doctor"     │
       ╰───────┬───────╯
               │
               ▼
       ┌───────────────┐
       │ doctor_cmd()  │
       │ (7 checks)    │
       └───┬───────────┘
           │
           ├─→ check_python
           │   sys.version_info
           │   >= (3, 10)?
           │
           ├─→ check_packages
           │   typer/rich/pydantic
           │   instalados?
           │
           ├─→ check_state_dir
           │   ~/.time-tasker/ existe?
           │   14 JSONs parseáveis?
           │
           ├─→ check_datasets
           │   TIME_TASKER_DATASET?
           │   CSVs golden/synthetic OK?
           │
           ├─→ check_constants
           │   POMODORO_WORK_MIN=50?
           │   LAMBDA_LEARNING=0.093?
           │
           ├─→ check_console
           │   is_captured()?
           │   encoding UTF-8?
           │
           └─→ check_files_sanity
               BOM presente?
               CRLF presente?
               │
               ▼
       ┌───────────────┐
       │ all_ok =      │
       │ all checks.ok │
       └───┬───────────┘
           │
       ◇─────────◇
      / --json?      \──y──→ typer.echo(json)
      \ default no   /
       └─────┬───────┘
             │ n
             ▼
       ┌───────────────┐
       │ SCR-021       │
       │ Panel:        │
       │ ╭─ DOCTOR -   │  ◀── border green
       │ │  OK ──────╮ │      ou red
       │ │           │ │
       │ │ [OK] py   │ │
       │ │ [OK] pkgs │ │
       │ │ [OK] st   │ │
       │ │ [OK] data │ │
       │ │ [OK] cst  │ │
       │ │ [OK] cnsl │ │
       │ │ [OK] files│ │
       │ ╰───────────╯ │
       └─────┬─────────┘
             │
       ◇─────────◇
      / all_ok?        \──n──→ SCR-022
      \                /         (issues list)
       └─────┬─────────┘
             │ y
             ▼
       ┌───────────────┐
       │ ◯  doctor     │
       │  concluído    │
       │  (sem erros)  │
       └───────────────┘

  Exceções (linhas tracejadas):
  - - - - - - - - - - - - - - - - - - -
  : (E1) algum check lança    : → log_error
  :     exception              :   + check
  :                             :   marca !ok
  : (E2) timeout em            : → check falha
  :     _check_files_sanity    :   (raro: 14
  :                             :    arquivos
  :                             :    pequenos)
  : (E3) state dir sem         : → check_state_dir
  :     permissão de leitura   :   marca !ok
  :                             :   "not readable"
  - - - - - - - - - - - - - - - - - - -
```

---

## Fluxos alternativos

### A1 — User roda via home menu opção 10 (gap)

`operational home` → `10` (Sistema) → `_system_info` (`cli/home.py:434-466`).

**Incoerência conhecida:** opção 10 do menu NÃO é doctor. É system info estática (versão, constants, tipos, categorias, glossário de flags). UX-009 sugere renomear ou reordenar.

Workaround: rodar `operational doctor` direto.

### A2 — JSON output (CI / log scraping)

```bash
operational doctor --json
```

Retorna payload completo:

```json
{
  "timestamp": "2026-06-08T15:30:00",
  "checks": {
    "python": {"ok": true, "version": "3.11.5", "version_info": "3.11.5", "executable": "/usr/bin/python3"},
    "packages": {"ok": true, "packages": {"typer": "0.9.0", "rich": "13.0.0", "pydantic": "2.0.0"}},
    "state_dir": {"ok": true, "path": "/home/user/.time-tasker", "exists": true, "writable": true, "files": {...}},
    "datasets": {"ok": true, "active": "production", "available": {...}},
    "constants": {"ok": true, "constants": {...}, "expected": {...}},
    "console": {"ok": true, "is_captured": false, "stdout_is_tty": true, "encoding": "utf-8"},
    "files_sanity": {"ok": true, "files_checked": 14, "issues": []}
  },
  "overall_ok": true
}
```

Útil para:
- **CI gate:** `if ! operational doctor --json | jq .overall_ok; then exit 1; fi`
- **Bug report:** user cola JSON completo em issue do GitHub.
- **Monitoring script:** `watch -n 60 'operational doctor --json'`.

### A3 — Doctor após clear (sanity check)

```bash
operational demo clear && operational doctor
```

Espera-se: `state_dir` ainda `ok` (dir existe, vazio, writable). `files_sanity` com `files_checked: 0` (sem JSONs para checar).

### A4 — Doctor após edição manual de JSON

Cenário: user abriu `~/.time-tasker/sleep_records.json` no Notepad++ (Windows) e salvou com CRLF.

```bash
operational doctor
# files_sanity: [FAIL]
#   journals.json: has CRLF line endings (should be LF)
#   sleep_records.json: has CRLF line endings (should be LF)
```

User vê o problema, converte para LF (`dos2unix` no Linux, ou "Edit > EOL Conversion > Unix" no Notepad++).

### A5 — Doctor com state dir corrompido

Cenário: `~/.time-tasker/pomodoros.json` tem `id` duplicado após edição manual.

```bash
operational doctor
# state_dir: [OK]  (parseable=True para todos)
#   ^-- doctor NÃO detecta duplicatas; só checa parse JSON
```

**Limitação:** `doctor` é shallow check. Para detectar duplicatas, rodar `report daily` (vai levantar `Pydantic ValidationError`).

### A6 — Loop de monitoramento

```bash
while true; do
  operational doctor --json | jq '.overall_ok'
  sleep 60
done
```

Risco: `jq` precisa estar instalado. Alternativa: `operational doctor | grep -q "OVERALL OK"`.

---

## Exceções e erros

### E1 — Algum check lança exception inesperada

- **Causa:** bug em um dos 7 checks.
- **Onde:** `doctor_cmd.doctor_cmd` (linhas 196-207) — exceptions não são capturadas individualmente.
- **Tratamento:** exception sobe, `_run_cmd` (se via home) captura via `error_panel`. Se comando direto, Typer mostra traceback.
- **Recuperação:** reportar bug com `doctor --json` output.

### E2 — State dir com 1000+ arquivos

- **Causa:** bug que criou JSONs extras.
- **Onde:** `_check_state_dir` itera 14 arquivos fixos (linha 63-69), não 1000. OK.
- **Onde:** `_check_files_sanity` itera `state_dir.glob("*.json")` (linha 175). Pode ser lento.
- **Tratamento:** espera ≥ 1s. Sem timeout explícito.
- **Diagnóstico:** não-detectado. UX-009.

### E3 — Encoding do terminal errado

- **Causa:** Windows cmd.exe com `chcp 850` (Latin-1).
- **Onde:** `_check_console.encoding` (linha 164) detecta `sys.stdout.encoding`.
- **Tratamento:** check passa (`ok=True`), mas renderização quebra.
- **Workaround:** `chcp 65001` (UTF-8).

### E4 — Constantes PAV com valores alterados

- **Causa:** user editou `constants.py` mudando `POMODORO_WORK_MIN=60`.
- **Onde:** `_check_constants` compara com `expected` (linha 136-143).
- **Tratamento:** check `!ok`, mostra "constants mismatch".
- **Mensagem:** "constants: 5 loaded" (sum de expected, não de mismatches) — confuso. UX-010.

### E5 — Permissão negada em state dir

- **Causa:** `chmod 000 ~/.time-tasker/`.
- **Onde:** `_check_state_dir.writable` (linha 71) usa `os.access(state_dir, os.W_OK)`.
- **Tratamento:** `writable=False`, check `!ok`.
- **Mensagem:** "state_dir: ok /home/user/.time-tasker (0 files)" — confuso (path aparece como "ok" mas check falhou). UX-010.

### E6 — Datasets CSV com 0 bytes

- **Causa:** `docs/golden.csv` truncado.
- **Onde:** `_check_datasets.csv_status` (linha 116-126) checa `p.exists()` mas não `p.stat().st_size > 0`.
- **Tratamento:** check passa (path existe), mas auto-loader falha depois.
- **Limitação:** `doctor` é shallow. UX-009.

---

## Telas envolvidas (refs)

- `docs/ux/05-telas/SCR-021-doctor-panel.md` (ref futura)
- `docs/ux/05-telas/SCR-022-doctor-issues.md` (ref futura)

> **Nota:** Os SCR-* ainda não existem.

## Componentes críticos

- CMP-019 Doctor Panel — `cli/commands/doctor_cmd.py:213-250` (Panel + Table.grid custom)
- CMP-004 error_panel — `ui/components.py:390-426` (se exception)
- **Não usa Header padrão** — Panel tem title próprio.

## Intenção de usabilidade

**Por que este fluxo é desenhado ASSIM:**

1. **7 checks cobrem 90% dos bugs** — Python version, packages, state dir, datasets, constants, console, files_sanity. Cada check é uma função pura retornando dict com `ok: bool`.
2. **Read-only** — `doctor` não altera state. User pode rodar sem medo.
3. **Panel com `OK`/`ISSUES` no title** — feedback binário no topo. User olha o border color e sabe se está tudo OK.
4. **Tabela compacta** — 7 rows, cada uma com ícone + nome + summary. Cabe em terminal 80 col. UX-010 sugere agrupar bom/ruim visualmente.
5. **Lista de issues no fim (se houver)** — scroll-to-bottom revela o que precisa de atenção.
6. **`--json` espelha o painel** — CI pode consumir estruturadamente.
7. **OBJ-07 do produto** — `docs/ux/00-visao-geral/01-objetivos-produto.md:124-136`. Métrica: < 1min para descobrir categoria do bug.

**Fricções mantidas:**

- **Não há opção "doctor" no home menu** — UX-009. Incoerente: opção 10 é "Sistema" mas não inclui doctor.
- **Mensagens "OK" sem detalhar o que está OK** — UX-010. `state_dir: ok /home/...` é confuso. Sugere "OK: 14/14 files parseable".
- **Não detecta bugs lógicos** — UX-009. Só problemas estruturais (encoding, permission, version). Bug em entity Pydantic não é detectado.
- **Output mistura status bom/ruim sem agrupamento visual** — UX-010. User rola 7 rows misturadas. Sugere seções: "✓ Tudo OK" + "✗ Issues".

## Critérios de sucesso

- **Tempo:** < 1s para 7 checks.
- **Cobertura:** detecta ≥ 90% dos bugs comuns (versão, permissão, encoding, CSV faltando).
- **Clareza:** OK/FAIL óbvio em < 2s de leitura.
- **CI-friendly:** `--json` parseável por `jq`.

## Onde aparece

- **Comando direto** — `operational doctor [--json]`
- **OBJ-07 do produto** — `docs/ux/00-visao-geral/01-objetivos-produto.md:124-136`
- **Não aparece no home menu** — gap conhecido (UX-009)

## Notas de implementação

**File:line refs principais:**

- Doctor controller: `cli/commands/doctor_cmd.py:191-250`
- `doctor_cmd` (entry): `cli/commands/doctor_cmd.py:191-250`
- `_check_python`: `cli/commands/doctor_cmd.py:33-40`
- `_check_packages`: `cli/commands/doctor_cmd.py:43-56`
- `_check_state_dir`: `cli/commands/doctor_cmd.py:59-100`
- `_check_datasets`: `cli/commands/doctor_cmd.py:103-131`
- `_check_constants`: `cli/commands/doctor_cmd.py:134-155`
- `_check_console`: `cli/commands/doctor_cmd.py:158-166`
- `_check_files_sanity`: `cli/commands/doctor_cmd.py:169-188`
- Panel render: `cli/commands/doctor_cmd.py:213-250`

**Como adicionar check 8 (test runner):**

```python
def _check_tests() -> dict[str, Any]:
    """Verify pytest discovers tests."""
    import subprocess
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q"],
            capture_output=True, text=True, timeout=30,
        )
        return {"ok": r.returncode == 0, "tests_collected": "..."}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# Em doctor_cmd (linha 196):
"tests": _check_tests(),
```

**Como adicionar doctor ao home menu (opção 11):**

```python
# Em cli/home.py, adicionar:
MENU_ITEMS.insert(10, ("11", "🩺 Doctor", "Diagnóstico completo do ambiente"))
# Atualizar _route (linha 136):
"11": _menu_doctor,
# Handler:
def _menu_doctor() -> None:
    _submenu("🩺 Doctor", [
        ("1", "Doctor (visual)", ["doctor"]),
        ("2", "Doctor JSON", ["doctor", "--json"]),
    ])
```

**Como mudar layout do Panel (UX-010):**

```python
# Em cli/commands/doctor_cmd.py:218, substituir Table.grid por:
ok_section = Table.grid(padding=(0, 2))
fail_section = Table.grid(padding=(0, 2))
for name, check in results["checks"].items():
    target = ok_section if check.get("ok") else fail_section
    target.add_row(icon, name, summary)
group = Group(
    Panel(ok_section, title="✓ OK", border_style="green"),
    Panel(fail_section, title="✗ Issues", border_style="red"),
)
```

(Requer import `Group` de `rich.console`.)

**Como adicionar opção `--fix` que auto-corrige problemas simples:**

```python
# Em doctor_cmd:
fix: bool = typer.Option(False, "--fix", help="Tentar corrigir issues (BETA)")
if fix:
    if not results["checks"]["files_sanity"]["ok"]:
        # Convert CRLF to LF em todos os JSONs
        for f in state_dir.glob("*.json"):
            content = f.read_bytes()
            f.write_bytes(content.replace(b"\r\n", b"\n"))
```

(Perigoso. Backup automático recomendado.)
