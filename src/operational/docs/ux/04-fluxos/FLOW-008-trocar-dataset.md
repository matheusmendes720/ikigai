# FLOW-008 — Trocar Dataset (synthetic ↔ golden ↔ production)

> **Wireflow ASCII:** ver bloco "Fluxo principal" abaixo. Notação: oval = início/fim, retângulo = tela, losango = decisão, paralelogramo = input, tracejada = exceção.

**Objetivo do usuário:** "Quero testar uma feature nova com `golden.csv` sem perder meus dados reais de `production`. Em 10s eu listo datasets, ativo um, e volto."

**Ponto de entrada:**
- Comando direto: `operational demo dataset` (lista), `operational demo dataset <name>` (ativa via env var)
- Não há entrada pelo home menu (FLOW-008 é "operacional" — não workflow)

**Pré-condições:**
- `docs/synthetic.csv` e/ou `docs/golden.csv` existem no projeto
- Env var `TIME_TASKER_DATASET` é **read-only** no processo atual (trocar exige nova invocação do CLI)

**Telas envolvidas:**
- SCR-019 Dataset List (panel com `Active: production` + lista de datasets)
- SCR-020 Dataset Activation Hint (instrução de env var)

**Componentes críticos:**
- CMP-001 Header (não usado — `demo dataset` é comando direto)
- CMP-017 Plain text output (`typer.echo`) — `cli/commands/demo_cmd.py:217-234`

**Duração típica:** 5s (1 comando, leitura, 1 env var export + nova invocação)

**Taxa de abandono estimada:** 0% (sem prompts intermediários)

---

## Fluxo principal (happy path)

### A — Listar datasets

1. User digita `operational demo dataset` (sem argumento).
2. `demo_cmd.dataset(name=None)` (`cli/commands/demo_cmd.py:182-234`):
   - `current = os.environ.get("TIME_TASKER_DATASET", "production")` (linha 197)
   - `all_datasets = list_datasets()` (de `cli/dataset_selector.py:list_datasets`)
   - Para cada dataset: `[OK]` ou `[MISSING]` (linha 219)
   - Imprime path
3. Output:
   ```text
   Active dataset: production

     [OK]      production   — Dados reais do usuário
                            /home/user/.time-tasker/
     [OK]      synthetic    — 7 dias de mock PAV determinístico
                            /path/to/docs/synthetic.csv
     [OK]      golden       — 7 dias de golden run (referência)
                            /path/to/docs/golden.csv
   ```
4. User lê, decide qual ativar.

### B — Ativar dataset

1. User digita `operational demo dataset synthetic`.
2. `demo_cmd.dataset(name="synthetic")` (linhas 223-234):
   - `ref = resolve_dataset("synthetic")` (de `cli/dataset_selector.py:resolve_dataset`)
   - Imprime:
     ```text
     Dataset: synthetic
       Path: /path/to/docs/synthetic.csv
       To activate: TIME_TASKER_DATASET=synthetic operational home
     ```
3. **NÃO muda o estado do processo atual.** User tem que copiar o comando e rodar.
4. User roda `TIME_TASKER_DATASET=synthetic operational home` (Linux/Mac) ou `$env:TIME_TASKER_DATASET="synthetic"; operational home` (PowerShell).
5. Próxima invocação do CLI lê `TIME_TASKER_DATASET` e auto-carrega o CSV.

### Wireflow ASCII (FLOW-008)

```text
       ╭───────────────╮
       │ ◯  user digita│
       │  "operational │
       │   demo        │
       │   dataset"    │
       ╰───────┬───────╯
               │
               ▼
       ┌───────────────┐
       │ SCR-019       │
       │ Dataset List  │
       │               │
       │ Active: prod  │  ◀── de env var ou
       │               │      default "production"
       │ [OK]  prod    │
       │  ~/.time-tk/  │
       │ [OK]  synth   │
       │  docs/...csv  │
       │ [OK]  golden  │
       │  docs/...csv  │
       └─────┬─────────┘
             │
             ▼
       ╭───────────────╮
       │ ◯  user       │
       │  "operational │
       │   demo        │
       │   dataset     │
       │   synthetic"  │
       ╰───────┬───────╯
               │
               ▼
       ┌───────────────┐
       │ SCR-020       │
       │ Hint:         │
       │               │
       │ Dataset: synth│
       │ Path: ...csv  │
       │               │
       │ To activate:  │
       │ TIME_TASKER_  │
       │  DATASET=     │
       │  synthetic    │
       │  operational  │
       │   home        │  ◀── NÃO muda o
       └─────┬─────────┘      processo atual
             │                (read-only)
             ▼
       ╭───────────────╮
       │ ◯  user copia │
       │  e roda o     │
       │  comando      │
       │  (nova        │
       │   invocação)  │
       ╰───────┬───────╯
               │
               ▼
       ┌───────────────┐
       │ (próximo      │
       │  processo)    │
       │ auto-loader   │  ◀── em cli/state.py
       │ lê CSV no     │      (não lido)
       │ startup       │
       └─────┬─────────┘
             │
             ▼
       ┌───────────────┐
       │ ◯  state      │
       │  populado     │
       │  com 345      │
       │  entities     │
       └───────────────┘

  Exceções (linhas tracejadas):
  - - - - - - - - - - - - - - - - - - -
  : (E1) CSV não encontrado   : → list_datasets
  :                            :   marca
  :                            :   [MISSING]
  : (E2) nome inválido        : → resolve_dataset
  :     (ex: "foo")            :   lança ValueError
  :                            :   → error_panel
  : (E3) --json               : → payload flat
  - - - - - - - - - - - - - - - - - - -
```

---

## Fluxos alternativos

### A1 — User pula o comando `dataset` e seta env var direto

```bash
# Linux/Mac
TIME_TASKER_DATASET=synthetic operational home

# PowerShell
$env:TIME_TASKER_DATASET = "synthetic"
operational home

# cmd.exe
set TIME_TASKER_DATASET=synthetic
operational home
```

Equivalente a rodar `operational demo dataset synthetic` e depois invocar. Pula a etapa de "ver path".

### A2 — Ativação permanente (adicionar ao shell rc)

Para tornar a troca persistente (sobrevive a reinício do shell):

```bash
# ~/.bashrc ou ~/.zshrc
export TIME_TASKER_DATASET=synthetic
```

Ou usar `direnv` (`.envrc` no projeto):

```bash
# .envrc
export TIME_TASKER_DATASET=synthetic
```

### A3 — JSON output

```bash
operational demo dataset --json
# ou
operational demo dataset synthetic --json
```

Retorna payload estruturado. Útil para scripts que precisam saber datasets disponíveis.

### A4 — Atalho via alias shell

```bash
# ~/.bashrc
alias tt-synth="TIME_TASKER_DATASET=synthetic operational"
alias tt-gold="TIME_TASKER_DATASET=golden operational"
alias tt-prod="unset TIME_TASKER_DATASET && operational"
```

Acelera o switch. Trade-off: aliases não-portáveis (Linux vs Windows).

### A5 — Voltar para production (após testar synthetic)

```bash
operational demo dataset production
# Mostra hint: TIME_TASKER_DATASET=production operational home
# User roda nova invocação com env var unset ou =production
```

Ou, mais simples:

```bash
unset TIME_TASKER_DATASET && operational home  # Linux/Mac
$env:TIME_TASKER_DATASET = $null; operational home  # PowerShell
```

### A6 — Verificar se env var está setada

```bash
echo $TIME_TASKER_DATASET  # Linux/Mac
echo $env:TIME_TASKER_DATASET  # PowerShell
```

Sem ferramenta interna para isso (UX-009).

---

## Exceções e erros

### E1 — CSV não encontrado

- **Causa:** `docs/synthetic.csv` foi movido ou deletado.
- **Onde:** `cli/dataset_selector.py:list_datasets` (não lido integralmente) checa `csv_path.exists()`.
- **Tratamento:** marca `[MISSING]` no output (linha 219: `exists = "OK" if ... else "MISSING"`).
- **Mensagem ao user:** visual: `[MISSING] synthetic — /path/docs/synthetic.csv`.

### E2 — Nome de dataset inválido

- **Causa:** `operational demo dataset foo` (não existe).
- **Onde:** `cli/dataset_selector.py:resolve_dataset` (não lido).
- **Tratamento:** provavelmente `ValueError` ou `KeyError`, capturado por `_run_cmd` (não usado aqui — comando direto).
- **Mensagem ao user:** Typer converte em `BadParameter` ou erro genérico. UX-009.

### E3 — Permissão de leitura do CSV

- **Causa:** `docs/golden.csv` com `chmod 000` (raro).
- **Onde:** `cli/dataset_selector.py` ou auto-loader em `cli/state.py`.
- **Tratamento:** `PermissionError`, capturado por Typer ou `error_panel` (se via home menu).
- **Diagnóstico:** `operational doctor` reporta.

### E4 — CSV malformado

- **Causa:** `golden.csv` editado manualmente, linha corrompida.
- **Onde:** `cli/csv_loader.py:import_from_csv_as_entities` (não lido integralmente).
- **Tratamento:** pula linha, warning no log. Auto-load parcial.
- **Workaround:** `operational demo clear && operational demo seed` regenera.

### E5 — Env var setada mas processo já está rodando

- **Causa:** user seta `TIME_TASKER_DATASET=synthetic` no meio de uma sessão `operational home`.
- **Comportamento:** a sessão atual **não recarrega**. O `os.environ.get()` foi lido no startup. UX-016 (auto-load só roda com state vazio).

---

## Telas envolvidas (refs)

- `docs/ux/05-telas/SCR-019-dataset-list.md` (ref futura)
- `docs/ux/05-telas/SCR-020-dataset-hint.md` (ref futura)

> **Nota:** Os SCR-* ainda não existem.

## Componentes críticos

- **Não usa CMP-001 Header** — `demo dataset` é comando direto, sem home menu.
- CMP-017 Plain text output — `typer.echo` (`demo_cmd.py:217-234`)
- **Auto-loader** — `cli/state.py` (não lido integralmente) — lê CSV no startup se env var setada

## Intenção de usabilidade

**Por que este fluxo é desenhado ASSIM:**

1. **Listar + ativar são 2 comandos, não 1 com prompt** — fluxo "command-style", não "interactive". Decisão: trocar dataset é raro, não justifica submenu interativo.
2. **Ativação via env var, não estado mutável** — `TIME_TASKER_DATASET` é read-only no processo. Trade-off: user tem que rodar nova invocação. Benefício: cada invocação é determinística (mesmo env var → mesmo estado). Scripts de CI beneficiam-se.
3. **`production` é default implícito** — `os.environ.get(..., "production")` (`demo_cmd.py:197`). User que nunca setou env var está em production.
4. **Hint impresso em vez de "ativado agora"** — `demo_cmd.py:232` imprime o comando para o user copiar. UX-009 sugere botão "run now" (mas Typer não tem).
5. **Datasets vivem em CSV** — `golden.csv` e `synthetic.csv` em `docs/`. Versionáveis em git. Production é `~/.time-tasker/*.json` (não versionado).
6. **OBJ-06 do produto** — `docs/ux/00-visao-geral/01-objetivos-produto.md:106-122`. Métrica: 1 comando lista, 1 ativa, 1 volta. Nenhum dado perdido.

**Fricções mantidas:**

- **Não há "ativar agora" (read-only env var)** — UX-005. Workaround: alias shell (A4).
- **Sem UI para "qual dataset está ativo agora?"** — user tem que rodar `operational demo dataset` para listar. UX-009 sugere adicionar no header do home menu.
- **Auto-load só roda com state vazio** — UX-016. Se user já tem state populado, mudar env var não recarrega.

## Critérios de sucesso

- **Tempo:** < 10s para listar + ativar + nova invocação.
- **Clareza:** 100% dos users entendem "rode o comando abaixo em nova janela".
- **Zero perda de dados:** production state é preservado durante switch.
- **Idempotência:** rodar `demo dataset synthetic` 10× seguidas = mesmo resultado.

## Onde aparece

- **Comando direto** — `operational demo dataset [name] [--json]`
- **Não aparece no home menu** — é "operacional", não workflow.
- **OBJ-06 do produto** — `docs/ux/00-visao-geral/01-objetivos-produto.md:106-122`

## Notas de implementação

**File:line refs principais:**

- `demo_cmd.dataset`: `cli/commands/demo_cmd.py:182-234`
- `list_datasets` (helper): `cli/dataset_selector.py` (não lido integralmente)
- `resolve_dataset` (helper): `cli/dataset_selector.py` (não lido integralmente)
- Auto-loader (lê env var): `cli/state.py` (não lido integralmente)
- CSV files: `docs/synthetic.csv`, `docs/golden.csv`
- Production state: `~/.time-tasker/*.json`

**Como adicionar novo dataset (ex: "stress-test"):**

1. Criar `docs/stress-test.csv` (mesmo formato que `synthetic.csv`).
2. Adicionar entrada em `cli/dataset_selector.py:list_datasets` (provavelmente uma lista literal).
3. Documentar em `docs/ux/01-inventario/01-telas-inventario.md` (ref futura).

**Como mudar a env var name:**

`TIME_TASKER_DATASET` é hard-coded em `demo_cmd.py:197, 225, 232` e em `cli/state.py` (auto-loader). Para mudar, fazer replace global. Cuidado com retrocompatibilidade.

**Como adicionar UI de switch no home menu:**

```python
# Em cli/home.py, adicionar option 11:
("11", "🔄 Trocar dataset", "Lista/ativa via env var TIME_TASKER_DATASET"),
# Handler:
def _menu_dataset() -> None:
    _submenu("🔄 Dataset", [
        ("1", "Listar datasets", ["demo", "dataset"]),
        ("2", "Ativar synthetic", ["demo", "dataset", "synthetic"]),
        ("3", "Ativar golden", ["demo", "dataset", "golden"]),
        ("4", "Voltar para production", ["demo", "dataset", "production"]),
    ])
```

(Requer entender que "ativar" só imprime hint — user tem que copiar e rodar.)

**Consideração de segurança:**

`docs/synthetic.csv` e `docs/golden.csv` são versionados em git. Production (`~/.time-tasker/`) **NÃO** é. Não commitar acidentalmente.
