# FLOW-009 — Limpar e Resetar Estado (clear, com confirmação)

> **Wireflow ASCII:** ver bloco "Fluxo principal" abaixo. Notação: oval = início/fim, retângulo = tela, losango = decisão, paralelogramo = input, tracejada = exceção.

**Objetivo do usuário:** "Quero começar do zero. Apaguei todos os 14 arquivos JSON do state dir para testar uma feature nova ou corrigir dados corrompidos."

**Ponto de entrada:**
- `operational home` → `9` (Demo & Testes) → `5` (Limpar todos dados)
- Comando direto: `operational demo clear` (UX-014: sem confirmação!)

**Pré-condições:**
- Nenhuma. Comando destrutivo — **não exige confirmação** (gap conhecido — UX-014).
- State dir `~/.time-tasker/` deve existir OU `demo clear` cria vazio.

**Telas envolvidas:**
- SCR-001 Home Menu
- SCR-006e Demo Submenu
- (Sem tela de confirmação — gap)

**Componentes críticos:**
- CMP-001 Header
- CMP-018 Plain text confirmation `Limpo!` (após clear)

**Duração típica:** 2s (1 comando destrutivo)

**Taxa de abandono estimada:** 0% (sem confirmação; user que chegou aqui quer apagar)

---

## Fluxo principal (happy path)

1. User digita `operational home`, digita `9` (Demo & Testes), Enter.
2. `_route("9")` despacha para `_menu_demo` (`cli/home.py:357-364`).
3. `_submenu` mostra 5 opções. User digita `5` (Limpar todos dados).
4. `_run_cli_command(["demo", "clear"])` — `home.py:363`.
5. `demo_cmd.clear` (`cli/commands/demo_cmd.py:42-51`):
   - `msg = clear_demo_data()` (de `cli/seed.py:clear_demo_data`, não lido integralmente)
   - Imprime `msg` (ou JSON se `--json`).
6. **Sem confirmação "Tem certeza?"** — UX-014. Comando executa imediatamente.
7. **Sem banner `Press Enter to continue`** — fluxo rápido (não há, mas o submenu loop retorna após `_run_cli_command`).
8. **PROMPT EXTRA APÓS SUBMENU:** `_menu_demo` pergunta `Rodar suite de testes agora? (y/n)` (`home.py:365`). Default `n`. User pressiona Enter.
9. Volta ao menu principal.

### Wireflow ASCII (FLOW-009)

```text
       ╭───────────────╮
       │ ◯  user digita│
       │  "9" no home  │
       ╰───────┬───────╯
               │
               ▼
       ┌───────────────┐
       │ SCR-006e      │
       │ Submenu       │
       │ Demo (5+1)    │◀════╮
       └───┬───────────┘    │
           │ digita "5"     │
           │ (Limpar)        │
           ▼                │
       ╔═══════════════╗    │
       ║ demo clear    ║    │  ◀── SEM
       ║ (DESTRUTIVO)  ║    │      confirmação!
       ╚═══════╤═══════╝    │      (UX-014)
               │            │
               ▼            │
       ┌───────────────┐    │
       │ clear_demo_   │    │
       │ data()        │    │  ◀── apaga 14
               │            │      JSON files
               ▼            │
       ┌───────────────┐    │
       │ CMP-018       │    │
       │ "Limpo!"      │    │
       │ ou "Removed N │    │
       │  entities"    │    │
       └─────┬─────────┘    │
             │              │
             ▼              │
       ┌───────────────┐    │
       │ SUBMENU       │    │
       │ pergunta:     │    │
       │ "Rodar suite  │    │
       │  de testes?"  │    │  ◀── prompt extra
       │ (y/n, def n)  │    │      após o submenu
       └─────┬─────────┘    │
             │ n            │
             ▼              │
       ┌───────────────┐    │
       │ ◯  volta      │    │
       │  ao menu      │────┘
       └───────────────┘

  Exceções (linhas tracejadas):
  - - - - - - - - - - - - - - - - - - -
  : (E1) state dir não existe : → clear_demo_data
  :                            :   cria dir vazio
  :                            :   (silent)
  : (E2) permission denied    : → error_panel
  :     em algum JSON         :   + log_error
  : (E3) user queria "demo    : → confusão
  :     seed" e rodou "clear" :   (UX-014)
  - - - - - - - - - - - - - - - - - - -
```

---

## Fluxos alternativos

### A1 — User pula o home menu (comando direto)

```bash
operational demo clear
# ou
operational demo clear --json
```

Equivalente. Sem confirmação. UX-014.

### A2 — "Seed" + "Clear"组合 (workflow de dev)

```bash
operational demo clear && operational demo seed
# ou, no submenu opção 2:
operational demo week  # seed + report weekly
```

Cenário típico: testar relatório em dados sintéticos conhecidos.

### A3 — `seed` em vez de `clear`

Se o user quer **adicionar** 7 dias de mock (não apagar), usa `demo seed` (opção 1 do submenu, `home.py:359`):

```bash
operational demo seed
# Popula 7 dias PAV (Perfeito, Desvio, Hardcore, Recuperação...)
```

Cuidado: `seed` faz **append** se state já tem dados (UX-015). Workaround: `clear && seed`.

### A4 — Backup antes de clear (workaround)

```bash
# Backup
cp -r ~/.time-tasker/ ~/.time-tasker.backup.$(date +%Y%m%d)
# Clear
operational demo clear
# Restore (se necessário)
rm -rf ~/.time-tasker
mv ~/.time-tasker.backup.YYYYMMDD ~/.time-tasker
```

UX-009 sugere adicionar `--backup` flag em `demo clear`.

### A5 — Limpar 1 arquivo só (granular)

Não há comando granular (`demo clear --only sleep` não existe). `clear` apaga **tudo**. Para granular:

```bash
# 1. Listar
operational state show
# 2. Identificar arquivo problemático (ex: sleep_records.json)
# 3. Editar manualmente (PERIGOSO)
# 4. Re-rodar state show para confirmar
```

UX-009 sugere `state reset --entity sleep_records`.

### A6 — JSON output

```bash
operational demo clear --json
# {"status": "cleared"}
```

Útil para CI: rodar antes de testes para garantir state limpo.

---

## Exceções e erros

### E1 — State dir não existe

- **Causa:** primeira execução do CLI nunca rodou.
- **Onde:** `cli/seed.py:clear_demo_data` (não lido integralmente).
- **Tratamento:** cria dir vazio, sem erro.
- **Mensagem ao user:** nenhuma (silent).

### E2 — Permission denied em algum JSON

- **Causa:** `chmod 000` em `~/.time-tasker/sleep_records.json`.
- **Onde:** `clear_demo_data` tenta deletar arquivo.
- **Tratamento:** `PermissionError`, capturado por `error_panel`.
- **Recuperação:** `chmod 644 ~/.time-tasker/*.json` e re-rodar.

### E3 — Ctrl+C durante clear

- **Causa:** user interrompe mid-loop.
- **Onde:** `clear_demo_data` itera 14 arquivos.
- **Tratamento:** `KeyboardInterrupt` sai do clear. **State parcial**: alguns arquivos apagados, outros não.
- **Diagnóstico:** `operational doctor` reporta quais faltam.
- **Recuperação:** rodar `operational demo clear` de novo (idempotente).

### E4 — JSON em uso por outro processo

- **Causa:** dois terminais com `operacional home` aberto, um roda `clear`.
- **Comportamento:** segundo terminal ainda tem dados em memória. Próximo `repo.list()` pode ter inconsistência.
- **Risco:** UX-006 (sem locking). Workaround: fechar todas as instâncias antes de clear.

### E5 — User roda `clear` por engano (sem backup)

- **Causa:** UX-014 (sem confirmação).
- **Impacto:** dados de produção perdidos.
- **Recuperação:** ver A4 (backup manual pré-clear). Sem undo.

---

## Telas envolvidas (refs)

- `docs/ux/05-telas/SCR-001-home-menu.md` (ref futura)
- `docs/ux/05-telas/SCR-006e-demo-submenu.md` (ref futura)

> **Nota:** Os SCR-* ainda não existem.

## Componentes críticos

- CMP-001 Header — `cli/home.py:84-93`
- CMP-018 Plain text confirmation — `cli/seed.py:clear_demo_data` retorna string (provavelmente `"Limpo!"` ou `"Removed 0 entities"`)
- CMP-004 error_panel — `ui/components.py:390-426`

## Intenção de usabilidade

**Por que este fluxo é desenhado ASSIM:**

1. **Comando destrutivo SEM confirmação** — `home.py:363` (`items[4]` é `["demo", "clear"]`). Trade-off: fricção zero para power users; perigoso para novatos. UX-014.
2. **Submenu "Demo & Testes"** agrupa comandos destrutivos (`seed`, `clear`, `show`) sob opção 9 com ícone 🎬. Sinaliza: "isso é playground".
3. **Prompt extra "Rodar testes?"** após submenu (`home.py:365`) — porque usuário que está testando provavelmente quer rodar pytest logo depois.
4. **`seed` faz append (não replace)** — UX-015. User que quer replace tem que `clear && seed`. Trade-off: permite builds incrementais.
5. **OBJ-07 do produto** — `docs/ux/00-visao-geral/01-objetivos-produto.md:124-136` (doctor). `clear` não é OBJ, mas é prep para doctor.

**Fricções mantidas:**

- **Sem confirmação** — UX-014. User pode perder dados. Workaround: backup manual (A4).
- **Sem granularidade** — UX-009. `clear` apaga 14 repos. Sem "limpar só sleep_records".
- **Sem undo** — UX-006. Ação é irreversível.
- **`seed` polui state dir** — UX-015. 345 entities adicionadas sem aviso. Workaround: rodar em `TIME_TASKER_DATASET=synthetic` (FLOW-008) para isolar.

## Critérios de sucesso

- **Tempo:** < 2s para limpar 14 arquivos.
- **Atomicidade:** se interrompido, próximo `clear` completa (idempotente).
- **Sem perda silenciosa:** user SEMPRE sabe que rodou `clear` (banner ou log).
- **Idempotência:** rodar `clear` 10× seguidas = mesmo estado final (vazio).

## Onde aparece

- **Home menu opção 9 → 5** — `_menu_demo` (`cli/home.py:363`)
- **Comando direto** — `operational demo clear [--json]`
- **Workflow de dev** — combinado com `demo seed` (FLOW-008 A2, este doc A2)

## Notas de implementação

**File:line refs principais:**

- Fluxo principal: `cli/home.py:357-366`
- `_menu_demo`: `cli/home.py:357-364`
- `_submenu` helper: `cli/home.py:297-318`
- Submenu item 5: `cli/home.py:363` (`["demo", "clear"]`)
- Prompt "Rodar testes?": `cli/home.py:365`
- `_run_tests`: `cli/home.py:369-400`
- `demo_cmd.clear`: `cli/commands/demo_cmd.py:42-51`
- `clear_demo_data`: `cli/seed.py` (não lido integralmente)

**Como adicionar confirmação `Tem certeza? (y/n)`:**

```python
# Em cli/commands/demo_cmd.py:clear (linha 42):
from rich.prompt import Confirm
@app.command()
def clear(
    force: bool = typer.Option(False, "--force", "-f", help="Pular confirmação"),
    json: bool = typer.Option(False, "--json"),
) -> None:
    """Remove all demo data."""
    if not force and not Confirm.ask("Apagar todos os 14 JSON files?", default=False):
        typer.echo("Cancelado.")
        return
    msg = clear_demo_data()
    if json:
        typer.echo(format_as_json({"status": "cleared"}))
    else:
        typer.echo(msg)
```

(Adiciona fricção. Scripts de CI usam `--force`. UX-014.)

**Como adicionar backup automático:**

```python
# Em clear_demo_data, antes de deletar:
import shutil
from pathlib import Path
backup_dir = state_dir.parent / f".time-tasker.backup.{datetime.now().isoformat()}"
if state_dir.exists():
    shutil.copytree(state_dir, backup_dir)
```

(Requer import. Cria backup com timestamp.)

**Como adicionar granularidade `--only`:**

```python
# Em demo_cmd.py:clear:
only: str | None = typer.Option(None, "--only", help="Limpar só uma entity (ex: sleep_records)")
if only:
    clear_specific_entity(only)  # helper em cli/seed.py
else:
    clear_demo_data()
```

(Requer `clear_specific_entity` em `cli/seed.py`.)

**Como mudar prompt "Rodar testes?":**

`home.py:365` (`default="n"`). Mudar para `default="y"` se user em dev workflow ativo.

**Consideração sobre pytest:**

`_run_tests` (`home.py:369-400`) executa `pytest -x --tb=short -q` em subprocesso com timeout 180s. Pode demorar. Captura stdout/stderr, imprime exit code. Risco: se pytest trava, user espera 180s. UX-009 sugere `--quick` flag.
