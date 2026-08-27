# 02 — Checklist de Usabilidade

> Checklist prático para revisar **qualquer nova tela** antes de merge.
> Use em PR review como segunda camada (após lint/typecheck/test).
> 30+ itens agrupados por 8 categorias. Cada item tem:
> - **Pergunta** que o revisor faz
> - **Como verificar** (manual ou automático)
> - **Severidade** se falhar (Alta/Média/Baixa)
>
> Inspirado em checklists de NNG, Baymard, e padrões internos. **Não é exaustivo** — é o mínimo que toda tela deve passar.

---

## Como usar

```markdown
## Review da Tela: [SCR-NNN nome]

**Revisor:** @fulano
**Data:** 2026-06-08
**Tela:** docs/ux/05-telas/SCR-NNN-...md (ref futura)

### Compreensibilidade
- [x] User sabe o que esta tela faz em <5s
- [ ] Propósito aparece no header
- [x] Sem jargão técnico

### Navegação
- [x] User sabe como voltar
- [ ] User sabe como sair
- [x] Tecla "b" (back) documentada
- ...

## Veredicto
[ ] Aprovado
[ ] Aprovado com comentários
[ ] Mudanças necessárias
```

**Severidades:**

- **Alta** — bloqueia merge. User fica confuso, perde dados, ou não consegue usar.
- **Média** — pode mergir com issue aberto. UX degradada mas funcional.
- **Baixa** — polimento. Não bloqueia.

---

## Compreensibilidade (3 itens)

### C-1: User sabe o que esta tela faz em <5s

- [ ] O **propósito** da tela aparece no **header** ou **primeira linha**
- [ ] Não exige ler parágrafos para entender
- **Como verificar:** mostrar tela a alguém de fora do time. Se pedir "o que é isso?", falhou.
- **Severidade:** Alta

### C-2: Linguagem em PT-BR sem jargão

- [ ] Sem `Pydantic`, `ValidationError`, `TypeError`, `NoneType`
- [ ] Sem `snake_case` em labels visíveis
- [ ] Sem menção a "JSON", "repo", "entity" (jargão interno)
- **Como verificar:** grep por termos técnicos em `cli/commands/`, `ui/components.py`. Se aparecer, mover para log/hint.
- **Severidade:** Média

### C-3: Glossário de símbolos disponível

- [ ] Cores têm significado documentado (ok/warn/crit)
- [ ] Emojis têm significado documentado (🌅=MANHÃ, 💻=TARDE, 🌙=NOITE, ⚡=energia)
- [ ] Glyphs (◆▲✗) têm legenda inline
- **Como verificar:** abrir `docs/tui/04-COLOR-PALETTE.md` (ref) e checar se todos os símbolos da tela estão lá.
- **Severidade:** Média

---

## Navegação (4 itens)

### N-1: User sabe como voltar

- [ ] Em submenu: opção `b` (back) visível
- [ ] Em flow: prompt "Continuar? (y/n)" permite abortar
- [ ] Em relatório: `Press Enter to continue` é claro
- **Como verificar:** rodar fluxo e tentar voltar em cada etapa. Se não há como, é bloqueante.
- **Severidade:** Alta

### N-2: User sabe como sair

- [ ] Opção `q` no menu principal (`home.py:108`)
- [ ] `Ctrl+C` em qualquer prompt sai limpo (`home.py:477-480`)
- [ ] Mensagem de despedida amigável: "Até logo! 🚀" ou similar
- **Como verificar:** pressionar Ctrl+C em cada prompt. Se levantar traceback, falhou.
- **Severidade:** Alta

### N-3: Tecla "b" (back) consistente

- [ ] Todo submenu usa `_submenu` helper (`home.py:297-318`)
- [ ] Não há submenu custom que esquece o `b`
- **Como verificar:** grep `_submenu(` em `cli/`. Se algum submenu renderiza menu custom, é candidato a refatorar.
- **Severidade:** Baixa

### N-4: Sem "becos sem saída"

- [ ] Toda tela tem saída (voltar, q, Ctrl+C, Enter)
- [ ] Nenhum `sys.exit(1)` sem hint de recuperação
- **Como verificar:** tentar travar o user em loop infinito. Se conseguir, é bloqueante.
- **Severidade:** Alta

---

## Acessibilidade (3 itens)

### A-1: Funciona sem cor

- [ ] Glyphs (◆▲✗) transmitem informação independente de cor
- [ ] Texto explica o status, não só ícone
- [ ] User daltônico (~8% homens) consegue distinguir ok/warn/crit
- **Como verificar:** rodar com `NO_COLOR=1` ou em terminal cinza. Se vermelho/verde é a única diferença, falhou.
- **Severidade:** Média (UX-002)

### A-2: Funciona em terminal 80 colunas

- [ ] Layout 2x2 ou 1x1 quando width < 100
- [ ] Sem truncamento de texto em 80 col
- [ ] Tabelas largas têm versão compacta
- **Como verificar:** `stty cols 80` e abrir a tela. Se quebrar linha ou truncar, falhou.
- **Severidade:** Média (UX-003)

### A-3: Encoding UTF-8 sem BOM/CRLF

- [ ] Output em UTF-8 limpo
- [ ] Sem `?` ou `[]` no lugar de emoji
- [ ] Source files em LF (não CRLF)
- **Como verificar:** `file *` em `src/operational/cli/`. Se algum arquivo tem "CRLF", converter.
- **Severidade:** Baixa

---

## Performance (2 itens)

### P-1: Renderiza em <500ms

- [ ] Para state com 30 dias de dados
- [ ] Para state vazio (cold start)
- [ ] Para state com 365 dias (ano cheio)
- **Como verificar:** `time operational report daily`. Se > 1s, investigar.
- **Severidade:** Média

### P-2: Sem I/O bloqueante síncrono

- [ ] Sem `time.sleep()`, `input()` raw, ou `subprocess.run` sem timeout
- [ ] Operações de arquivo wrapped em `try/except`
- **Como verificar:** grep por `time.sleep` em `src/operational/`. Se aparecer, questionar.
- **Severidade:** Alta

---

## Dados (3 itens)

### D-1: Dataset vazio tratado

- [ ] Renderiza placeholders (em-dash, "(sem dados)")
- [ ] Não crasha com `None`
- [ ] Mensagem user-friendly "Comece com opção 1 (Iniciar Manhã)"
- **Como verificar:** `rm -rf ~/.time-tasker && operational state show`. Se crashar, falhou.
- **Severidade:** Alta

### D-2: Dataset corrompido tratado

- [ ] JSON com `id` duplicado não crasha
- [ ] Pydantic ValidationError logado E mostrado ao user
- [ ] Próximo `repo.clear()` regenera
- **Como verificar:** editar `~/.time-tasker/sleep_records.json` adicionando linha com `id` duplicado. Rodar `report daily`. Se crashar, falhou.
- **Severidade:** Média

### D-3: Time-tasker state dir criado lazy

- [ ] Primeira execução cria `~/.time-tasker/` automaticamente
- [ ] Permissão negada retorna erro claro (não `FileNotFoundError`)
- **Como verificar:** `rm -rf ~/.time-tasker && operational home`. Se criar dir, OK.
- **Severidade:** Média

---

## Interação (3 itens)

### I-1: Teclado funciona sem mouse

- [ ] Sem dependência de click, hover, drag
- [ ] Atalhos de tecla documentados (se houver)
- [ ] `Tab` autocompleta onde aplicável (não crítico para CLI)
- **Como verificar:** usar a tela **sem mouse**. Se Mouse for necessário, é bloqueante (CLI não suporta).
- **Severidade:** Alta

### I-2: Ctrl+C clean

- [ ] `KeyboardInterrupt` capturado em `home.py:477-480` (sai com exit 0)
- [ ] Não deixa ANSI parcial no terminal
- [ ] State inalterado se interrupção antes de `upsert`
- **Como verificar:** Ctrl+C em cada prompt. Se aparecer traceback ou prompt quebrado, falhou.
- **Severidade:** Alta

### I-3: Defaults em todos os prompts

- [ ] `Prompt.ask(..., default=...)` em todo input numérico ou string
- [ ] Default é razoável (não 0, não "")
- [ ] User pode aceitar com Enter
- **Como verificar:** rodar flow com 5 Enters consecutivos. Se completar, OK.
- **Severidade:** Média

---

## Mensagens (3 itens)

### M-1: Erros em português

- [ ] `error_panel` em PT-BR (`ui/components.py:390-426`)
- [ ] Sem "Pydantic ValidationError" no output
- [ ] Sem "TypeError" sem tradução
- **Como verificar:** forçar erro (ex: `--date 2026-13-99`). Ler mensagem. Se em inglês, falhou.
- **Severidade:** Alta (UX-012)

### M-2: Próxima ação clara após erro

- [ ] `error_panel(mensagem, hint="...")` com hint actionable
- [ ] Hint inclui comando ou referência (ex: "Tente: `operational doctor`")
- [ ] Não genérico ("Verifique os dados") sem especificidade
- **Como verificar:** forçar erro e ler hint. Se for "tente novamente" sem detalhe, falhou.
- **Severidade:** Média

### M-3: Mensagens de sucesso concisas

- [ ] Banner `✔ ...` em verde bold após flow completo
- [ ] Confirmação por comando: `✓ Sono registrado: <id>`
- [ ] Sem "Operação concluída com sucesso!" (verbose)
- **Como verificar:** rodar flow e contar caracteres da confirmação. Se > 50, enxugar.
- **Severidade:** Baixa

---

## Consistência (2 itens)

### K-1: Mesmos ícones/cores/formatos que o resto

- [ ] Severity `ok`/`warn`/`crit` em todos os lugares (`ui/components.py:SEVERITY_COLOR`)
- [ ] Emojis reservados: 🌅=MANHÃ, 💻=TARDE, 🌙=NOITE, ⚡=energia
- [ ] Banner `✔` (U+2714) e não `✓` (U+2713) ou `[OK]`
- **Como verificar:** abrir 3 telas e comparar ícones. Se algum diverge, é candidato a normalizar.
- **Severidade:** Baixa

### K-2: Layout factory único

- [ ] KPIs vêm de `kpi_card` (`ui/components.py:341-361`)
- [ ] Pomodoros vêm de `pomodoros_grid` (`ui/components.py:222-238`)
- [ ] Cartesian vem de `cartesian_plane` (`ui/components.py:241-327`)
- [ ] Sem `Table(...)` ou `Panel(...)` inline em `cli/commands/`
- **Como verificar:** `grep -n "Table(" cli/commands/*.py`. Se aparecer, é violação do pattern MVC (`architecture/01-MVC-LAYERS.md`).
- **Severidade:** Média

---

## Onde aplicar este checklist

1. **PR review de nova tela:** copiar template acima, preencher, anexar ao PR.
2. **Auto-auditoria mensal:** revisar 1 tela aleatória por semana.
3. **Onboarding de contribuidor:** novo dev roda checklist na primeira tela que tocar.

## Quando NÃO aplicar

- **Hotfix crítico** (produção quebrada) — merge rápido, auditoria pós-mortem.
- **Refactor interno** (sem mudança de UX) — skip categoria Compreensibilidade/Acessibilidade.
- **Tela de dev-only** (ex: `_run_tests` em `home.py:369-400`) — não é user-facing.

## Referências cruzadas

- **Heurísticas de Nielsen:** `01-heuristicas-nielsen.md` (H1-H10).
- **Riscos conhecidos:** `03-riscos-conhecidos.md` (UX-001 a UX-020). Cada item do checklist referencia um UX-NNN.
- **Componentes:** `docs/tui/02-COMPONENT-CATALOG.md` (CMP-001 a CMP-019).
- **Telas:** `docs/ux/05-telas/SCR-001-...md` (refs futuras).
- **Fluxos:** `docs/ux/04-fluxos/FLOW-001-...md` (FLOW-001 a FLOW-010).

## Estatísticas de uso

_(A ser preenchido após primeiros 10 PRs que usam o checklist.)_

- **Média de itens marcados:** TBD
- **% de PRs com ≥1 item Alta:** TBD
- **Itens mais frequentemente esquecidos:** TBD
