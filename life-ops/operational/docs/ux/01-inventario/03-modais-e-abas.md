# 03 — Modais e Abas (Tipos de Prompt)

> O `operational` CLI é baseado em **prompts**, não em janelas
> modais (porque é TUI, não GUI). Este documento cataloga os
> **4 tipos de prompt** que aparecem no CLI, com exemplos reais
> extraídos do código, flags que pulam o prompt (se houver),
> e o risco de fadiga de prompt acumulado.
>
> A tese é: cada prompt deve ser **curto, com default razoável,
> e fácil de pular**. Se um flow tem mais de 5 prompts, o usuário
> sente o peso e abandona.

---

## Sumário dos 4 tipos

| Tipo | Quando aparece | Implementação | Risco de fadiga |
|------|----------------|---------------|-----------------|
| **Confirmação** (Sim/Não) | Ações destrutivas ou não-óbvias | `Prompt.ask(..., choices=["y", "n"], default="y")` | Baixo (1 prompt) |
| **Escolha** (opções numeradas) | Submenus, decisões de fluxo | `Prompt.ask(..., choices=[...], default=...)` | Médio (1 prompt, mas com N opções) |
| **Texto livre** (com default) | Campos opcionais, notas, respostas de OKR | `Prompt.ask(prompt, default="")` | Baixo (default permite skip) |
| **Multi-step form** (vários prompts em sequência) | Flows longos (morning, metric sleep) | Sequência de `Prompt.ask` + `_run_cmd` | **Alto** (acumula) |

---

## Tipo 1 — Confirmação (Sim/Não)

### Definição

Pergunta binária que o usuário responde com `y` ou `n` (ou Enter
para o default). Usado em ações **destrutivas** (delete data)
ou **não-óbvias** (flows que alteram várias entidades).

### Onde aparece

- **`cli/home.py:166`** — antes de iniciar um flow (morning,
  afternoon, evening):
  ```python
  if Prompt.ask("Continuar?", choices=["y", "n"], default="y") != "y":
      return
  ```
- **`operational demo clear`** — antes de apagar todos os dados:
  ```python
  if not typer.confirm("Deseja realmente apagar todos os dados?"):
      raise typer.Abort()
  ```

### Exemplo real (flow do home)

```text
🌅 Iniciar Manhã

Esta rotina cobre:
  1. Registrar sono (retroativo)
  2. Criar rotina ENTRY (acordar)
  3. Criar bloco MANHA (workout + meditação)

Continuar? [Y/n]: █
```

### Flag que pula

- **`--yes` / `-y`**: typer option em alguns sub-comandos
  destrutivos (ex: `demo clear --yes`).
- **Default = "y"** em flows interativos: apertar Enter aceita.

### Risco de fadiga

**Baixo.** 1 prompt binário não acumula; o usuário lê, decide,
segue.

### Armadilha comum

Default errado. Se a ação é destrutiva (apagar tudo), o default
deveria ser `n` (não "y"). O flow do morning é OK com `default="y"`
porque é opt-in (o usuário escolheu opção 1 do menu, então Enter
para continuar é razoável). O `demo clear` deveria ter
`default=False` (mais seguro).

---

## Tipo 2 — Escolha (Opções Numeradas)

### Definição

Pergunta de múltipla escolha onde o usuário digita um número ou
uma string de uma lista. Usado em submenus e decisões de fluxo
(ex: pomodoro config).

### Onde aparece

- **`cli/home.py:106-110`** — menu principal:
  ```python
  choice = Prompt.ask(
      "[bold yellow]Choose[/bold yellow]",
      choices=[str(i) for i in range(1, 11)] + ["q"],
      default="5",
  )
  ```
- **Submenus** (`_menu_reports`, `_menu_data`, etc.) — `cli/home.py:297-318`:
  ```python
  choice = Prompt.ask(
      "[bold yellow]Choose[/bold yellow]",
      choices=[str(i) for i in range(1, len(items) + 1)] + ["b"],
      default="1",
  )
  ```
- **Pomodoro config** (em desenvolvimento) — escolher
  `max_per_session ∈ {2, 3, 4}`:
  ```python
  n = Prompt.ask("Max rounds per session", choices=["2", "3", "4"], default="4")
  ```

### Exemplo real (submenu)

```text
╭───  📈 Relatórios  ─────────────────────────────────────────────╮
│  1. Diário                                                       │
│  2. Semanal                                                      │
│  3. Estado consolidado                                           │
│  b. Voltar                                                       │
╰──────────────────────────────────────────────────────────────────╯

Choose [1]: █
```

### Flag que pula

- **Comando direto** (não passa pelo home): o usuário pode chamar
  `operational report daily` diretamente, sem precisar do submenu.
- **Default**: apertar Enter escolhe a primeira opção (geralmente
  "1" ou a opção mais comum).

### Risco de fadiga

**Médio.** 1 prompt de escolha não acumula, mas se o usuário
precisa fazer 3 submenus em sequência, o atrito é perceptível.
Por isso o home menu tem 10 opções no top-level (não 30).

### Armadilha comum

- **Muitas opções (>7)**: viola o "reconhecimento > recordação".
  Mitigação atual: agrupar em submenus (1-5 são workflows; 6-9
  são categorias; 10 é sistema).
- **Sem default**: se o usuário apertar Enter e o sistema reclamar
  "no default", vira atrito. **Regra:** sempre tenha default.

---

## Tipo 3 — Texto Livre (com Default)

### Definição

Pergunta aberta onde o usuário digita uma string (texto, número,
data) e o Enter aceita o default. Usado em campos opcionais ou
em OKR (reflexão).

### Onde aparece

- **`reflect saida`** — `cli/commands/reflect_cmd.py:81-87`:
  ```python
  deu_certo = _prompt_list("O que deu certo hoje", default="")
  aprendizado = Prompt.ask("  Maior aprendizado do dia", default="")
  e = Prompt.ask("  Estado final do dia (1-10)", default="6")
  ```
- **Flow morning** — `cli/home.py:170-174`:
  ```python
  q = Prompt.ask("Qualidade do sono (1-10)", default="8")
  bh = Prompt.ask("Hora que dormiu (0-23)", default="20")
  ```

### Exemplo real (reflect)

```text
🌙 OKRs de Saída — 2026-06-08

Reflita sobre HOJE para alimentar o sistema

  O que deu certo hoje (separar por ;) ['']: Feature JWT completa
  O que deu errado (separar por ;) ['']:
  Maior aprendizado do dia ['']: Sono define o dia
  Ajustes finos para amanhã (separar por ;) ['']: Dormir 20:00
  Estado final do dia (1-10) [6]: 8
```

### Flag que pula

- **Default `""`** (string vazia) — o prompt é pulado com Enter.
- **Para validação numérica**: `default="8"` significa "se você
  não disser nada, é 8". Útil quando há um valor "esperado".

### Risco de fadiga

**Baixo**, se os defaults são sensatos. Se o usuário precisa
pensar muito na resposta (ex: "maior_aprendizado"), o default
vazio permite skip.

### Armadilha comum

- **Default irrealista** (`default="7"` para "qualidade do sono"
  quando o usuário dormiu 5h). O sistema sugere 7 por preguiça,
  o usuário aceita, o Q fica inflado, e o `sev_for_quality(7)`
  retorna `ok` (que é mentira). **Mitigação:** não ter default
  em campos subjetivos que variam muito.
- **Sem limite de caracteres**: um usuário pode colar 10KB de
  texto em `notes`. Pydantic valida `max_length` (ex: 5000),
  mas o CLI não dá feedback até o Typer abortar.

---

## Tipo 4 — Multi-Step Form (Vários Prompts em Sequência)

### Definição

Sequência de 2+ prompts (de qualquer tipo) que coletam dados
relacionados antes de chamar o comando real via `_run_cmd`.
Usado em flows que alteram várias entidades ou coletam dados
estruturados.

### Onde aparece

- **Morning flow** (`_flow_morning`) — 8 prompts:
  ```python
  q = Prompt.ask("Qualidade do sono (1-10)", default="8")
  bh = Prompt.ask("Hora que dormiu (0-23)", default="20")
  bm = Prompt.ask("Minuto que dormiu (0-59)", default="30")
  wh = Prompt.ask("Hora que acordou (0-23)", default="4")
  wm = Prompt.ask("Minuto que acordou (0-59)", default="0")
  # then _run_cmd(["metric", "sleep", "-q", q, "-bh", bh, ...])
  label = Prompt.ask("Label do bloco da manhã", default="Morning Workout")
  # then _run_cmd(["block", "create", "MANHA", "--label", label])
  ```
- **Check-in flow** (`_flow_checkin`) — 3 prompts:
  ```python
  e = Prompt.ask("Energia (1-10)", default="7")
  f = Prompt.ask("Foco (1-10)", default="8")
  # then _run_cmd(["metric", "energy", "-e", e, "-f", f])
  ```
- **Reflect entrada/saida** — 4-5 prompts cada (ver Tipo 3).

### Exemplo real (morning flow completo)

```text
🌅 Iniciar Manhã

Esta rotina cobre:
  1. Registrar sono (retroativo)
  2. Criar rotina ENTRY (acordar)
  3. Criar bloco MANHA (workout + meditação)

Continuar? [Y/n]: y

Qualidade do sono (1-10) [8]: 9
Hora que dormiu (0-23) [20]: 21
Minuto que dormiu (0-59) [30]: 0
Hora que acordou (0-23) [4]: 5
Minuto que acordou (0-59) [0]: 15
Label do bloco da manhã [Morning Workout + Meditação]: Deep Work JWT

✔ Manhã iniciada!
```

### Flag que pula

- **Comando direto não-interativo**: a flag existe para pular
  o flow inteiro. Ex: `operational metric sleep -q 9 -bh 21 -bm 0 -wh 5 -wm 15`
  em 1 linha. O flow do home só existe para ajudar novatos.

### Risco de fadiga

**ALTO.** Cada prompt adicional é fricção. O usuário Mateus
usa 5-10x/dia — qualquer prompt extra vira 50s/dia perdidos.
**Regra atual:** máximo 8 prompts por flow (o morning flow
atinge o limite). Flows > 8 devem ser **divididos em
sub-flows** (Entrar/Sair).

### Armadilha comum

- **Misturar tipos de prompt** (confirmação no meio de texto
  livre) confunde o ritmo. **Regra:** confirmar no início ("Continuar?")
  e no fim ("Confirmar save?") apenas; no meio, só texto livre.
- **Sem preview antes do save**: o usuário só vê o resultado
  após `_run_cmd`, que é 1 nível de abstração abaixo. Para
  flows críticos, mostrar um **preview** ("Você está prestes a
  registrar: sono Q=9 21:00→05:15, bloco MANHA 'Deep Work JWT'.
  Confirma?").

---

## Resumo comparativo

| Tipo | # Prompts | Tempo médio | Fadiga | Recomendação |
|------|-----------|-------------|--------|--------------|
| Confirmação | 1 | < 2s | Baixo | OK para destrutivo |
| Escolha | 1 | < 3s | Médio | Default sempre |
| Texto livre | 1-3 | < 5s/prompt | Baixo | Default razoável |
| Multi-step | 4-8 | < 60s total | **Alto** | Máximo 8, dividir se mais |

---

## Padrão "voltar" durante prompt

Atualmente o `operational` **NÃO tem "voltar"** durante um
multi-step form. Se o usuário digitou errado no prompt 2 de 8,
ele tem que completar os 6 restantes ou `Ctrl+C` (que aborta
silenciosamente).

**Proposta futura (gap):** adicionar `b ← back` como choice
universal. Implementação:
```python
def _prompt_with_back(prompt, choices, default):
    full_choices = list(choices) + ["b"]
    while True:
        result = Prompt.ask(prompt, choices=full_choices, default=default)
        if result != "b":
            return result
        # else: signal back to caller
```
O caller teria que manter o índice do prompt atual e voltar se
receber `b`. Custo: ~50 linhas de código, +5-10% complexidade,
mas **UX significativamente melhor** para flows longos.

---

## Onde ler mais

- **Implementação do home menu** que orquestra os 4 tipos →
  [`../../architecture/01-MVC-LAYERS.md`](../../architecture/01-MVC-LAYERS.md)
- **Componente `next_step_panel` que aparece após o flow** →
  [`../02-componentes/03-next-step-panel.md`](../02-componentes/03-next-step-panel.md)
- **Catálogo completo de telas (que telas usam qual tipo)** →
  [`01-telas-inventario.md`](01-telas-inventario.md)
