# 01 — Objetivos de Produto

> Este documento lista os 8 objetivos centrais do `operational` CLI,
> priorizados em P0 (precisa ter), P1 (deveria ter) e P2 (seria bom ter).
> Cada objetivo tem persona-alvo, métrica de sucesso e status atual
> (como alcançá-lo via comandos existentes).

A ideia aqui não é descrever o *que* o sistema faz tecnicamente (isso
está em `architecture/`), mas o *porquê* do ponto de vista do usuário
final. Se um objetivo não for alcançável hoje, ele aparece marcado como
**gap** — e isso vira candidato natural para o backlog de UX.

---

## Legenda de prioridade

| Sigla | Significado | Quando descartar |
|-------|-------------|------------------|
| **P0** | Crítico. Sem isso, o CLI não cumpre sua proposta. | Nunca. |
| **P1** | Importante. Diferencial vs alternativas. | Só após P0 estabilizado. |
| **P2** | Desejável. Polimento. | Quando virar P0, sobe. |

---

## P0 — Objetivos críticos

### OBJ-01 — Registrar sono de ontem em < 30 segundos

- **Objetivo:** "Eu acordei. Em menos de 30s, eu registrei que horas eu
  dormi, que horas eu acordei, e como foi a qualidade do sono."
- **Persona-alvo:** Dev Solo que acorda cedo (4h–5h) e quer começar o
  dia sem fricção.
- **Métrica de sucesso:** Tempo entre o comando `operational home` →
  opção 1 → `_run_cmd(["metric", "sleep", ...])` e a confirmação
  visual `✓ Sono registrado`. Meta: < 30s para 5 prompts simples.
- **Status atual:** ✅ Alcançável. Comando
  `metric sleep -q 8 -bh 20 -bm 30 -wh 4 -wm 0` cobre em 1 linha
  não-interativa. Fluxo interativo do menu (opção 1 → `_flow_morning`)
  tem 5 prompts sequenciais: qualidade, hora-dormiu, min-dormiu,
  hora-acordou, min-acordou. Cada prompt tem `default=` razoável
  (`cli/home.py:170-179`), então apertar Enter 5 vezes completa o
  registro.

### OBJ-02 — Ver "onde estou" em relação ao plano do dia

- **Objetivo:** "Em < 5s eu sei se estou no plano, atrasado, ou se já
  era pra ter parado."
- **Persona-alvo:** Dev Solo que trabalha em sessões longas de 50min e
  precisa decidir se continua, para, ou troca de tarefa.
- **Métrica de sucesso:** 1 olhar cobre: sono OK? pomodoros meta?
  hardwork orçado vs realizado? Q1/Q2/Q3/Q4? Próxima ação sugerida?
- **Status atual:** ✅ Alcançável. Comando `operational state show`
  (`cli/commands/state_cmd.py:71-130`) renderiza um dashboard 2x2 com
  4 KPI cards (Sono, Pomodoros, Hardwork, Energia/Foco) + grid de
  pomodoros + activity table + next-step panel. Tempo de render: 20-80ms
  para 30 dias de dados. Em caso de JSON piping, `--json` extrai tudo
  num payload estruturado.

### OBJ-03 — Identificar burnout antes de chegar lá

- **Objetivo:** "O sistema me avisa quando estou 3+ dias seguidos em
  Q3, ou quando meu sono médio semanal cai abaixo de 6h."
- **Persona-alvo:** Dev Solo que trabalha sozinho e não tem um manager
  pra puxar a orelha dele.
- **Métrica de sucesso:** Comando `operational report weekly` mostra
  (a) distribuição por quadrante com contagem de Q3, (b) média de
  sono com cor `crit` se < 5h, e (c) um next-step panel `crit` quando
  há Q3 detectado (`cli/commands/report_cmd.py:296-301`).
- **Status atual:** ✅ Alcançável. O relatório semanal já detecta Q3 ≥ 1
  e dispara o alerta. Detecção de *sequência* de Q3 (3+ dias) ainda
  é **gap** — precisa de lógica extra em
  `core/weekly_aggregator.py` (não coberto ainda — ver
  `INTEGRATION-BACKLOG.md`).

### OBJ-04 — Refletir sobre o dia em < 2 minutos

- **Objetivo:** "Antes de dormir, em 2min eu respondo: deu_certo?
  deu_errado? maior_aprendizado? ajustes_para_amanhã?"
- **Persona-alvo:** Dev Solo, ritual noturno (~22h) antes de dormir.
- **Métrica de sucesso:** Tempo entre `reflect saida` e a confirmação
  `✔ OKRs de saída registrados!`. Meta: < 2min para 4 prompts.
- **Status atual:** ✅ Alcançável. Comando `reflect saida` tem 4
  prompts sequenciais: deu_certo (lista ;-separada), deu_errado
  (lista), maior_aprendizado (texto livre com default), ajustes
  (lista). Cada prompt tem `default=""`, então Enter pula
  (`cli/commands/reflect_cmd.py:81-84`).

### OBJ-05 — Comparar semana atual vs anterior em < 10s

- **Objetivo:** "Eu vejo se minha produtividade média subiu, se meu
  sono melhorou, se eu tive mais dias Q1 esta semana."
- **Persona-alvo:** Dev Solo em revisão semanal de domingo à noite.
- **Métrica de sucesso:** 1 comando gera comparação A/B (atual vs
  anterior) com 4 KPIs (hardwork, pomodoros, sono, Q1 count) e
  sparklines de 7 dias para tendência visual.
- **Status atual:** ⚠️ Parcialmente alcançável. O comando
  `report weekly` mostra os 7 dias correntes com sparklines
  (`ui/daily_report.py` + `cli/commands/report_cmd.py:202-204`), mas
  a **comparação A/B** com a semana anterior ainda é **gap** — o
  weekly só olha 1 janela. Workaround: rodar duas vezes com `--start`
  e `--end` diferentes e comparar mentalmente.

---

## P1 — Objetivos importantes

### OBJ-06 — Trocar entre dataset sintético, golden e production

- **Objetivo:** "Quero testar uma feature nova com `golden.csv` sem
  perder meus dados reais."
- **Persona-alvo:** Dev Solo que contribui para o próprio projeto e
  precisa de dataset de teste previsível.
- **Métrica de sucesso:** 1 comando lista datasets disponíveis, 1
  comando ativa, 1 comando volta. Nenhum dado é perdido durante o
  switch.
- **Status atual:** ✅ Alcançável. Comando
  `demo dataset` lista, `demo dataset golden` ativa via env var
  `TIME_TASKER_DATASET=golden`. Trocar de volta: `demo dataset
  production`. Os datasets vivem em CSV (golden.csv, synthetic.csv)
  e a persistência real é feita via JSON em
  `~/.time-tasker/*.json` — alternar é só mudar a env var
  (`cli/commands/demo_cmd.py:182-235`).

### OBJ-07 — Diagnosticar problemas do CLI em < 1 minuto

- **Objetivo:** "Algo quebrou. Em 1min eu descubro se é: Python
  desatualizado, pacotes faltando, state dir corrompido, ou um bug de
  dados."
- **Persona-alvo:** Dev Solo e contribuidores open-source.
- **Métrica de sucesso:** 1 comando roda 7 checks (Python, packages,
  state_dir, datasets, constants, console, files_sanity) e reporta
  pass/fail com severidade visual.
- **Status atual:** ✅ Alcançável. Comando `operational doctor` faz
  exatamente isso (`cli/commands/doctor_cmd.py:191-250`) e renderiza
  um painel Rich com ícones `[green]OK[/green]` /
  `[red]FAIL[/red]`. Suporta `--json` para CI/log scraping.

### OBJ-08 — Aderir a horários-ouro (acordar 4h, dormir 21h)

- **Objetivo:** "O sistema me diz quando meu horário de acordar está
  fora do padrão ouro (3h-5h = ok, 6h = warn, 7h+ = crit)."
- **Persona-alvo:** Dev Solo em rotina CURSO (SENAI seg-sex).
- **Métrica de sucesso:** Severity `ok`/`warn`/`crit` aparece em todos
  os pontos onde wake_hour é exibido: daily report (linha "Acordou"),
  state dashboard (KPI card Sono), e sparklines semanais (média
  aparece em `ok` se ≥ 7h ou `crit` se < 5h).
- **Status atual:** ✅ Alcançável. O helper
  `sev_for_wake_hour(hour)` (`ui/components.py:101-110`) é usado em
  `ui/daily_report.py:97-99` e em `ui/components.py:101-110`. Thresholds:
  3–5h = `ok`, 6h = `warn`, 7h+ = `crit`. Mudar o padrão-ouro exige
  editar `constants.py` (`PAV.HORARIO_ACORDAR_MIN`/`MAX`).

---

## Resumo visual

| ID | Título | Persona | Prio | Status |
|----|--------|---------|------|--------|
| OBJ-01 | Sono < 30s | Dev Solo | P0 | ✅ |
| OBJ-02 | "Onde estou" < 5s | Dev Solo | P0 | ✅ |
| OBJ-03 | Detectar burnout | Dev Solo | P0 | ⚠️ parcial |
| OBJ-04 | Reflexão < 2min | Dev Solo | P0 | ✅ |
| OBJ-05 | Comparar semanas | Dev Solo | P0 | ⚠️ parcial |
| OBJ-06 | Trocar dataset | Contribuidor | P1 | ✅ |
| OBJ-07 | Doctor < 1min | Contribuidor | P1 | ✅ |
| OBJ-08 | Padrão-ouro horários | Dev Solo | P1 | ✅ |

---

## Onde ler mais

- **Glossário dos termos usados** (Q1-Q4, EASE, HARDWORK, etc.) →
  [`04-glossario-dominio.md`](04-glossario-dominio.md)
- **Catálogo das telas que entregam esses objetivos** →
  [`../01-inventario/01-telas-inventario.md`](../01-inventario/01-telas-inventario.md)
- **Componentes visuais por trás das telas** →
  [`../02-componentes/`](../02-componentes/)
