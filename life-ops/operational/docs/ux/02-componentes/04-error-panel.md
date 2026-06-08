# CMP-004 — error_panel

**Arquivo fonte:** `src/operational/ui/components.py:390-426`
**Função Python:** `error_panel(mensagem, *, contexto=None, severity="crit", hint=None) -> Panel`
**Propósito:** Erro **padronizado** com mensagem, contexto opcional e dica de debugging. Substitui o traceback bruto por uma superfície limpa. O traceback completo é logado em arquivo (`log_error` em `ui/logging_setup.py`).
**Quando usar:** Em qualquer controller quando uma operação falha. O `error_panel` é o **contrato visual de erro** do CLI.
**Quando NÃO usar:** Para validação de input do Typer (que aborta antes do controller). Para avisos não-críticos (use `severity="warn"` e mensagem positiva).

## Assinatura

```python
def error_panel(
    mensagem: str,
    *,
    contexto: str | None = None,
    severity: str = "crit",
    hint: str | None = None,
) -> Panel
```

| Param | Tipo | Default | Notas |
|-------|------|---------|-------|
| `mensagem` | `str` | — | A mensagem de erro em si, em texto plano |
| `contexto` | `str \| None` | `None` | Estado ao redor, ex: `"routine='Morning' period=MANHA"` |
| `severity` | `str` | `"crit"` | `crit` (vermelho), `warn` (amarelo), `ok` (verde/info) |
| `hint` | `str \| None` | `None` | Dica de debugging, ex: `"Verifique o enum HabitCategory."` |

## Saída ASCII

**Default (severity=crit):**

```text
╭────  SISTEMA FALHOU  ────────────────────────────────────────────╮
│  ❌ Erro de Execução                                              │
│                                                                  │
│  ValidationError: 1 validation error for SleepRecord             │
│  quality_score                                                    │
│    Input should be less than or equal to 10                      │
│    [type=less_than_equal, input_value=15, input_type=int]        │
│                                                                  │
│  [Contexto]  date=2026-06-08                                     │
│  [💡 Dica]  Use --quality entre 1 e 10.                          │
╰──────────────────────────────────────────────────────────────────╯
```

**Warn (severity=warn, ícone ⚠️):**

```text
╭────  SISTEMA FALHOU  ────────────────────────────────────────────╮
│  ⚠️ Aviso                                                        │
│                                                                  │
│  JSON file is empty: routines.json                               │
│                                                                  │
│  [💡 Dica]  O arquivo será recriado no próximo upsert.            │
╰──────────────────────────────────────────────────────────────────╯
```

## Severidades disponíveis

| Severity | Ícone | Título | Cor da borda |
|----------|-------|--------|--------------|
| `crit` | ❌ | "Erro de Execução" | red |
| `warn` | ⚠️ | "Aviso" | yellow |
| `ok` | ℹ️ | "Informação" | green |

A severity "ok" é estranha para um error_panel, mas é
intencional: permite usar o mesmo formato para mensagens
**informativas** (ex: "Tudo certo, operação concluída com
ressalvas").

## Estados internos

- **Erro simples (sem contexto):** caller passa `mensagem` e
  `severity`; nada mais.
- **Erro com contexto:** caller adiciona `contexto="repos=14,
  date=2026-06-08"` para debug.
- **Erro com dica:** caller adiciona `hint="Use --quality entre
  1 e 10."` para ajudar o usuário a corrigir.
- **Erro de validação Pydantic:** caller pode passar a mensagem
  completa do Pydantic em `mensagem` (multi-linha é ok).

## Acessibilidade

- **Funciona sem cores?** Sim, mas o ícone (`❌`, `⚠️`, `ℹ️`)
  é o que carrega a semântica. **Regra:** sempre inclua o
  ícone.
- **Funciona com TTY 80-col?** Sim; o `Panel` se adapta
  (largura default `min(100, 120) = 100`).
- **Leve para screen reader?** Não, mas o `Text` interno é
  uma string contínua que pode ser lida em ordem (mensagem →
  contexto → dica).

## Onde é usado

1. `cli/home.py:69-75` — fallback de `_run_cmd` quando há
   `Exception` não tratada
2. `cli/commands/metric_cmd.py:20` (import) + espalhado —
   validações Pydantic
3. `cli/commands/reflect_cmd.py` — validações de OKR
4. `ui/daily_report.py` (potencial) — para `get_day_snapshot`
   quando falta dados

**Nota:** o `error_panel` é a **única superfície** que o usuário
vê em caso de erro. O traceback completo vai para
`~/.time-tasker/logs/operational.log` (via
`log_error` em `ui/logging_setup.py:31-58`).

## Riscos de usabilidade

- **Cores podem ser confusas para daltônicos:** o vermelho
  (`crit`) é universalmente "erro", mas a diferença entre
  ❌ e ⚠️ pode ser sutil. **Mitigação:** incluir o **título
  textual** ("Erro de Execução", "Aviso", "Informação")
  além do ícone.
- **Texto pode ser mal interpretado em outro contexto:** o
  caller controla o tom. **Regra:** a `mensagem` deve ser
  **específica** (não "Erro genérico") e **acionável**
  (não "Algo deu errado"). Se for `crit`, o usuário precisa
  saber o que fazer a seguir.
- **Layout pode quebrar em terminal narrow:** o `Panel` tem
  `width=min(100, 120)`. Em 80 col, ele excede e wrap fica
  feio. **Mitigação atual:** width flexível; testar com
  terminal narrow.

## Padrões de copy

| Tipo | `mensagem` | `contexto` (opcional) | `hint` (opcional) |
|------|-----------|----------------------|-------------------|
| Pydantic ValidationError | Texto completo do erro | `date=..., repos=...` | "Verifique o range de X." |
| FileNotFoundError | Mensagem do erro | `path=...` | "Crie o diretório ou ajuste env var." |
| PermissionError | Mensagem do erro | `file=...` | "chmod 700 ~/.time-tasker" |
| FaltaDadosError | Mensagem do erro | `date=...` | "Use `demo seed` para popular dados." |
| JSONDecodeError | Mensagem do erro | `file=...` | "Restaure de backup ou delete o arquivo." |

---

## Onde ler mais

- **Estado "Erro" da matriz de telas** →
  [`../01-inventario/02-matriz-estados.md`](../01-inventario/02-matriz-estados.md)
- **Componente irmão `severity_text`** (cor inline, não painel) →
  [`10-severity-text.md`](10-severity-text.md)
- **Catálogo geral de componentes** →
  [`../../tui/02-COMPONENT-CATALOG.md`](../../tui/02-COMPONENT-CATALOG.md)
