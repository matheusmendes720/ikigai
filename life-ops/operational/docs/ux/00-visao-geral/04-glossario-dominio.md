# 04 — Glossário do Domínio PAV

> Este é o documento **mais importante** desta pasta. Ele define cada
> termo da metodologia PAV (Produtividade Algorítmica Visual) usado
> no `operational` CLI. O usuário pediu explicitamente: "eu não
> entendo Q3, X/Y, EASE, HARDWORK" — este glossário responde.
>
> **Para cada termo:** definição em 1 frase, fórmula matemática
> (quando aplicável), exemplo numérico tirado do `golden.csv`,
> onde aparece na UI, interpretação prática, e armadilha comum.

A estrutura é deliberadamente repetitiva (definição → fórmula →
exemplo → UI → interpretação → armadilha) porque o objetivo é
**escaneabilidade**: você não precisa ler 5 parágrafos para achar
a fórmula; ela está sempre no segundo bloco.

---

## Sumário alfabético

- [B — Block / Bloco](#block--bloco)
- [C — Cartesiano (Plano)](#cartesiano--plano-cartesiano)
- [C — Core (Tipo de Rotina)](#core--tipo-de-rotina)
- [C — CURSO (TipoDia)](#curso--tipodia)
- [D — DayContext](#daycontext)
- [D — DaySnapshot](#daysnapshot)
- [D — DESCANSO (TipoDia)](#descanso--tipodia)
- [D — Desvio / Infração](#desvio--infracao)
- [E — EASE](#ease)
- [E — Entry (Tipo de Rotina)](#entry--tipo-de-rotina)
- [E — Estado Psicomatico](#estado-psicomatico)
- [E — Exit (Tipo de Rotina)](#exit--tipo-de-rotina)
- [H — HARDCORE (TipoDia)](#hardcore--tipodia)
- [H — HARDWORK](#hardwork)
- [K — KPI](#kpi-key-performance-indicator)
- [L — LIVRE (TipoDia)](#livre--tipodia)
- [M — MANHÃ (Period)](#manha--period)
- [M — MAX POMODOROS PER DAY](#max-pomodoros-per-day)
- [P — PolicyState (PUSH/MAINTAIN/REDUCE/RECOVER)](#policystate-pushmaintainreducerecover)
- [P — Pomodoros Grid](#pomodoros-grid-simbolos)
- [P — Pomodoro Round / Config / Session](#pomodoro-round--config--session)
- [P — Produtividade (Eixo X)](#produtividade--eixo-x)
- [Q — Q1 / Q2 / Q3 / Q4 (Quadrantes)](#q1--q2--q3--q4-quadrantes)
- [Q — Q_HE (Quociente de Hábito Estratégico)](#q_he--quociente-de-habito-estrategico)
- [S — Severity (primary, ok, warn, crit, info, muted)](#severity-primary-ok-warn-crit-info-muted)
- [S — Sleep Quality Score (1-10)](#sleep-quality-score-1-10)
- [S — Sparkline (Caracteres)](#sparkline-caracteres-unicode)
- [T — T1–T9 (Transições)](#t1t9-transicoes-entre-periodos)
- [U — UEID (Universal Entity ID)](#ueid--universal-entity-id)
- [X / Y — Eixos do Cartesiano](#x--y-eixos-do-cartesiano)

---

## Block / Bloco

**Definição:** Intervalo contínuo de tempo (em minutos) dedicado a
uma atividade específica. Diferente de Rotina (que é *template*),
o Bloco é a *ocorrência concreta* de um período de trabalho.

**Fórmula:** `duration_minutes = (end - start).total_seconds() / 60`

**Exemplo (golden.csv):**
- `blk_demo_00_00_2026_06_02` — 04:00 → 08:00 = 240min (4h)
- `blk_demo_00_01_2026_06_02` — 08:30 → 12:00 = 210min (3h30)

**Onde aparece na UI:**
- Daily Report → linha "HARDWORK": total realizado em minutos
- State Dashboard → time blocks timeline (`timeline_h` em
  `cli/renderers.py:238-260`)
- Pomodoros Grid → cada bloco gera N rounds

**Interpretação prática:** Blocos SÃO a unidade de trabalho
rastreável. Se você quer medir "quanto tempo de deep work
hoje?", some os blocos `TARDE` com `period='TARDE'`.

**Armadilha comum:** Confundir bloco com pomodoro. Um bloco de
50min contém 1 pomodoro. Um bloco de 4h contém 4 pomodoros
(separados por 10min break cada).

---

## Cartesiano (Plano Cartesiano)

**Definição:** Visualização 2D onde X = Produtividade e Y =
Eficiência. Cada dia é plotado como 1 ponto `(x, y)` que cai em
um dos 4 quadrantes (Q1 a Q4).

**Fórmula:**
- `x = (realizado / orçado) × 100`, clamp [0, 100]
- `y = (focus_time / total_block_min) × 100`, clamp [0, 100]
- (Hoje, no relatório semanal, `y = x` como simplificação;
  ver `cli/commands/report_cmd.py:233-235`.)

**Exemplo (golden.csv, dia 2026-06-02):**
- realizado = 240min, orçado = 240min → x = 100%
- (y simplificado = x = 100%)
- (100, 100) → **Q1** (top-right, "🏆 Excelente")

**Onde aparece na UI:**
- Daily Report → seção "Plano Cartesiano"
  (`ui/daily_report.py:204-218`)
- Weekly Report → tabela "Posição Diária (X, Y, Quadrante)"
  (`cli/commands/report_cmd.py:251-275`)

**Interpretação prática:** X = "você fez o que planejava?",
Y = "quando fez, estava focado?". X alto + Y alto = Q1 (top-right).
Q3 = "não fez e nem estava focado" (combinação pior).

**Armadilha comum:** Olhar para o plano cartesiano e pensar que
X e Y são a mesma coisa. **NÃO SÃO.** Em produção, Y < X com
frequência (porque interrupções reduzem foco mas não eliminam
trabalho). Q1 só com ambos ≥ 50%.

---

## CORE (Tipo de Rotina)

**Definição:** Rotina que representa o "núcleo" do trabalho focado
do dia (deep work, estudo, coding). Diferente de ENTRY (acordar)
ou EXIT (encerrar).

**Fórmula:** Não há fórmula — é um enum: `RoutineType.CORE`.

**Exemplo:** `rou_demo_00_01_2026_06_02` → "Deep Work - Feature JWT"
com `routine_type='CORE'`, 04:30-08:00 (3h30).

**Onde aparece na UI:**
- Daily Report → rotina CORE aparece com severity "ok" se completou,
  "warn" se incompleto
- Weekly Report → distribuição por RoutineType

**Interpretação prática:** Se você só completa ENTRY (acordou) e
não completa CORE (deep work), o dia é "EASE-completo" mas
"HARDWORK-vazio". Isso é o pior cenário — acordou, mas não
produziu.

**Armadilha comum:** Marcar ENTRY como CORE. ENTRY é ritual de
abertura (10-25min); CORE é o trabalho principal (90-240min). Se
sua rotina "Acordar" está marcada como CORE, a agregação semanal
vai inflar artificialmente o HARDWORK.

---

## CURSO (TipoDia)

**Definição:** Tipo de dia em que há compromisso externo fixo
(aula no SENAI, reunião semanal, plantão). `hardwork_orcado_min`
vem do orçamento (budget) — não é fixo.

**Fórmula:** `TipoDia.CURSO` ∈ `{"CURSO", "LIVRE", "HARDCORE", "DESCANSO"}`.
Quando `weekday < 5` (seg-sex), o default é CURSO (aula).

**Exemplo (golden.csv):** `ctx_2026_06_02` tem `tipo_dia='curso'`,
orçado 240min (4h).

**Onde aparece na UI:**
- Header do Daily Report: "◆ CURSO" em dodger_blue1
- Weekly Report: "Distribuição por TipoDia" com barra por dia

**Interpretação prática:** Dia CURSO = manhã dedicada ao curso
(SENAI 7h-12h), tarde para trabalho pessoal/profissional, noite
para descanso. Orçamento típico: 4h hardwork.

**Armadilha comum:** Esquecer de mudar para LIVRE no fim de semana.
Se você mantém CURSO no sábado, o orçamento fica irrealista (você
não vai atingir 4h de deep work no sábado) e cai em Q3 desnecessariamente.

---

## DayContext

**Definição:** Entidade que registra o **plano do dia** (orçado,
meta de pomodoros, tipo de dia) ANTES do dia acontecer. Diferente
de `DaySnapshot`, que é o **resultado** (realizado, efetivo).

**Fórmula:** Não há fórmula — é um record. Veja
`entities/day_context.py`.

**Exemplo (golden.csv):** `ctx_2026_06_02`:
- `tipo_dia='curso'`
- `hardwork_orcado_min=240`
- `pomodoros_meta=12`
- `pomodoros_realizados=11`

**Onde aparece na UI:**
- Daily Report → seção HARDWORK (orçado vs realizado, calculado
  a partir do DayContext)
- State Dashboard → KPI "Hardwork" usa `budget_min` do DayContext

**Interpretação prática:** Se não há `DayContext` para a data,
o sistema **infere** CURSO/LIVRE a partir do weekday
(`core/services.py:280-284`).

**Armadilha comum:** Confundir DayContext com DaySnapshot.
**DayContext = PLANO.** **DaySnapshot = EXECUÇÃO.** O relatório
cruza os dois para calcular desvio.

---

## DaySnapshot

**Definição:** Frozen dataclass que junta todos os 14 repos para
uma data específica. É o **contrato** entre `core.services` e
`ui.daily_report` — Pydantic entities NÃO vazam para a UI; só
o snapshot.

**Fórmula:** `get_day_snapshot(d: date) -> DaySnapshot`. Veja
`core/services.py:133-277`.

**Exemplo:** Para `d = 2026-06-02`:
- `tipo_dia = TipoDia.CURSO`
- `wake_hour = 4`, `sleep_hour = 20` (bedtime 20:30, wake 04:00)
- `hardwork_orcado_min = 240`, `realizado = 240`
- `n_pomodoros = 11`, `pomodoros_meta = 12`
- `energia = 8`, `foco = 9`

**Onde aparece na UI:**
- É a **fonte de dados** de TODA tela de relatório
  (Daily, Weekly, State, Reflect)
- Nunca aparece diretamente — sempre via `render_daily_report(snap)`

**Interpretação prática:** Se um relatório está "vazio" ou "quebrado",
o problema é quase sempre um `DaySnapshot` mal formado (sleep_record
sem wake_time, day_context sem orcado_min, etc.).

**Armadilha comum:** Achar que o DaySnapshot é a mesma coisa que
o JSON persistido. **NÃO É.** Ele é uma view imutável construída
on-demand.

---

## DESCANSO (TipoDia)

**Definição:** Dia dedicado a recuperação ativa (descanso, família,
hobbies sem cobrança de produtividade). Orçamento hardwork = 0.

**Fórmula:** `TipoDia.DESCANSO` ∈ `{"CURSO", "LIVRE", "HARDCORE", "DESCANSO"}`.
Cor: grey50 (cinza).

**Exemplo (golden.csv):** Dias de sábado/domingo são tipicamente
DESCANSO ou LIVRE. No demo: `ctx_2026_06_07` (sábado) →
`tipo_dia='livre'`, orçado 180min (3h leve).

**Onde aparece na UI:**
- Header do Daily Report: "◆ DESCANSO" em cinza
- Weekly Report: distribuição por TipoDia

**Interpretação prática:** Se seu regime é PUSH e você marca
DESCANSO, está tudo bem — DESCANSO é "intencional", não "fracasso".

**Armadilha comum:** Marcar DESCANSO para um dia que você PRECISA
trabalhar (deadline, prova). Aí a frustração vem de expectativa
não-realista, não do sistema.

---

## Desvio / Infração

**Definição:** Diferença entre o **orçado** e o **realizado**, em
minutos. Severity: LEVE, MEDIA, GRAVE (sinônimos: warn, crit).
É diferente de "erro" — desvio é só uma diferença; nem sempre é ruim.

**Fórmula:**
- `desvio_min = realizado - orçado` (negativo = abaixo, positivo = acima)
- `sev_for_desvio(desvio_min)` (`ui/components.py:157-163`):
  - `-20 ≤ desvio ≤ 20` → `ok` ("DENTRO")
  - `desvio > 20` → `warn` ("ACIMA")
  - `desvio > 60` → `crit` ("MUITO_ACIMA")
  - `desvio < -60` → `crit` ("MUITO_ABAIXO")

**Exemplo (golden.csv, dia 2026-06-03):**
- orçado = 240, realizado = 180
- desvio = -60 (1h abaixo)
- severity = `warn` ("ABAIXO" — não chegou a MUITO_ABAIXO)

**Onde aparece na UI:**
- Daily Report → linha "Δ Desvio" (verde/amarelo/vermelho)
- Weekly Report → distribuição de desvios por dia

**Interpretação prática:** Desvio positivo = "você over-achou" (talvez
em HARDCORE). Desvio negativo = "você under-achou" (em geral
recovery). Ambos são informação; só viram alerta se saem do range.

**Armadilha comum:** Tratar TODO desvio como erro. Desvio de -10min
(severity `ok`) é variação natural — não corrija.

---

## EASE

**Definição:** Tempo de **recuperação** e **rituais** (sono,
hidratação, meditação, refeições, transições). É a contraparte
da HARDWORK. **EASE ≠ preguiça** — é "tudo que recupera energia
para a próxima sessão".

**Fórmula:** Não há fórmula fechada — é uma categoria conceitual
que agrupa 9 métricas (sono, acordar, dormir, workout, meditação,
lunch, jantar, luz azul, transições).

**Exemplo (golden.csv, dia 2026-06-02):**
- Sono 7.5h Q=9 → severity `ok`
- Workout 10min ✓ → `ok`
- Meditação 8min ✓ → `ok`
- Lunch 5min eat + 30min rest, sem pesado → `ok`

**Onde aparece na UI:**
- Daily Report → seção "EASE" com 9 linhas
  (`ui/daily_report.py:85-130`)
- State Dashboard → KPI "Sono"

**Interpretação prática:** Se EASE está `crit` (sono ruim, sem
workout, almoço pesado), a sessão seguinte de HARDWORK vai sofrer.
EASE é investimento em produtividade futura.

**Armadilha comum:** Sub-valorizar EASE. "Eu não preciso meditar,
só preciso focar mais" — sem EASE, foco degrada após 90min.

---

## ENTRY (Tipo de Rotina)

**Definição:** Ritual de **abertura** do dia (acordar, hidratar,
alongar, meditar 5-10min). Geralmente 10-25min.

**Fórmula:** Não há fórmula — é um enum: `RoutineType.ENTRY`.

**Exemplo:** `rou_demo_00_00_2026_06_02` → "Despertar Natural +
Hidratação" com `routine_type='ENTRY'`, 04:00-04:25 (25min).

**Onde aparece na UI:**
- Daily Report → rotina ENTRY no EASE table (severity `ok` se
  completo)

**Interpretação prática:** ENTRY é o "check-in matinal" do sistema.
Se você perde o ENTRY (acordou tarde, pulou hidratação), o dia
começa com -10% de energia/foco preditos.

**Armadilha comum:** Confundir ENTRY com CORE. ENTRY é o **pré-aquecimento**
(baixa intensidade, alta importância). CORE é o **treino principal**.

---

## Estado Psicomatico

**Definição:** Classificação discreta do estado emocional/mental
diário, inferida de um score numérico 1-10.

**Fórmula:** `EstadoPsicomatico.from_score(n)` (`enums.py`):
- `1-3` → `RUIM`
- `4-6` → `REGULAR`
- `7-10` → `BOM`

**Exemplo (golden.csv, dia 2026-06-02):** `estado_geral='bom'`
(8/10) na DailyReflection.

**Onde aparece na UI:**
- Daily Report → "Estado Subjetivo" (seção)
- Reflect list → coluna "Estado"

**Interpretação prática:** Estado Psicomatico é um **proxy** para
produtividade futura: BOM + sono OK = alta probabilidade de Q1
amanhã. RUIM + sono ruim = alta probabilidade de Q3.

**Armadilha comum:** Inserir `estado_geral` retroativamente para
"ajeitar" o histórico. O score 1-10 deve refletir o momento, não
a narrativa que você quer contar.

---

## EXIT (Tipo de Rotina)

**Definição:** Ritual de **encerramento** do dia (jantar leve,
shutdown, planejamento do dia seguinte, reflexão). Geralmente
20-30min.

**Fórmula:** Não há fórmula — é um enum: `RoutineType.EXIT`.

**Exemplo:** `rou_demo_*_2026_06_02` → "Shutdown" com
`routine_type='EXIT'`, 21:00-21:30 (30min).

**Onde aparece na UI:**
- Daily Report → rotina EXIT no EASE table

**Interpretação prática:** EXIT é o "fechamento de sistema" do
dia. Sem EXIT, o cérebro fica em "modo trabalho" enquanto você
tenta dormir → insônia, sono ruim, Q3 no dia seguinte.

**Armadilha comum:** Pular EXIT para "ganhar mais 30min de trabalho".
Ganho ilusório — você perde 1h de sono, e o dia seguinte sofre.

---

## HARDCORE (TipoDia)

**Definição:** Dia de **deep work máximo** (deadline apertado,
sprint, prova). Orçamento hardwork alto (5-8h), regime PUSH.

**Fórmula:** `TipoDia.HARDCORE` ∈ `{"CURSO", "LIVRE", "HARDCORE", "DESCANSO"}`.
Cor: red.

**Exemplo (golden.csv, dia 2026-06-04):** `ctx_2026_06_04` →
`tipo_dia='hardcore'`, orçado 285min (4h45, modo "Relatório
Trimestral").

**Onde aparece na UI:**
- Header do Daily Report: "◆ HARDCORE" em vermelho
- Weekly Report: distribuição por TipoDia

**Interpretação prática:** HARDCORE é para momentos excepcionais.
Mais que 2 HARDCORE/semana = burnout iminente. A regra PAV:
`HARDCORE_MAX_PER_MONTH = 8` (ver `core/scenario_classifier.py`).

**Armadilha comum:** Marcar dias como HARDCORE por default. Se
tudo é HARDCORE, nada é — e o sistema perde a capacidade de
distinguir urgência real de autoboicot.

---

## HARDWORK

**Definição:** Tempo **focado em trabalho** (core, deep work,
coding, estudo). É a contraparte da EASE.

**Fórmula:**
- `hardwork_orcado_min` = orçamento planejado (vem do `DayContext`)
- `hardwork_realizado_min` = soma de `time_blocks.duration_minutes`
  filtrada por `period ∈ {MANHA, TARDE}` (exclui NOITE)

**Exemplo (golden.csv, dia 2026-06-02):**
- orçado = 240min (4h)
- realizado = 240min (4h) → delta = 0 → DENTRO (severity `ok`)

**Onde aparece na UI:**
- Daily Report → seção "HARDWORK" (orçado/realizado/desvio)
- State Dashboard → KPI "Hardwork" (atual/budget %)
- Cartesian Plane → Eixo X é **produtividade** (que é realizado/orçado)

**Interpretação prática:** HARDWORK é o "output" do dia. Mas
atenção: output ≠ qualidade. 4h de HARDWORK com foco 4/10 não é
Q1 — é Q4 (produtivo, mas pouco eficiente).

**Armadilha comum:** Confundir HARDWORK com "tempo sentado na
cadeira". HARDWORK exige foco (rating ≥ 5 em energia/foco).
HARDWORK sentado olhando o nada = HARDWORK zero.

---

## KPI (Key Performance Indicator)

**Definição:** Métrica numérica de alto nível exibida num card
(`kpi_card` em `ui/components.py:341-361`). Geralmente título +
valor grande + footer descritivo.

**Fórmula:** Não há fórmula — é um padrão de UI. Exemplos:
- "Sono: 7.5h, footer: Q=9/10 · 20:30→04:00"
- "Pomodoros: 11, footer: completos hoje"
- "Hardwork: 4h00, footer: 240/240min · 100% atingido"

**Exemplo:** State Dashboard tem 4 KPI cards em grid 2x2
(`cli/commands/state_cmd.py:165-214`).

**Onde aparece na UI:**
- State Dashboard (4 KPIs: Sono, Pomodoros, Hardwork, Energia/Foco)
- Weekly Report (4 KPIs: Hardwork, Pomodoros, Sono Médio, Reflexões)
- Daily Report (header com 3-4 KPIs inline)

**Interpretação prática:** KPIs são o "1 olhar cobre tudo" do
dashboard. A escolha de 4 KPIs no state dashboard é deliberada:
cabe em 1 tela, cobre sono + trabalho + estado subjetivo.

**Armadilha comum:** Adicionar mais KPIs "porque é importante".
O dashboard vira poluído e o usuário não lê. **Regra:** 4 KPIs
máx. por tela.

---

## LIVRE (TipoDia)

**Definição:** Dia **flexível** (sem compromisso externo, sem
hardcore). Orçamento moderado (3-4h). Default para sábado/domingo.

**Fórmula:** `TipoDia.LIVRE` ∈ `{"CURSO", "LIVRE", "HARDCORE", "DESCANSO"}`.
Cor: green3.

**Exemplo (golden.csv, dia 2026-06-07 sábado):** `ctx_2026_06_07` →
`tipo_dia='livre'`, orçado 180min (3h leve).

**Onde aparece na UI:**
- Header do Daily Report: "◆ LIVRE" em verde
- Weekly Report: distribuição por TipoDia

**Interpretação prática:** LIVRE é o "default saudável" — dia
com trabalho, mas com margem. Use para catching up, hobbies
produtivos, ou transição entre sprints.

**Armadilha comum:** Tratar LIVRE como "dia de nada". LIVRE ≠
DESCANSO. Em LIVRE, você ainda orça 3-4h — só não tem cobrança
de HARDCORE.

---

## MANHÃ (Period)

**Definição:** Período do dia entre acordar (4h-5h) e o almoço
(12h). Blocos `period='MANHA'` são contados no HARDWORK.

**Fórmula:** `Period.MANHA` ∈ `{"MANHA", "TARDE", "NOITE"}`. Cor
no header: 🌅.

**Exemplo (golden.csv, dia 2026-06-02):** Bloco 04:00-08:00
(MANHA) = 4h. Pomodoros S1 manhã = 4 rounds.

**Onde aparece na UI:**
- Header do State Dashboard: "🌅 MANHA" (se for de manhã)
- Daily Report: "S1 manhã" no Pomodoros Grid

**Interpretação prática:** MANHÃ é a "sessão S1" do dia — a de
maior energia/foco. Reserve as tarefas **mais importantes** (CORE
+ ENTRY) para S1.

**Armadilha comum:** Agendar tarefas pesadas à TARDE. A energia
e o foco caem ~30% de manhã para tarde, em média. Reserve a
tarde para tarefas **administrativas** (email, organização,
reuniões).

---

## MAX POMODOROS PER DAY

**Definição:** Limite superior de pomodoros por dia, configurado
por regime PUSH/MAINTAIN/REDUCE/RECOVER. Vem de
`constants.py:MAX_POMODOROS_PER_DAY`.

**Fórmula:**
- PUSH = 10 rounds
- MAINTAIN = 8 rounds
- REDUCE = 5 rounds
- RECOVER = 2 rounds

**Exemplo (golden.csv):** `ctx_2026_06_02` → `pomodoros_meta=12`
(excede o limite MAINTAIN=8, mas é o valor do DayContext específico;
o `MAX_POMODOROS_PER_DAY` é o **teto absoluto**).

**Onde aparece na UI:**
- Daily Report → linha "Pomodoros: 11/12" (ratio)
- State Dashboard → KPI "Pomodoros"

**Interpretação prática:** Mais que MAX_POMODOROS_PER_DAY é
**alarme**: foco sustentado de 50min × 12 = 10h é incompatível
com sono ≥ 7h + almoço + ENTRY/EXIT. Provável erro de registro.

**Armadilha comum:** Forçar meta de pomodoros acima do regime
atual. Se você está em REDUCE, o limite é 5. Forçar 8 gera
inflação artificial e mascara o burnout.

---

## PolicyState (PUSH/MAINTAIN/REDUCE/RECOVER)

**Definição:** Regime **cibernético** atual, ajustado pelo
`PolicyEngine` (state machine em `core/policy_engine.py`) com base
em Q_HE, sono, e tendências semanais. Determina os **setpoints**
(orçamento, max pomodoros, Q_HE target, allowed phases).

**Fórmula:** Não há fórmula fechada — é uma state machine.
Transições:
- PUSH → MAINTAIN (se sono < 7h médio ou Q_HE < 0.7)
- MAINTAIN → REDUCE (se 2+ dias Q3 consecutivos)
- REDUCE → RECOVER (se 3+ dias Q3 consecutivos)
- RECOVER → MAINTAIN (se Q_HE ≥ 0.65 e sono ≥ 7h)
- MAINTAIN → PUSH (se Q_HE ≥ 0.85 por 1 semana)

**Exemplo (golden.csv):** `pol_demo_01_2026_06_03` → state
`REDUCE`, severity `WARNING`, reason "Desvio leve mas recuperavel.
Recomendar sono extra."

**Onde aparece na UI:**
- Policy Decisions table (`policy list`)
- State Dashboard (não diretamente — fica implícito nos setpoints)

**Interpretação prática:** PolicyState é a "sugestão do sistema
para o seu regime". Você pode **override** via `policy setpoints`
manualmente. PUSH é "vamos lá", RECOVER é "pare tudo".

**Armadilha comum:** Ignorar PolicyState. "Eu sei que estou em
burnout, mas tenho que entregar" — sim, mas o sistema está
avisando que a próxima semana vai ser Q3 com 80% de chance.

---

## Pomodoros Grid (Símbolos)

**Definição:** Visualização compacta de quantos pomodoros foram
completos em cada sessão (S1 manhã, S2 tarde, S3 noite).

**Fórmula:** Cada round completo = `▣` (verde); cada round
**planejado mas não completo** = `▢` (cinza). Limite por sessão
= `max_per_session=4` (configurável).

**Exemplo (golden.csv, dia 2026-06-02):**
- S1 manhã: 4/4 (todos completos) → `▣ ▣ ▣ ▣`
- S2 tarde: 4/4 → `▣ ▣ ▣ ▣`
- S3 noite: 3/4 → `▣ ▣ ▣ ▢`
- (Note: 11 pomodoros total, mas S3 noite tem 3 visíveis, com 1
  implícito no "P1" seguinte.)

**Onde aparece na UI:**
- Daily Report → seção "🍅 Pomodoros Grid"
- State Dashboard → "🍅 Pomodoros (S1 manhã · S2 tarde · S3 noite)"

**Interpretação prática:** O grid é **escaneável**: você bate o
olho e vê "S1 completa, S2 completa, S3 incompleta" em < 1s. A
distribuição importa mais que o total.

**Armadilha comum:** Contar rounds `IN_PROGRESS` como completos.
Só conta `COMPLETE` (state contém "COMPLETE" em
`core/services.py:160-168`).

---

## Pomodoro Round / Config / Session

**Definição:**
- **Round:** 1 ciclo de 50min foco + 10min break (padrão PAV).
- **Config:** definições em `constants.py` (POMODORO_WORK_MIN=50,
  POMODORO_BREAK_MIN=10, POMODORO_LONG_BREAK_MIN=30 após 4 rounds).
- **Session:** S1 manhã, S2 tarde, ou S3 noite. Cada session tem
  `max_per_session=4` rounds.

**Fórmula:**
- `duration_min = work_min + break_min` = 60min (50 + 10)
- Pomodoro = `PomodoroRound(round_number, started_at, completed_at,
  is_focus_round=True)`

**Exemplo (golden.csv, dia 2026-06-02):**
- `pom_demo_00_00` → round 1, started 04:00, completed 05:00,
  duration 60min, `is_focus_round=true`
- `pom_demo_00_01` → round 2, started 05:00, completed 06:00, ...
- (4 rounds na S1 manhã = 4h total de foco + break)

**Onde aparece na UI:**
- Daily Report → Pomodoros Grid (3 sessões × 4 rounds)
- State Dashboard → KPI "Pomodoros" (total de rounds completos)

**Interpretação prática:** Pomodoro = unidade **atômica** de
foco. Você não pode "fazer meio pomodoro" — é ou 50min ou é
interrupção (que vira break, conta como pausa).

**Armadilha comum:** Cortar pomodoro no meio para "trocar de
tarefa". Isso quebra o flow state e degrada a qualidade do
foco. Pomodoro cortado não conta como completo.

---

## Produtividade (Eixo X)

**Definição:** Eixo horizontal do Plano Cartesiano. Mede **o
quanto você fez do que planejava**.

**Fórmula:** `x = (realizado / orçado) × 100`, clamp [0, 100].

**Exemplo (golden.csv, dia 2026-06-02):**
- realizado = 240min, orçado = 240min
- x = (240/240) × 100 = **100%** (borda direita do cartesiano)

**Onde aparece na UI:**
- Cartesian Plane → label "X% (Produtividade)" abaixo
- Daily Report → "Point: (x%, y%)" no header do cartesiano
- Weekly Report → coluna "X" da tabela "Posição Diária"

**Interpretação prática:** X alto = você **executou o plano**.
X baixo = você **sub-executou** (faltou tempo, energia, ou
foco). X ≥ 50% é o threshold para sair de Q3/Q4.

**Armadilha comum:** Achar que X = "horas trabalhadas brutas".
NÃO É. Se você orçou 4h e trabalhou 6h, X = 150% → clamp para
100%. X mede **aderência ao plano**, não esforço bruto.

---

## Q1 / Q2 / Q3 / Q4 (Quadrantes)

**Definição:** 4 quadrantes do Plano Cartesiano (X, Y ∈ [0, 100]).
Cada um representa um regime de produtividade.

**Fórmula:** `classify_quadrant(x, y)` em `core/budget.py`:
```
if x >= 50 and y >= 50:  return "Q1"   # top-right
if x <  50 and y >= 50:  return "Q2"   # top-left
if x <  50 and y <  50:  return "Q3"   # bottom-left
if x >= 50 and y <  50:  return "Q4"   # bottom-right
```

**Visualização ASCII:**

```
       Y (Eficiência)
       ↑
   100 ┤  Q2                Q1
       │  🟢                🏆
       │  "Otimizado       "Excelente —
       │   mas pouco        manter ritmo"
       │   output"
    50 ┤  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
       │
       │  "Crítico —        "Produtivo mas
       │   revisar          precisa
       │   sistema"         otimizar"
       │  🚨                ⚠️
    ────┼──────────────────────────→ X (Produtividade)
       0    50              100
            Q3                Q4
```

**Exemplos (golden.csv):**
- 2026-06-02: x=100, y=100 → **Q1** 🏆 (Dia Perfeito)
- 2026-06-03: x=75, y=75 → **Q1** 🏆 (ainda; só desvio leve)
- 2026-06-04: x=120(clamp 100), y=100 → **Q1** 🏆 (Hardcore, sono ruim, mas worked)

**Onde aparece na UI:**
- Daily Report → header "🚨 Q3" ou "🏆 Q1"
- Cartesian Plane → glyph do ponto: `◆` (Q1/Q2), `✗` (Q3), `▲` (Q4)
- Weekly Report → distribuição por quadrante (Q1: 4, Q2: 1, Q3: 1, Q4: 1)
- State Dashboard → não mostra quadrante diretamente, mas os KPIs
  indicam tendência

**Interpretação prática:**

| Q | Diagnóstico | Ação |
|---|-------------|------|
| Q1 🏆 | Plano executado + foco alto | Manter ritmo |
| Q2 🟢 | Foco alto, mas pouco output | Aumentar volume de trabalho |
| Q3 🚨 | Pouco output + pouco foco | Revisão urgente do sistema |
| Q4 ⚠️ | Output alto, foco baixo | Reduzir distrações |

**Armadilha comum (a principal!):**
- **Q3 NÃO é "dia perdido".** Q3 por 1 dia é normal (doença,
  interrupção). Q3 por **3+ dias consecutivos** é alarme de
  burnout. Use a **sequência**, não o quadrante isolado.
- **Q4 NÃO é "fracasso".** Q4 é "você produziu mas estava
  exausto". Frequente em HARDCORE days. Ok se for exceção.

---

## Q_HE (Quociente de Hábito Estratégico)

**Definição:** Score agregado de **aderência aos hábitos** no
período, ponderado por `weight_in_qhe` e `resistance`. Vai de
0.0 (nenhum hábito completo) a 1.0 (todos os hábitos completos
com peso máximo).

**Fórmula:** `Q_HE = Σ(weight × completed) / Σ(weight × meta)`
(aproximação; veja `core/habit_engine.py`).

**Exemplo (golden.csv, dia 2026-06-02):** `pol_demo_00_2026_06_02` →
`qhe_input=0.78`, severity `ok`, regime `MAINTAIN`.

**Onde aparece na UI:**
- Policy Decisions → coluna "QHE"
- Weekly Report → footer de cards "QHE alto/médio/baixo"

**Interpretação prática:**
- Q_HE ≥ 0.85 → "Excelente; considere PUSH"
- 0.70 ≤ Q_HE < 0.85 → "MAINTAIN"
- 0.50 ≤ Q_HE < 0.70 → "REDUCE"
- Q_HE < 0.50 → "RECOVER"

**Armadilha comum:** Inflar Q_HE completando hábitos fáceis e
ignorando os difíceis. O `weight_in_qhe` corrige isso: hábitos
de alta resistência (ex: meditar 30min) têm peso 0.7, enquanto
"ligar para família" tem peso 0.3.

---

## Severity (primary, ok, warn, crit, info, muted)

**Definição:** Vocabulário **discreto de cor** usado em todo
output do CLI. 6 valores, cada um com cor fixa via
`SEVERITY_COLOR` (`ui/components.py:87-94`).

**Fórmula:** Não há fórmula — é um enum. Mapeamento:

| Severity | Cor | Quando usar |
|----------|-----|-------------|
| `primary` | cyan | Títulos, destaques |
| `ok` | bright_green | Sucesso, dentro do plano |
| `warn` | yellow | Atenção, no limite |
| `crit` | bold red | Crítico, fora do plano |
| `info` | deep_sky_blue1 | Informativo, neutro |
| `muted` | grey58 | Secundário, histórico |

**Exemplo (golden.csv, dia 2026-06-02):** Sono 7.5h → `ok`;
Sono 6h (dia 2026-06-03) → `warn`; Sono 4h (dia 2026-06-04) → `crit`.

**Onde aparece na UI:**
- TODO output do CLI. Toda cor resolve para uma severity.

**Interpretação prática:** Se você não decora nada do sistema,
decore as 6 severities. Elas são o **código de cores universal**
do CLI.

**Armadilha comum:** Adicionar uma severity "highlight" sem
atualizar `SEVERITY_COLOR`. O sistema cai no fallback `white`
e a cor "some".

---

## Sleep Quality Score (1-10)

**Definição:** Avaliação **subjetiva** da qualidade do sono, em
escala 1-10. NÃO é medido por sensor — é declarado pelo usuário
no `metric sleep -q`.

**Fórmula:** `quality_score = 1..10`, validado por Pydantic
(`ge=1, le=10`).

**Exemplo (golden.csv):**
- 2026-06-02: Q=9 (excelente, "Sono reparador. Ciclo completo.")
- 2026-06-03: Q=6 (bom, "Dormi mais tarde (serie no streaming).")
- 2026-06-04: Q=4 (hardcore, "Deadline do relatorio trimestral.")

**Onde aparece na UI:**
- Daily Report → linha "⭐ Qualidade: 9/10"
- State Dashboard → KPI "Sono" (footer: "Q=9/10")
- Weekly Report → distribuição do sono (média, mín, máx)

**Interpretação prática:**
- Q ≥ 8 → "Excelente; sono restaurador"
- 7 ≤ Q < 8 → "Bom; funcional"
- 5 ≤ Q < 7 → "Regular; funcional mas com margem"
- 4 ≤ Q < 5 → "Hardcore; sono de emergência"
- Q < 4 → "Crítico; privação"

**Armadilha comum:** Superestimar Q para "ficar bem no relatório".
O Q é auto-reportado e a única sanidade contra inflação é a
correlação com `duration_hours` (Q 9 + 4h é inconsistente — o
sistema não checa, mas **você** sabe).

---

## Sparkline (Caracteres Unicode)

**Definição:** Visualização **inline** de tendência (1 linha, N
valores), usando os 8 caracteres de bloco Unicode
`▁▂▃▄▅▆▇█`.

**Fórmula:** `idx = int((v - min(values)) / (max - min) × 7)`,
resultado ∈ {0..7} → caractere `chars[idx]`.

**Exemplo (sparkline de 7 dias de sono):**
- valores: [7.0, 7.5, 6.0, 4.0, 7.0, 8.0, 7.5]
- min=4.0, max=8.0, span=4.0
- 4.0 → 0 → `▁` (min)
- 8.0 → 7 → `█` (max)
- resultado: `▃▅▂▁▃█▅` (8 chars para 7 valores, com normalização)

**Onde aparece na UI:**
- Weekly Report → "😴 Sono", "📈 Produtividade", "🍅 Pomodoros"
- State Dashboard → trendline de 7 dias inline

**Interpretação prática:** O sparkline é **scan-and-see**: você
olha a forma (subindo, descendo, plana) antes de ler os números.
Forma `▁▂▃▄▅▆▇█` = tendência positiva; `█▇▆▅▄▃▂▁` = negativa.

**Armadilha comum:** Comparar sparklines de grandezas diferentes.
"Sono 8h" e "Pomodoros 4" não são comparáveis no mesmo eixo.
Use cores diferentes (`sleep` vs `hardwork`) para separar.

---

## T1–T9 (Transições entre períodos)

**Definição:** As **9 transições** entre ENTRY/CORE/EXIT ao longo
do dia, cada uma com um `ritual` (HIDRATACAO, MEDITACAO, MORNING,
etc).

**Fórmula:** Não há fórmula — é convenção PAV:
- **T1** = após ENTRY manhã (HIDRATATION)
- **T2-T4** = entre rounds CORE manhã (MORNING, MORNING, MEDITATION)
- **T5** = entrada tarde (MORNING)
- **T6-T8** = entre rounds CORE tarde (AFTERNOON, AFTERNOON, MEDITATION)
- **T9** = antes do EXIT noite (SHUTDOWN_PREP)

**Exemplo (golden.csv, dia 2026-06-02):**
- T1: 08:00, HYDRATION, 15min, completed=true
- T2: 09:00, MORNING, 15min, completed=true
- T3: 10:00, MORNING, 15min, completed=true
- T4: 11:00, MEDITATION, 15min, completed=true
- T5: 12:00, MORNING, 15min, completed=true

**Onde aparece na UI:**
- Daily Report → "🔄 Transições: 5/5" (severity `ok` se todos
  completos)

**Interpretação prática:** Transições quebram o flow state de
forma **deliberada** (hidratar, meditar) para preservar energia
nas próximas 1h-2h. Sem transições, fadiga cumulativa degrada
foco após 90min.

**Armadilha comum:** Pular T4 (meditação) para "ganhar 15min".
Ganho ilusório — você perde 30min de CORE depois por fadiga.

---

## UEID (Universal Entity ID)

**Definição:** Tipo opaco (`NewType`) que garante que IDs de
entidades diferentes não se misturam. Formato canônico:
`{prefix}_{YYYYMMDD}[_sufixo]`.

**Fórmula:** `UEID = NewType("UEID", str)`. Veja `types.py`.

**Exemplos (golden.csv):**
- Sleep: `sle_2026_06_02`
- Routine: `rou_demo_00_00_2026_06_02`
- TimeBlock: `blk_demo_00_00_2026_06_02`
- Pomodoro: `pom_demo_00_00_2026_06_02`
- DayContext: `ctx_2026_06_02`
- DailyReflection: `ref_2026_06_02`
- PolicyDecision: `pol_demo_00_2026_06_02`
- Lunch: `lun_2026_06_02`
- Transicao: `trn_t1_2026_06_02`
- Journal: `jrn_demo_00_00_2026_06_02`
- Habit: `hab_beber_2l_agua`
- AjusteFino: `adj_demo_00_00_2026_06_02`
- PolicySetpoints: `set_push_demo` (não é data-bound)

**Onde aparece na UI:**
- Listas tabulares (coluna "ID")
- Mensagens de erro: "Bloco {id} não encontrado"
- JSON output (campo `"id"`)

**Interpretação prática:** O prefixo (3 letras) identifica o
tipo de entidade. Quando você ver `sle_...` sabe que é sleep;
`ctx_...` é day_context. Útil para grep em logs.

**Armadilha comum:** Conflar `sle_2026_06_02` (sleep) com
`lun_2026_06_02` (lunch) — parecidos, mas entidades diferentes.
Sempre inclua o prefixo de 3 letras.

---

## X / Y (Eixos do Cartesiano)

**Definição:** Eixos do Plano Cartesiano.

- **X = Produtividade** (horizontal). Mede aderência ao plano.
- **Y = Eficiência** (vertical). Mede foco sustentado.

**Fórmula:**
- `x = (realizado / orçado) × 100`, clamp [0, 100]
- `y = (focus_time / total_block_min) × 100`, clamp [0, 100]
  (No weekly, simplificado para `y = x`; ver
  `cli/commands/report_cmd.py:234`.)

**Exemplo (golden.csv, dia 2026-06-02):** x=100, y=100 → Q1.

**Onde aparece na UI:**
- Cartesian Plane (label "Y%" à esquerda, "X% (Produtividade)"
  em baixo)
- Daily Report header: "Point: (x%, y%)"

**Interpretação prática:**
- **X alto, Y alto** = Q1 (executou E estava focado) — **IDEAL**
- **X alto, Y baixo** = Q4 (executou MAS exausto) — comum em HARDCORE
- **X baixo, Y alto** = Q2 (focado MAS pouco output) — execução
  sub-utilizada
- **X baixo, Y baixo** = Q3 (não executou E não estava focado) —
  alerta de burnout

**Armadilha comum:** Tratar X e Y como sinônimos. **NÃO SÃO.**
X é "fiz o plano?", Y é "quando fiz, estava atento?". Em produção,
Y < X com frequência (interrupções degradam foco mas não
eliminam trabalho).

---

## Onde ler mais

- **Inventário de telas que exibem esses termos** →
  [`../01-inventario/01-telas-inventario.md`](../01-inventario/01-telas-inventario.md)
- **Componente visual do Cartesian Plane** (onde Q1-Q4 aparece) →
  [`../02-componentes/06-cartesian-plane.md`](../02-componentes/06-cartesian-plane.md)
- **Componente do Pomodoros Grid** (▢ vs ▣) →
  [`../02-componentes/05-pomodoros-grid.md`](../02-componentes/05-pomodoros-grid.md)
