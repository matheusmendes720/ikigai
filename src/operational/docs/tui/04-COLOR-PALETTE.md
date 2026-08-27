# 04 — Color Palette

> Colors in the `operational` dashboard are **semantic**, not decorative. Every colored element answers the question "what does this value *mean* — is it good, bad, watch-out, or just informational?" A green sleep duration means "you slept enough"; a red one means "you are at risk". This is the discipline that lets the user read the dashboard at a glance. The full palette is centralized in two places: **`ui/components.py`** (canonical, used by the core dashboard) and **`cli/renderers.py`** (extended, used by the v3 report renderers). The two share a common vocabulary and the same color names resolve identically in both.

## `COLORS` dict — the 11 named colors

**Defined in:** `ui/components.py:31-44`. The dict has 12 entries; 11 are "primary palette" plus the `transition` accent.

```python
# ui/components.py:31-44
COLORS: dict[str, str] = {
    "primary":    "cyan",
    "ok":         "bright_green",
    "warn":       "yellow",
    "crit":       "bold red",
    "info":       "deep_sky_blue1",
    "muted":      "grey58",
    "sleep":      "dodger_blue2",
    "hardwork":   "green3",
    "ease":       "magenta",
    "energy":     "yellow1",
    "focus":      "deep_sky_blue1",
    "transition": "deep_pink1",
}
```

| Key | Rich name | Semantic role | Example use |
|-----|-----------|---------------|-------------|
| `primary` | `cyan` | Brand / headers | Report titles, app header |
| `ok` | `bright_green` | Good / completed | Sleep ≥ 7h, all transitions done |
| `warn` | `yellow` | Watch out | Sleep 5-7h, partial transitions |
| `crit` | `bold red` | Critical | Sleep < 5h, Q3 quadrant |
| `info` | `deep_sky_blue1` | Neutral info | Setpoints, base data |
| `muted` | `grey58` | Footnotes | Captions, "vs ontem" |
| `sleep` | `dodger_blue2` | Sleep / EASE | Sleep panels, EASE rows |
| `hardwork` | `green3` | Hardwork / CORE | Hardwork rows, deep-work bars |
| `ease` | `magenta` | EASE ritual | EASE ritual panel |
| `energy` | `yellow1` | Energy metric | Energy KPI card, energy row |
| `focus` | `deep_sky_blue1` | Focus metric | Focus KPI card, focus row |
| `transition` | `deep_pink1` | Transition rituals | Transition section, shutdown |

A second `COLORS` dict in `cli/renderers.py:93-116` extends the palette with 10 more semantic names (`q1`, `q2`, `q3`, `q4`, `gold`, `orange`, `purple`, `accent`, `highlight`, `secondary`). Report-renderer code uses these; core dashboard code uses the canonical palette.

## `TIPO_DIA_COLOR` — day-type colors

**Defined in:** `ui/components.py:46-51`.

```python
TIPO_DIA_COLOR: dict[str, str] = {
    TipoDia.CURSO.value:    "dodger_blue1",
    TipoDia.LIVRE.value:    "green3",
    TipoDia.HARDCORE.value: "red",
    TipoDia.DESCANSO.value: "grey50",
}
```

| Day type | Rich name | Visual cue |
|----------|-----------|------------|
| `CURSO` | `dodger_blue1` | Cool blue — structured study day |
| `LIVRE` | `green3` | Green — free / light day |
| `HARDCORE` | `red` | Red — deep work / push day |
| `DESCANSO` | `grey50` | Grey — rest day |

These are the four day categories from the PAV spec. They are surfaced in the daily header bar.

## `PERIOD_ICON` — MANHA / TARDE / NOITE icons

**Defined in:** `ui/components.py:53-57`.

```python
PERIOD_ICON: dict[str, str] = {
    Period.MANHA.value: "🌅",
    Period.TARDE.value: "💻",
    Period.NOITE.value: "🌙",
}
```

| Period | Icon | Meaning |
|--------|------|---------|
| `MANHA` | 🌅 | Morning — wake up, workout, plan |
| `TARDE` | 💻 | Afternoon — deep work, CORE |
| `NOITE` | 🌙 | Evening — shutdown, OKRs |

Icons are used in workflow headers (`_header("🌅 Iniciar Manhã")` in `home.py:160`) and on the home menu rows.

## `QUADRANT_EMOJI / COLOR / LABEL / ACTION` — Q1-Q4 visual language

**Defined in:** `ui/components.py:59-85`.

The cartesian plane plots a day's X (produtividade) vs Y (qualidade). Each quadrant has a unique visual identity.

```python
QUADRANT_EMOJI: dict[str, str] = {
    "Q1": "🏆",   # Excelente
    "Q2": "🟢",   # Otimizado
    "Q3": "🚨",   # Crítico
    "Q4": "⚠️",   # Produtivo
}

QUADRANT_COLOR: dict[str, str] = {
    "Q1": "bright_green",
    "Q2": "cyan",
    "Q3": "bold red",
    "Q4": "yellow",
}

QUADRANT_LABEL: dict[str, str] = {
    "Q1": "Excelente — manter ritmo",
    "Q2": "Otimizado mas pouco output",
    "Q3": "Crítico — revisar sistema, identificar bloqueios",
    "Q4": "Produtivo mas precisa otimizar",
}

QUADRANT_ACTION: dict[str, str] = {
    "Q1": "Manter",
    "Q2": "Aumentar volume de trabalho",
    "Q3": "Revisão urgente",
    "Q4": "Reduzir distrações",
}
```

| Quadrant | X | Y | Color | Action |
|----------|---|---|-------|--------|
| **Q1** (top-right) | ≥ 50 | ≥ 50 | `bright_green` | Manter |
| **Q2** (top-left)  | < 50 | ≥ 50 | `cyan` | Aumentar volume |
| **Q3** (bottom-left) | < 50 | < 50 | `bold red` | Revisão urgente |
| **Q4** (bottom-right) | ≥ 50 | < 50 | `yellow` | Reduzir distrações |

The point glyph on the cartesian plane is also quadrant-dependent (`ui/components.py:260-267`): `◆` for Q1/Q2, `✗` for Q3, `▲` for Q4. The `✗` in Q3 is deliberate — it is the only "negative" glyph in the system and signals "something is wrong, look at the recommendation".

## Severity levels

The severity vocabulary is the **only** color axis that is dynamic. It is a small enum that every data point carries (`ok`, `warn`, `crit`, `info`, `muted`, `None`) and that the dashboard resolves to a color via `SEVERITY_COLOR` (`ui/components.py:87-94`).

| Severity | Color | Resolved by |
|----------|-------|-------------|
| `ok` | `bright_green` | `sev_for_*` helpers in `ui/components.py:101-164` |
| `warn` | `yellow` | same |
| `crit` | `bold red` | same |
| `info` | `deep_sky_blue1` | same |
| `muted` | `grey58` | same |
| `None` | `white` | default fallback in `SEVERITY_COLOR` |

The classification functions (`sev_for_wake_hour`, `sev_for_sleep_hours`, `sev_for_lunch`, `sev_for_transicoes`, `sev_for_desvio`, `sev_for_quality`) take a raw value and return a severity string. They are pure functions, deterministic, and live in `ui/components.py:101-164`. New metrics should add a new `sev_for_*` function there, not embed the thresholds in the controller.

## How to add a new color

The discipline is "extend, do not fork". When you need a new semantic color:

1. **Reuse if possible.** If your new use case fits one of the 11 existing keys (e.g. "this is an energy metric"), do not add a new key — use `energy` and add a comment in the controller explaining the choice.
2. **Add to the palette only if it is genuinely new.** Edit `COLORS` in `ui/components.py:31-44`. Pick a Rich color that has good contrast on both dark and light backgrounds (Rich has 256 named colors — see [the Rich style docs](https://rich.readthedocs.io/en/stable/appendix/colors.html)).
3. **Add to `SEVERITY_COLOR` only if it is a severity.** New severity levels (e.g. `"highlight"`) go in `SEVERITY_COLOR` (`ui/components.py:87-94`).
4. **Update the lookup helpers if it is a quadrant or day type.** Add to `TIPO_DIA_COLOR` / `QUADRANT_*` if relevant. These dicts double as the canonical "what is the visual identity of X" registry.
5. **Document in this file.** Add a row to the relevant table above.

Never inline a Rich color name (e.g. `style="bold red"`) inside a controller or report. Always reference the palette key. The only exception is the singleton's own `style=` arguments in `home.py:88-93`, which are pure UI chrome and not part of the data palette.

## The no-color mode

When `is_captured()` returns `True` (`ui/__init__.py:35-37`), the singleton Console is built with `no_color=True` (`ui/__init__.py:48`). In this mode, **all** color and most style attributes are stripped from the output. The Unicode box characters (`╭─╮`, `│`, `▣ ▢`, `▁▂▃▄▅▆▇█`, `◆ ✗ ▲`) are **preserved** because `safe_box=False` is still in effect.

This is the same output that `format_as_json` returns (after `strip_ansi` is applied for safety). The point is: **the dashboard is still readable in a captured buffer or a `| less` pipe.** The Unicode characters carry the visual information; the colors are an enhancement.

If you find yourself reaching for `style="white"` because the dashboard looks "boring" in no-color mode — stop. The data layout, the box characters, the percentages, the icons, and the labels are all there. The colors are the cherry on top, not the substance.
