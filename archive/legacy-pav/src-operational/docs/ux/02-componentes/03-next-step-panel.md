# CMP-003 — next_step_panel

**Arquivo fonte:** `src/operational/ui/components.py:381-387`
**Função Python:** `next_step_panel(text, *, severity="ok", icon="→") -> Panel`
**Propósito:** Painel de **recomendação curta** ("Aplicar este plano: ...") que aparece no fim de relatórios. É a "voz do sistema" dizendo o que fazer a seguir.
**Quando usar:** No final do Daily Report, Weekly Report, e State Dashboard para resumir a ação recomendada. Sempre depois de todos os dados, como um "tl;dr".
**Quando NÃO usar:** No meio do relatório (interrompe a leitura). Use `severity_text` inline se precisar destacar uma ação no meio do conteúdo.

## Assinatura

```python
def next_step_panel(
    text: str,
    *,
    severity: str = "ok",
    icon: str = "→",
) -> Panel
```

| Param | Tipo | Default | Notas |
|-------|------|---------|-------|
| `text` | `str` | — | A recomendação em 1-2 frases, ex: `"Dia dentro do padrão ouro. Manter ritmo."` |
| `severity` | `str` | `"ok"` | Define a cor da borda; `crit` para alertas, `warn` para atenção, `ok` para confirmação, `info` para neutro |
| `icon` | `str` | `"→"` | Emoji/glyphe líder; `!` para alerta, `↑` para aumentar, `→` para indicar direção, `✓` para ok |

## Saída ASCII

**Default (severity=ok, icon=→):**

```text
╭────────────────────────────────────────────────────╮
│  →  Dia dentro do padrão ouro. Manter ritmo,       │
│     monitorar fadiga.                              │
╰────────────────────────────────────────────────────╯
```

**Crit (alerta, icon=!):**

```text
╭────────────────────────────────────────────────────╮
│  !  Aplicar plano de recuperação antes de          │
│     continuar. Sono < 6h ou Q3 detectado.          │
╰────────────────────────────────────────────────────╯
```

**Warn (atenção, icon=↑):**

```text
╭────────────────────────────────────────────────────╮
│  ↑  Produtividade média 45% (abaixo de 50%).       │
│     Aumentar volume de trabalho.                   │
╰────────────────────────────────────────────────────╯
```

## Severidades disponíveis

| Severity | Cor | Quando usar |
|----------|-----|-------------|
| `ok` | bright_green | Tudo ok, manter |
| `warn` | yellow | Atenção, ajustar |
| `crit` | bold red | Crítico, parar/agir |
| `info` | deep_sky_blue1 | Informativo, neutro |

A cor **resolve** via `SEVERITY_COLOR.get(severity, "ok")`.

## Estados internos

- **Vazio:** se não há recomendação (gap), o caller simplesmente
  não inclui o painel no Group.
- **1 painel:** o caso normal — 1 recomendação por relatório.
- **N painéis:** o caller pode empilhar 2+ (ex: 1 `crit` para
  Q3 + 1 `ok` para "manter hábitos"). Raro.

## Acessibilidade

- **Funciona sem cores?** Sim, mas o ícone (`!`, `→`, `↑`, `✓`)
  é o que carrega a semântica. Sempre **inclua o ícone**.
- **Funciona com TTY 80-col?** Sim; o `Panel` se adapta.
- **Leve para screen reader?** Não. O `Text` interno é uma
  string única, sem estrutura semântica.

## Onde é usado

1. `ui/daily_report.py:260-278` — final do Daily Report, com
   `crit` se Q3 ou sono < 6h, `ok` se padrão ouro, `info`
   caso contrário
2. `cli/commands/report_cmd.py:296-313` — final do Weekly
   Report, com `crit` se Q3 ≥ 1, `warn` se avg_x < 50, `ok`
   caso contrário
3. `cli/commands/state_cmd.py:267-277` — final do State
   Dashboard, com `warn` se journal não feito ou 0 pomodoros,
   `ok` caso contrário
4. `cli/renderers.py:468-478` — variante `next_step` (mesmo
   visual, parâmetro `color=` em vez de `severity=`)

## Riscos de usabilidade

- **Cores podem ser confusas para daltônicos:** `crit` (bold
  red) e `warn` (yellow) são distinguíveis pela maioria, mas
  o ícone `!` vs `↑` é o diferenciador universal. **Regra:**
  sempre combine cor + ícone.
- **Texto pode ser mal interpretado em outro contexto:** o
  `text` é uma string livre, e o caller controla o tom.
  **Regra:** comece com verbo no infinitivo ou imperativo
  ("Aplicar", "Aumentar", "Manter", "Revisar") e seja
  específico.
- **Layout pode quebrar em terminal narrow:** o `Panel` se
  adapta, mas se o `text` for muito longo (>200 chars), o
  wrap fica estranho. **Regra:** máximo 2 frases, < 200
  chars.

## Padrões de copy

| Severidade | Template | Exemplo |
|------------|----------|---------|
| `ok` | "[Resumo positivo]. [Ação de manutenção]." | "Dia dentro do padrão ouro. Manter ritmo, monitorar fadiga." |
| `warn` | "[Problema]. [Ação corretiva]." | "Produtividade média 45% (abaixo de 50%). Aumentar volume de trabalho." |
| `crit` | "[Alerta]. [Ação urgente]." | "Aplicar plano de recuperação antes de continuar. Sono < 6h ou Q3 detectado." |
| `info` | "[Contexto]. [Sugestão neutra]." | "Ajustar próximo dia: revisar desvios e aplicar ajustes finos." |

---

## Onde ler mais

- **Componente irmão `next_step`** (variante em `renderers.py`) →
  [`12-next-step.md`](12-next-step.md)
- **Decisões de quando usar `crit` vs `warn` no Daily Report** →
  [`../00-visao-geral/04-glossario-dominio.md`](../00-visao-geral/04-glossario-dominio.md#q1--q2--q3--q4-quadrantes)
- **Catálogo geral de componentes** →
  [`../../tui/02-COMPONENT-CATALOG.md`](../../tui/02-COMPONENT-CATALOG.md)
