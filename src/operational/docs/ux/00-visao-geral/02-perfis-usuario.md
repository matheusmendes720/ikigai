# 02 — Perfis de Usuário (Personas)

> Este documento descreve as 3 personas-alvo do `operational` CLI.
> Cada persona tem nome, contexto, objetivos, dores, frequência de uso,
> comandos favoritos e comandos que nunca usa. O objetivo é lembrar
> que **não existe "o usuário"** — cada pessoa usa o CLI de um jeito,
> e isso deve refletir nas decisões de UX.

As personas aqui são compostas: a primária é o próprio autor do
projeto (Dev Solo). As secundárias foram inferidas a partir do
formato do CLI e do público-alvo declarado (estudantes, contribuidores).

---

## Persona primária: Dev Solo

**Nome fictício:** Mateus, 34 anos
**Contexto:** Desenvolvedor backend full-stack em São Paulo. Trabalha
em regime autônomo + estuda no SENAI (curso técnico) de segunda a
sexta, das 7h às 12h. Tracking pessoal high-touch: usa o
`operational` CLI religiosamente, em modo interativo, todos os dias.

### Objetivos

- Acordar 4h, dormir 21h, manter sono 7-8h com qualidade ≥ 8.
- Cumprir 4 pomodoros na S1 manhã (4h-8h), 4 na S2 tarde (13h-17h),
  2-3 na S3 noite (apenas tarefas leves, regime DESCANSO ou LIVRE).
- Manter Q1 ≥ 4 dias/semana, Q3 ≤ 1 dia/semana.
- Refletir 5min de manhã (OKRs entrada) e 5min de noite (OKRs saída).
- Identificar padrões semanais (qual dia é mais produtivo, qual hábito
  está descascando, qual rotina perdeu o sentido).

### Dores (do ponto de vista do CLI)

- "Eu esqueci de logar o sono de ontem" → o flow interativo do menu
  (opção 1) só pergunta sono, mas se o usuário já acordou faz 6h e
  esqueceu, ele não lembra a hora exata que dormiu.
- "Eu não entendo 'Q3' sem ler o doc" → ver
  [`04-glossario-dominio.md`](04-glossario-dominio.md) (este folder).
- "Às vezes eu rodo `state show` e o dashboard está vazio porque
  esqueci de logar o `metric energy`" → o sistema não adivinha
  energia; o card mostra "—" cinza.
- "Demora pra entender qual `routine_type` escolher" — `ENTRY`,
  `CORE`, `EXIT`, `RITUAL` — todos enum, mas a UX é só uma combo-box
  do Typer.

### Frequência de uso

- **Diária:** 5-10 invocações (metric sleep, metric energy, routine
  create, block create, journal create, reflect entrada/saida,
  state show, report daily).
- **Semanal:** 2-3 (report weekly, reflect com mais profundidade).
- **Mensal:** 1 (ajuste de setpoints, revisão de habits, export CSV).

### Comandos favoritos (top 8)

1. `operational home` (entrada default, default="5" no Prompt.ask)
2. `operational state show` (dashboard do dia)
3. `operational report daily` (relatório V3 completo)
4. `operational metric sleep -q 8 -bh 20 -bm 30 -wh 4 -wm 0` (registro
   rápido de sono, modo não-interativo)
5. `operational metric energy -e 7 -f 8` (check-in 30s)
6. `operational reflect saida` (reflexão noturna OKRs)
7. `operational reflect entrada` (reflexão matinal OKRs)
8. `operational report weekly` (revisão de domingo)

### Comandos que nunca usa (ou quase)

- `operational routine list` (raramente precisa revisar todas as
  rotinas; usa o demo pra ver exemplos)
- `operational habit list` (criou 8 habits fixos; nunca mexe)
- `operational policy decisions` (não tem regime HARDCORE ativo, então
  o policy fica em MAINTAIN o tempo todo)
- `operational demo seed` (só roda uma vez no setup; depois
  `production` é o dataset default)
- `operational journal list` (prefere ler no Daily Report, onde
  aparece inline)

### Implicações para UX

- O **fluxo interativo** (1-4 do menu) precisa ser rápido: Mateus
  usa 5-10x/dia, e qualquer fricção adicional de 5s vira 50s/dia.
- A **densidade de informação** no state dashboard é ok: ele quer ver
  TUDO de uma vez (4 KPIs + grid + activity + next step).
- A **consistência de severidades** é crítica: ok=verde, warn=amarelo,
  crit=vermelho. Mateus lê o dashboard por cor, não por número.
- **Cores e ícones devem sobreviver ao no-color mode** (captured
  buffer). Mateus usa pipes em CI/log scraping.

---

## Persona secundária 1: Estudante universitário

**Nome fictício:** Camila, 22 anos
**Contexto:** Estudante de Ciência da Computação em universidade
pública. Não tem regime fixo de trabalho, mas usa o `operational`
**só para journal e métricas** (semanas de prova, trabalhos finais).
Não se importa com policy FSM (PUSH/MAINTAIN/REDUCE/RECOVER).

### Objetivos

- Registrar sono, energia/foco e journal de estudo durante a semana
  de provas.
- Ver se está dormindo o suficiente para a semana de prova.
- Comparar "semana de prova" vs "semana normal".

### Dores

- "O menu principal tem 10 opções, só quero 2." → Camila nunca usa
  opções 8 (Política) e 9 (Demo).
- "O que é `HARDWORK`? Eu só estudo, não trabalho." → o termo
  hardwork é confuso para quem não é CLT/autônomo.
- "O `reflect entrada/saida` pede coisas que eu não sei responder
  no meio do semestre" (`big_win`, `sempre_fazer`).

### Frequência de uso

- **Esporádica:** 2-4 invocações/semana, em semanas de prova.
- **Nula no resto do tempo.**

### Comandos favoritos

1. `operational metric sleep` (registra sono)
2. `operational metric energy` (check-in)
3. `operational journal create` (journal livre, sem OKR)
4. `operational report daily` (vê o que aconteceu)

### Comandos que nunca usa

- Tudo de `policy` (regimes PUSH/MAINTAIN/REDUCE/RECOVER não fazem
  sentido para ela)
- `routine create` (não tem rotina fixa)
- `pomodoro` tracking (ela prefere timer externo, tipo Pomofocus)

### Implicações para UX

- O CLI deveria oferecer um **modo "mínimo"** que esconde Política e
  Demo — ou uma flag `--minimal` no home menu.
- O termo **HARDWORK** deveria ser renomeado para algo mais neutro
  ("DEEP WORK" ou "FOCO") em uma versão futura.
- O **journal create** deveria ter um template "estudante" com
  prompts mais leves.

---

## Persona secundária 2: Contribuidor open-source

**Nome fictício:** Ravi, 28 anos
**Contexto:** Engenheiro de software na Índia, contribui para o
projeto `life-oss` no GitHub. Usa o `operational` CLI para **medir
foco durante sprints** de contribuição (ex: 1 sprint = 2 semanas,
8h/dia de coding).

### Objetivos

- Medir quantas horas de deep work por sprint.
- Verificar distribuição de pomodoros S1/S2/S3 durante a sprint.
- Exportar dados para CSV e analisar em Jupyter/Pandas.
- Rodar testes localmente antes de abrir PR.

### Dores

- "O `report weekly` não tem visualização por projeto" — o `label`
  do time_block às vezes tem prefixo de projeto (ex: "JWT - Deep
  Work"), mas o weekly não agrega por prefixo.
- "Quero comparar sprint 1 vs sprint 2" — mesmo gap do OBJ-05
  (Dev Solo).

### Frequência de uso

- **Esporádica em sprints:** 3-5 invocações/semana, em semanas
  ativas de contribuição.
- **Mais intenso em PR review:** `operational test` roda 2518 testes.

### Comandos favoritos

1. `operational test` (roda a suite)
2. `operational doctor` (sanity check antes de PR)
3. `operational report weekly --json | jq` (pipeline de análise)
4. `operational demo export_csv sprint1.csv` (exporta dados)
5. `operational demo dataset golden` (testa com dataset previsível)

### Comandos que nunca usa

- `operational home` (prefere CLI explícito, não menu)
- `operational reflect entrada/saida` (não tem rotina diária; é
  contribuição pontual)
- `operational routine create` (não tem rotinas pessoais fixas;
  usa time_blocks avulsos)

### Implicações para UX

- O **suporte a `--json` em todos os comandos** é crítico. Ravi
  pipea tudo em `jq` para processar.
- O **doctor** deveria ter uma checagem extra: "git status limpo?
  branch up-to-date?".
- O **test runner** deveria aceitar `--coverage` e `--failfast`
  (provavelmente já aceita via pytest por baixo).
- O **CSV export** deveria ter opção `--filter` por data (gap atual:
  exporta tudo).

---

## Resumo comparativo

| Aspecto | Dev Solo | Estudante | Contribuidor |
|---------|----------|-----------|--------------|
| Frequência | 5-10x/dia | 2-4x/semana | 3-5x/semana |
| Modo preferido | Interativo (menu) | Não-interativo (1-liner) | Não-interativo + JSON |
| Comandos favoritos | 1, 2, 3, 5, 6, 7, 8 | 4, 5, 6, 7 | 1, 2, 3, 4, 5 |
| Política FSM | Ativa (MAINTAIN) | Não usa | Não usa |
| Dataset | Production | Production | Golden (em testes) |
| Reflexão diária | Sim (entrada+saída) | Não | Não |
| Export CSV | Raramente | Nunca | Toda sprint |

---

## Onde ler mais

- **Objetivos que essas personas querem alcançar** →
  [`01-objetivos-produto.md`](01-objetivos-produto.md)
- **Princípios de design que guiam as decisões** →
  [`03-principios-usabilidade.md`](03-principios-usabilidade.md)
- **Telas que cada persona mais usa** →
  [`../01-inventario/01-telas-inventario.md`](../01-inventario/01-telas-inventario.md)
