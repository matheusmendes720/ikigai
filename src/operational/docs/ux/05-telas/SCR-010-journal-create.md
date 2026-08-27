# SCR-010 — Journal Create (Form de Entrada de Diário)

**Comando:** `operational journal create [flags]`
**Arquivo renderizador:** `cli/commands/journal_cmd.py:20-43`
**Arquivo de comando:** `src/operational/cli/commands/journal_cmd.py`
**Tipo:** Form muito curto (2 flags) — não tem argumentos posicionais. Aceita modo não-interativo.
**Modo JSON:** Sim — `--json` retorna a entidade `JournalEntry` serializada.
**Validação:** Pydantic v2 via factory `make_journal_entry` (`meta/factories.py:144-162`) → `JournalEntry` (`entities/journal.py:90`).

## Propósito

Registrar uma **entrada de diário** (PAV §10) — texto livre narrando o dia, com data opcional. É o "diário bruto" do sistema: o que você viveu, pensou, aprendeu. Valor gerado:

- **Narrativa diária** que alimenta o `report daily` (lê `entry_text` truncado em 50 chars no list, completo no relatório).
- **Captura retroativa** — você pode registrar o dia de ontem caso tenha esquecido.
- **Base para reflexões estruturadas** — `reflect entrada`/`saida` usa a mesma entity mas com campos OKR (parar_de_fazer, etc.); `journal create` é a versão minimal.
- **Único campo "válvula de escape"** — se você só quer escrever 1 linha sem categorias, é este command.

## Usuário-alvo

- **Primário:** practitioner PAV que quer **escrever livremente** sobre o dia sem categorizar em OKRs.
- **Momento de uso:** final do dia (antes de dormir) ou no dia seguinte (manhã, ao acordar).
- **Frequência:** alta — 1× por dia idealmente, ou 2-3× se碎片化 (chunks curtos).

## Entradas

- **Do Home Menu:** opção `3` (Encerrar Dia) cria um journal agregador de 4 prompts (`deu_certo`, `deu_errado`, `aprendizado`, `ajustes`) via `journal create --text` (`home.py:243-255`).
- **Do Home Menu:** opção `4` (Check-in Rápido) cria um journal curto `f"Check-in: {note}"` se você passou nota (`home.py:276`).
- **Comando direto:** `operational journal create --text "Hoje foi um dia focado..."`.
- **Auto-trigger:** nenhum.

## Saídas

- **Persiste em:** `journals.json` (via `cli.state.journals`).
- **Confirmação:** `✓ Entrada criada: <id>` + preview do texto em itálico dim (`journal_cmd.py:39-43`).
- **Redireciona:** volta ao shell / menu. Sem próximo passo sugerido (mas o dashboard usa o journal para narrativa).

## Modos de uso

### Modo 1: Flags (não-interativo) — mais comum

```bash
operational journal create --text "Acordei 06:00, fiz workout, estudei 4h ENEM, almocei leve. Energia 7/10, foco 8/10. Aprendizado: micro-pausas funcionam."
# Saída:
#   ✓ Entrada criada: day_2026_06_08
#   data: 2026-06-08 · 142 caracteres
#     "Acordei 06:00, fiz workout, estudei 4h ENEM, almocei leve. Energia 7/10,..."
```

### Modo 2: Data retroativa

```bash
operational journal create --date 2026-06-07 --text "Ontem esqueci de logar..."
# Cria entrada com date=2026-06-07, id=day_2026_06_07
# Se já existe entry para 2026-06-07, UPSERT (substitui text, atualiza updated_at)
```

### Modo 3: Texto vazio (aceita, mas sem narrativa)

```bash
operational journal create
# Cria entry com text="", id=day_YYYY_MM_DD
# Útil para "marcar o dia" sem escrever nada
```

### Modo 4: JSON

```bash
operational journal create --date 2026-06-08 --text "..." --json
# Saída: {"id": "day_2026_06_08", "date": "2026-06-08", "entry_text": "...", ...}
```

## Argumentos e flags (TODOS)

| Parâmetro | Tipo | Default | Obrigatório | Validação Pydantic | Exemplo |
|---|---|---|---|---|---|
| `--date`, `-d` | str (ISO date) | hoje | não (Option) | `date.fromisoformat()` (raise `ValueError` se malformado) | `2026-06-08` |
| `--text`, `-t` | str | `""` | não (Option) | `max_length=5000` (entity `JournalEntry.entry_text`) | `"Hoje foi..."` |
| `--json` | bool | `False` | não (Option) | — | — |

> **⚠ Atenção:** `--date` aceita **qualquer string** que `date.fromisoformat()` aceite: `2026-06-08`, `2026-01-01`, etc. Não há validação de "data não é futuro" — você pode criar journal de 2030 se quiser. Útil para planejamento; perigoso para inconsistência.

> **⚠ Atenção:** `--text` **vazio é aceito**. Não há `min_length=1` na entity (`entities/journal.py:113`: `entry_text: str = Field(default="", max_length=5000)`). Journal com texto vazio aparece como preview `(vazio)` no list.

## Wireframe passo-a-passo

### Estado: Criação bem-sucedida via comando direto

```
$ operational journal create --text "Acordei 06:00, fiz workout, estudei 4h ENEM."

╭─ Input Summary ──────────────────────────────╮
│  Criando entrada de diário                    │
│    date      : 2026-06-08                     │
│    text_len  : 41                             │
│    preview   : Acordei 06:00, fiz workout, e… │
╰───────────────────────────────────────────────╯
  ✓ Entrada criada: day_2026_06_08
    data: 2026-06-08 · 41 caracteres
    "Acordei 06:00, fiz workout, estudei 4h ENEM."
```

### Estado: Invocação via Home Menu (Encerrar Dia)

```
# _flow_evening() em home.py:238-255:
? O que deu certo hoje? ["]: Estudei 4h sem interrupção
? O que deu errado hoje? ["]: Procrastinei 30min à tarde
? Maior aprendizado do dia? ["]: Pomodoro de 25min é melhor que 50min
? Ajustes finos para amanhã? ["]: Bloquear redes sociais 14-17h

# Internamente monta:
text = "✅ Deu certo: Estudei 4h sem interrupção\n❌ Deu errado: Procrastinei 30min à tarde\n💡 Aprendizado: Pomodoro de 25min é melhor que 50min\n🔧 Ajustes: Bloquear redes sociais 14-17h"
$ operational journal create --text "<text multilinha>"
  ✓ Entrada criada: day_2026_06_08
    data: 2026-06-08 · 187 caracteres
```

### Estado: Data malformada

```bash
$ operational journal create --date "ontem" --text "Teste"
# ValueError: Invalid isoformat string: 'ontem'
# (date.fromisoformat() raise)
# Exit code: 1
```

> **⚠ Atenção:** Typer **não** valida formato de `--date`. O erro vem de `date.fromisoformat()` no command, com mensagem técnica (não traduzida). Em versões futuras, usar `core.services.parse_iso_date` para mensagem PT-BR.

### Estado: Texto >5000 chars

```bash
$ operational journal create --text "$(python -c 'print("x"*5001)')"
# Pydantic: String should have at most 5000 characters
# Exit code: 1
```

### Estado: Texto vazio (aceito)

```bash
$ operational journal create
  ✓ Entrada criada: day_2026_06_08
    data: 2026-06-08 · 0 caracteres
    "(sem preview)"
```

Aparece no `journal list` com preview `(vazio)` em cinza.

## Validação e erros

| Cenário | Comportamento | Onde é validado |
|---|---|---|
| `--date` malformado | `date.fromisoformat()` raise `ValueError` | `journal_cmd.py:27` |
| `--date` em formato não-ISO | Typer não valida, Pydantic não recebe o campo | `journal_cmd.py:22-27` |
| `--text` >5000 chars | Pydantic `max_length=5000` rejeita | `entities/journal.py:113` |
| `--text` vazio | Aceito (sem `min_length`) | n/a |
| Entry duplicada (mesmo date) | `journals.upsert()` substitui (id = `day_YYYY_MM_DD`) | `state.py:upsert` |
| Multiline text com `\n` | Aceito; preview mostra com `replace("\n", " ")` (`journal_cmd.py:42`) | renderização |

## Estados (5)

| Estado | Notas |
|---|---|
| **Vazio** | Não aplicável — command roda sem nenhum argumento (cria entry de hoje com texto vazio) |
| **Loading** | Não aplicável — operação síncrona |
| **Com dados (sucesso)** | Wireframe "Criação bem-sucedida" |
| **Erro de validação** | Data malformada, texto >5000 |
| **Cancelamento (Ctrl+C)** | Nada persistido |

## Comportamento interativo

- **Tipo de prompt:** nenhum no command. Toda entrada é via flags.
- **Validação inline:** Typer (não valida `--date`) + Pydantic (max_length de text).
- **Defaults:** `--date=hoje`, `--text=""`.
- **Histórico:** não aplicável.
- **Ctrl+C:** nada persistido.
- **Ctrl+D:** mesma rota.
- **Timeout:** não há.

## Comportamento especial: UPSERT por data

O `id` da entity é `day_YYYY_MM_DD` (`entities/journal.py:132`). Como o repositório `journals` faz **upsert** (substitui se o id já existe), criar uma nova entrada para o mesmo dia **substitui** a anterior:

```bash
$ operational journal create --text "Versão 1"
  ✓ Entrada criada: day_2026_06_08
$ operational journal create --text "Versão 2 — atualizada"
  ✓ Entrada criada: day_2026_06_08  # mesmo id, texto substituído
```

O campo `updated_at` é auto-refreshed em Pydantic (`entities/journal.py:196-213`). Útil para "edit diário"; arriscado se você queria manter histórico.

> **⚠ Atenção:** não há "versionamento" — cada chamada sobrescreve a anterior. Para histórico de reflexões, use `reflect entrada`/`saida` (que têm campos OKR estruturados e **merge com entry existente** — ver `reflect_cmd.py:90-100`).

## Comandos relacionados

- `journal list` — Rich Table com energy/focus/humor bars + preview (`journal_cmd.py:46-112`).
- `journal list --date 2026-06-08` — filtra por data.
- `reflect entrada` — OKRs estruturados de manhã (parar_de_fazer, repetir, big_win).
- `reflect saida` — OKRs estruturados de noite (deu_certo, deu_errado, aprendizado, ajustes).
- `state show` — dashboard que inclui a entry do dia.
- `report daily` — relatório que cita o `entry_text` no narrative panel.

> **Gap conhecido:** não há `journal update` (precisa recriar com mesmo `--date`); não há `journal delete`; não há `journal archive`.

## Riscos de usabilidade

Específicos deste form:

1. **Texto vazio é aceito** — usuário pode criar journal "em branco" sem aviso. Polui o dashboard.
2. **Sem validação de data futura** — você pode criar entry de 2030. A `date.fromisoformat()` não reclama.
3. **Erro de data malformada é técnico** — `ValueError: Invalid isoformat string: 'ontem'` em vez de "Data inválida. Use YYYY-MM-DD".
4. **UPSERT silencioso** — criar duas entries no mesmo dia **substitui** a primeira sem aviso. Usuário pode perder texto sem perceber.
5. **Sem preview antes de salvar** — o command grava direto. Para journal longo, isso é arriscado (e.g., "esqueci de mencionar X" — só descobre ao listar).
6. **Limit de 5000 chars é arbitrário** — não configurável. Para journal muito longo, precisa quebrar em múltiplas entries (mas isso cria ids diferentes e perde o "single narrative").
7. **Multiline via shell** — usar `--text "$(cat <<EOF ... EOF)"` funciona em bash; no Windows cmd exige `"line1\nline2"` ou escaping. UX-rugoso.
8. **Sem campos estruturados (energia/foco/humor)** — esses campos existem na entity (`JournalEntry.energia_nivel`, `foco_nivel`, `humor_morning`, `humor_evening`) mas **não são expostos na CLI**. Para setar, é preciso override via factory ou `reflect entrada`/`saida`. O `journal create` é minimal.

## Métricas de sucesso

- **Tempo médio de cadastro:** target <15s (pensar + digitar).
- **Taxa de uso com texto não-vazio:** target >70%. (Diário vazio = lembrete não cumprido.)
- **Frequência de UPSERT (mesmo dia):** target <10% (deveria ser criação primária).

## Onde aparece

- **Home Menu opção `3` (Encerrar Dia)** — `home.py:243-255`: agrega 4 prompts em uma única entry multilinha com emojis ✅/❌/💡/🔧.
- **Home Menu opção `4` (Check-in Rápido)** — `home.py:276`: cria entry `f"Check-in: {nota}"` se você passou nota; caso contrário, só registra energia/foco via `metric energy`.
- **Não aparece** nas opções `1` (Manhã) e `2` (Tarde).

## Notas de implementação

- **File:line refs:**
  - `cli/commands/journal_cmd.py:20-43` — definição do command `create`.
  - `cli/commands/journal_cmd.py:27` — `date.fromisoformat(entry_date) if entry_date else date.today()`.
  - `cli/commands/journal_cmd.py:34-35` — chamada da factory `make_journal_entry` + `journals.upsert(entry)`.
  - `meta/factories.py:144-162` — `make_journal_entry()` com defaults.
  - `entities/journal.py:90` — classe `JournalEntry` (Pydantic v2, `frozen=False` para `updated_at`).
  - `entities/journal.py:113` — `entry_text: str = Field(default="", max_length=5000)`.
  - `entities/journal.py:196-213` — `_auto_set_updated_at` (refresh em cada assignment).
- **Como adicionar `--energia`/`--foco`:** adicionar flags na assinatura e passar como `**overrides` para `make_journal_entry`. A factory faz `**overrides` (`factories.py:148, 162`), então qualquer campo válido de `JournalEntry` é aceito.
- **Como usar `parse_iso_date` (mensagem PT-BR):** importar de `operational.core.services` e usar em vez de `date.fromisoformat()`. Levanta `DataInvalidaError` (PT-BR: "Data inválida 'X'. Motivo: Y.").
- **Onde fica o estado após submit:** `cli/state.py:journals`. O `id` é `day_YYYY_MM_DD` (determinístico, mesmo date = mesmo id = UPSERT).
