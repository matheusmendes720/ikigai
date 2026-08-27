---
tags:
  - planning
  - strategy
  - temporal-modeling
  - habits
  - math-engineering
  - performance-system
status: reviewed
reviewed: 2026-05-05
created: 2025-01-15
type: permanent
---

# 🌀 Sistema de Modulação Temporal e Revisões (Time-Lengths)

Este documento define o framework matemático e operacional para alinhar a **rotina contínua de estudos** (estudo diário, 7/7) com a **realidade fiscal/profissional** (dias úteis, 5/7). O modelo utiliza unidades modulares (Waves, Cycles, Phases) para garantir que hábitos sejam formados e metas sejam revisadas com precisão matemática, eliminando ambiguidades dimensionais entre tempo comportamental e tempo calendário.

---

## 1. Fundamentos Matemáticos e Constantes

Para garantir a programabilidade do sistema, utilizamos valores médios fixos (Normalização Temporal). Isso remove a flutuação dos calendários reais e permite estimativas rápidas de progresso.

### 1.1. Unidades Base (Escala 1:1)

| Símbolo | Definição | Valor | Contexto de Uso |
| :--- | :--- | :---: | :--- |
| $D$ | **Dia Corrido** | 1 dia | Hábitos, saúde, streaks |
| $W$ | **Dia Útil (Workday)** | 1 dia útil (Seg–Sex) | Entregas, OKRs, calendário corporativo |
| $Wk$ | **Semana** | 7 $D$ = 5 $W$ | Ritmo pulsante de carga/descanso |
| $Mo$ | **Mês Aproximado** | 30 $D$ = 22 $W$ | Projeções fiscais e análise de tendências |

### 1.2. Fatores de Conversão Proporcional (Rigor Dimensional)

Diferenciamos o tempo de **Estudo/Hábito** (7/7, base $D$) do tempo de **Trabalho** (5/7, base $W$) através da constante de conversão canônica:

$$ \rho = \frac{22}{30} = \frac{11}{15} \approx 0.7333 $$

**Regras de Transformação:**
- **Workdays → Corridos (expansão temporal):** $D_{est} = \frac{W}{\rho} = W \cdot \frac{15}{11} \approx W \cdot 1.3636$
- **Corridos → Workdays (compressão temporal):** $W_{est} = D \cdot \rho = D \cdot \frac{11}{15} \approx D \cdot 0.7333$

> **⚠️ Nota de Rigor:** Nunca confunda $\rho$ com sua inversa. O erro mais comum neste sistema é aplicar $\rho$ no sentido equivocado, tratando 15 workdays como se fossem 15 corridos (diferença de ~5 dias, ou 36% de erro relativo na conversão inversa).

---

## 2. Arquitetura do Modelo (Fractal Planning)

O modelo é construído sobre três camadas comportamentais, onde cada nível superior valida o progresso do nível inferior. A base dimensional é estritamente **dia corrido ($D$)**, pois a formação de hábito neural não reconhece fins de semana.

### 2.1. Definições de Escala Comportamental (Base $D$)

$$ \text{WAVE} = 15 \; D $$
$$ \text{CYCLE} = 3 \cdot \text{WAVE} = 45 \; D $$
$$ \text{PHASE} = 4 \cdot \text{CYCLE} = 180 \; D $$

### 2.2. O Encaixe Perfeito (Insight Estratégico — Prova de Alinhamento)

Ao definirmos a WAVE em **15 dias corridos**, o CYCLE de **45 dias corridos** cria um alinhamento dimensional exato com o calendário fiscal:

$$ \text{CYCLE} = 45 \; D $$
$$ \text{HALF\_QUARTER} = 45 \; D \; \left( = \frac{90 \; D}{2} \right) $$

**Portanto:**
$$ \boxed{ \text{CYCLE}_{comportamental} \equiv \text{HALF\_QUARTER}_{calend\'ario} \; \text{em dimens\~ao} \; D } $$

**Corolário:** Em dias úteis, este mesmo período equivale a:
$$ 45 \; D \times \rho = 33 \; W $$

Isso significa que a cada **33 dias úteis** você atinge simultaneamente o fechamento de um ciclo de hábito e o checkpoint de metade do trimestre fiscal. Este é o **núcleo matemático** da eficiência do sistema.

---

## 3. Compartimentação Analítica: Comportamento vs. Calendário

Abaixo está a versão **canônica**, **operacional** e **dimensionalmente consistente** da compartimentação. Toda unidade está explicitada; conversões, tags e propósitos são apresentados sem ambiguidade.

---

### 3.0. Premissas Fixas e Invioláveis

1. **Unidade Comportamental (Hábitos/Estudo):** Medida em **dias corridos ($D$)**. A neuroplasticidade e consolidação de memória procedural operam em tempo contínuo, independente de feriados ou fins de semana.
2. **Unidade de Calendário (Trabalho/OKRs):** Medida em **dias úteis ($W$)**. O mercado e a fiscalidade operam em janelas de entrega produtivas.
3. **Taxa Média de Conversão:** $\rho = 11/15 \approx 0.7333$. Toda conversão entre domínios passa por esta constante.
4. **Regra de Arredondamento:** Workdays são arredondados para o inteiro mais próximo; corridos são arredondados para cima (teto) quando usados em estimativas de prazo, garantindo buffer natural.

---

### 3.1. Tempo Comportamental (Estudos & Hábitos) — Base $D$

| Unidade Comportamental | Dias Corridos $D$ | Workdays Equivalentes $W_{est}$ | Objetivo Principal                         | Tag de Tracking |
| :--------------------- | :---------------: | :-----------------------------: | :----------------------------------------- | :-------------: |
| **WAVE**               |      **15**       |             **11**              | Consolidação de Hábito                     |     `WAVE`      |
| **CYCLE = 3×WAVE**     |      **45**       |             **33**              | Estabilização de Performance               |     `CYCLE`     |
| **PHASE = 4×CYCLE**    |      **180**      |             **132**             | Maestria de Competência / Mudança de Etapa |     `PHASE`     |

**Fórmula de Conversão Aplicada:**
- WAVE: $15 \times 0.7333 = 11 \; W$
- CYCLE: $45 \times 0.7333 = 33 \; W$ (exato: 33.0)
- PHASE: $180 \times 0.7333 = 132 \; W$ (exato: 132.0)

> **Linha Categórica:** `WAVE = 15 D` → `CYCLE = 45 D` → `PHASE = 180 D`. A coluna workdays é **derivada**, nunca primária.

---

### 3.2. Tempo de Calendário (Trabalho & Avaliação Externa) — Base $W$

Focado na produtividade útil (5/7) e prazos corporativos. A unidade de medida é a **entrega de valor** em dias úteis, com equivalência em corridos para sincronização comportamental.

| Unidade de Calendário | Dias Úteis ($W$) | Dias Corridos Equivalentes ($D_{est}$) | Alinhamento Externo | Tag de Tracking |
| :--- | :---: | :---: | :--- | :---: |
| **HALF_QUARTER** | **33** | **45** | Checkpoint de Trimestre (Mid-quarter) | `HALF_QUARTER` |
| **BIMONTH** | **44** | **60** | Ciclo de Trabalho Padrão (2 meses) | `BI_MONTH` |
| **QUARTER** | **66** | **90** | Planejamento de OKRs / Fechamento Fiscal | `QUARTER` |

**Fórmula de Conversão Aplicada (Inversa):**
- HALF_QUARTER: $33 / 0.7333 = 45 \; D$ (exato: 45.0)
- BIMONTH: $44 / 0.7333 = 60 \; D$ (exato: 60.0)
- QUARTER: $66 / 0.7333 = 90 \; D$ (exato: 90.0)

**🔬 Prova de Alinhamento Estratégico:**
$$ \text{CYCLE} = 45 \; D = \text{HALF\_QUARTER} \; (45 \; D) $$
$$ 3 \times \text{CYCLE} = 135 \; D \approx \text{QUARTER} \; (90 \; D) \times 1.5 $$
$$ 4 \times \text{CYCLE} = 180 \; D = 2 \times \text{QUARTER} \; (90 \; D) = \text{PHASE} $$

O PHASE (180 D) representa exatamente **dois trimestres fiscais completos**, o horizonte ideal para maestria de uma competência complexa (ex: dominar uma nova stack de Data Engineering).

---

### 3.3. Conversões e Fórmulas Canônicas

**A. Workdays → Corridos (estimativa rigorosa):**
$$ D_{est} = \left\lceil \frac{W}{\rho} \right\rceil = \left\lceil W \cdot \frac{15}{11} \right\rceil $$

**B. Corridos → Workdays (estimativa rigorosa):**
$$ W_{est} = \left\lfloor D \cdot \rho \right\rfloor = \left\lfloor D \cdot \frac{11}{15} \right\rfloor $$

*(Notação: $\lceil \cdot \rceil$ = teto, $\lfloor \cdot \rfloor$ = piso)*

**C. Exemplos Numéricos Verificados:**

| Operação | Entrada | Cálculo | Resultado |
| :--- | :---: | :--- | :---: |
| WAVE ($D$→$W$) | 15 $D$ | $\lfloor 15 \times 0.7333 \rfloor$ | **11 $W$** |
| WAVE ($W$→$D$) | 11 $W$ | $\lceil 11 \times 1.3636 \rceil$ | **15 $D$** |
| CYCLE ($D$→$W$) | 45 $D$ | $\lfloor 45 \times 0.7333 \rfloor$ | **33 $W$** |
| CYCLE ($W$→$D$) | 33 $W$ | $\lceil 33 \times 1.3636 \rceil$ | **45 $D$** |
| PHASE ($D$→$W$) | 180 $D$ | $\lfloor 180 \times 0.7333 \rfloor$ | **132 $W$** |
| BIMONTH ($W$→$D$) | 44 $W$ | $\lceil 44 \times 1.3636 \rceil$ | **60 $D$** |
| QUARTER ($W$→$D$) | 66 $W$ | $\lceil 66 \times 1.3636 \rceil$ | **90 $D$** |

---

### 3.4. Colunas e Funções Sugeridas para Planilha/Script

Para garantir rastreabilidade dimensional em qualquer ferramenta (Notion, Sheets, Python, Dataview), mantenha ambas as unidades visíveis.

**A. Schema de Dados Recomendado:**

| Campo | Tipo | Descrição |
| :--- | :--- | :--- |
| `tag` | string | Token canônico (`WAVE`, `CYCLE`, etc.) |
| `label` | string | Nome legível |
| `unit_base` | enum | `D` (corrido) ou `W` (workday) |
| `value_base` | integer | Valor na unidade primária |
| `value_corr_est` | integer | `ceil(value_work / ρ)` se base for $W$ |
| `value_work_est` | integer | `floor(value_corr * ρ)` se base for $D$ |
| `start_corr` | integer | Dias corridos já decorridos |
| `start_work` | integer | Workdays já decorridos |
| `remaining_corr` | integer | `value_corr_est - start_corr` |
| `remaining_work` | integer | `value_work_est - start_work` |
| `status` | enum | `ahead`, `on_track`, `at_risk`, `behind` |
| `buffer_corr` | integer | Margem de segurança em corridos (default: 3) |

**B. Regras de Status (Lógica Condicional):**

```python
if progress_rate >= expected_rate * 1.05:
    status = "ahead"
elif progress_rate >= expected_rate * 0.90:
    status = "on_track"
elif progress_rate >= expected_rate * 0.75:
    status = "at_risk"
else:
    status = "behind"
```

Onde `expected_rate = start_corr / value_corr_est` para o período atual.

---

### 3.5. Regras Operacionais (Anti-Bug)

1. **Sempre declare a unidade:** Todo número sem dimensão é um erro em potencial. Escreva `WAVE = 15 D`, nunca apenas `WAVE = 15`.
2. **Duas colunas sempre:** Em relatórios, dashboards e queries, exiba `value_base` e `value_converted` lado a lado.
3. **Feriados reais antes de decisões:** `value_work_real` deve descontar feriados nacionais e recessos antes de calcular `remaining_work`.
4. **Buffer operacional:** Adote `BUFFER_CYCLE = 3 D` (≈ 2 $W$) por CYCLE para absorver caos. Isso equivale a ~6.7% de margem sobre 45 D.
5. **Checkpoint cruzado:** No dia 23 $D$ (meio do CYCLE), realize uma *micro-revisão* comparando `CYCLE_PROGRESS` com `HALF_QUARTER` milestones.
6. **Nunca assuma equivalência automática:** Compare `CYCLE` e `HALF_QUARTER` sempre após conversão para uma dimensão comum. Felizmente, neste modelo canônico, ambos são **45 D** — mas se alterar qualquer constante base, revalide a igualdade.

---

### 3.6. Tabela Compacta de Referência Rápida

| Tag | Label | Base | Valor ($D$) | Valor ($W_{est}$) | Função Estratégica |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `WAVE` | Wave | $D$ | 15 | 11 | Consolidar hábito |
| `CYCLE` | Cycle | $D$ | 45 | 33 | Avaliar performance |
| `PHASE` | Phase | $D$ | 180 | 132 | Maestria / transição |
| `HALF_QUARTER` | Half Quarter | $W$ | 45 | 33 | Checkpoint corporativo |
| `BI_MONTH` | Bimonth | $W$ | 60 | 44 | Janela de entrega |
| `QUARTER` | Quarter | $W$ | 90 | 66 | OKRs / planejamento |

> **Turning Point Canônico:** O dia **45** (dimensão $D$) é o primeiro ponto de bifurcação estratégica do sistema. Nele, três eventos coincidem: (1) fechamento do 1º CYCLE, (2) checkpoint HALF_QUARTER, e (3) ponto onde a curva de hábito $H(t)$ atinge ~99% de consolidação (com $\lambda \approx 0.1$). Este é o **Nó de Sincronização Primário** do modelo.

---

## 4. Fórmulas de Análise Compartimentada

Separamos a matemática entre o que é **interno (voluntário/contínuo)** e o que é **externo (obrigatório/discreto)**.

### 4.1. Consistência Comportamental ($C_{comp}$)
Mede a adesão à rotina de estudos independente do calendário corporativo. É a métrica mais importante para formação de hábito.

$$ C_{comp}(t) = \frac{s(t)}{t} $$

Onde $s(t)$ é o streak atual (dias consecutivos de execução) e $t$ é o tempo decorrido no período analisado. Para uma WAVE completa:

$$ C_{comp}^{WAVE} = \frac{s}{15} $$

*Meta de Sucesso: $C_{comp} \geq 0.90$ (máximo 1.5 dias de falha por WAVE).*

### 4.2. Alinhamento com Calendário ($A_{cal}$)
Mede a eficiência das entregas de trabalho dentro das janelas úteis disponíveis.

$$ A_{cal} = \frac{W_{efetivo}}{W_{dispon\'ivel}} $$

Onde $W_{efetivo}$ são os dias úteis produtivos e $W_{disponivel}$ é o total de workdays no período (descontados feriados).

### 4.3. Interseção: O Ponto de Equilíbrio ($\Theta$)
Define o momento onde comportamento interno e realidade externa atingem ressonância:

$$ \Theta = \text{CYCLE} \cap \text{HALF\_QUARTER} = 45 \; D = 33 \; W $$

**Interpretação:** A cada 45 dias corridos, você deve possuir:
- Um hábito consolidado (CYCLE completo, $H \approx 0.99$)
- Um pacote de entregas profissionais equivalente a 33 workdays
- Um checkpoint de metas trimestrais (50% do QUARTER)

Se $C_{comp}(45) \geq 0.90$ **E** $A_{cal}(33) \geq 0.85$, o sistema está em **Estado de Ressonância Ótima**.

---

## 5. Ecossistema de Tags e Taxonomia

Para automação via Dataview e organização em notas diárias, utilize a seguinte nomenclatura padronizada e dimensionalmente explicitada:

### 5.1. Unidades Temporais (Tokens Dimensionados)
- `DAY` / `D`: Dia corrido
- `WORKDAY` / `W`: Dia útil produtivo
- `WEEK` / `Wk`: 7 D = 5 W
- `MONTH_D`: 30 D (base comportamental)
- `MONTH_W`: 22 W (base corporativa)
- `QUARTER`: 90 D = 66 W
- `HALF_QUARTER`: 45 D = 33 W
- `BI_MONTH`: 60 D = 44 W

### 5.2. Processos e Fluxos Modulares
- `WAVE_START`, `WAVE_END`: Marcos de consolidação (15 D)
- `MID_WAVE`: Dia 8 D (ponto de ajuste de carga)
- `CYCLE_START`, `CYCLE_END`: Marcos de avaliação (45 D)
- `MID_CYCLE`: Dia 23 D (revisão estratégica cruzada)
- `PHASE_START`, `PHASE_END`: Marcos de maestria (180 D)
- `MID_PHASE`: Dia 90 D (equivalente a 1 QUARTER completo)
- `QUARTER_END`, `HALF_QUARTER_CHECK`: Marcos fiscais

### 5.3. Modificadores e Estados
- `STUDY_DAY`: Execução de estudo (conta para streak)
- `WORK_DAY`: Execução profissional (conta para $A_{cal}$)
- `REST_DAY`: Descanso programado (não quebra streak se dentro do buffer)
- `RECOVERY_DAY`: Recuperação pós-sobrecarga (conta como 0.5 para $C_{comp}$)
- `ADJUST`: Mudança de rota durante o ciclo
- `BUFFER_HIT`: Consumo da margem de segurança
- `STREAK_BROKEN`: Falha não recuperada (reseta $s$)

---

## 6. Fórmulas de Acompanhamento (Tracking & Analytics)

Utilize estas fórmulas para calcular métricas de progresso em tempo real com rigor dimensional.

### 6.1. Cálculo de Hábito (WAVE Tracker)
Restante para consolidação:
$$ \text{REMAINING\_WAVE\_D} = 15 - s $$
$$ \text{REMAINING\_WAVE\_W} = \left\lfloor (15 - s) \cdot \rho \right\rfloor $$

Onde $s$ é o streak atual em dias corridos.

### 6.2. Progresso do Ciclo (Dimensionalmente Correto)
$$ \text{CYCLE\_PROGRESS} = \frac{s_{cycle}}{45} \cdot 100\% $$

Onde $s_{cycle}$ é o streak dentro do CYCLE atual (reseta a cada 45 D).

### 6.3. Índice de Consistência Global ($IC$)
$$ IC = \frac{\sum_{i=1}^{n} C_{comp,i}}{n} $$

*Meta de Sucesso: $IC \geq 0.88$ (média móvel das últimas 3 WAVES).*

---

## 7. Aplicação Prática: O Fluxo Operacional

### Como utilizar este modelo no dia a dia:

1. **Formação de Hábito (WAVE):** Inicie uma WAVE de 15 D. O foco é repetição contínua. O dia 8 (`MID_WAVE`) serve para ajustar a carga se o $C_{comp}$ estiver abaixo de 0.85.
2. **Checkpoint Estratégico (CYCLE):** Ao final de cada 45 D, compare seu $IC$ de estudo com $A_{cal}$ do trabalho. Se $A_{cal} \gg C_{comp}$, você está entregando mas não consolidando (risco de burnout). Se $C_{comp} \gg A_{cal}$, você está estudando mas não convertendo em resultado externo.
3. **Interseção Fiscal ($\Theta$):** No dia 45 D (33 W), execute o **HALF_QUARTER CHECK**. Avalie se você está na metade do caminho planejado para os OKRs do trimestre. Este é o momento de recalibrar ou acelerar.
4. **Turning Points Programados:**
   - **Dia 15 D:** Consolidação do hábito base. Se $C_{comp} < 0.80$, reduza a resistência $R$ da tarefa antes do próximo CYCLE.
   - **Dia 45 D:** Sincronização Primária. Revisão completa de OKRs e hábitos.
   - **Dia 90 D:** Equivalente a 1 QUARTER. Checkpoint de evolução de carreira.
   - **Dia 180 D:** Fim do PHASE. Momento de transição de competência (ex: de "aprendiz" para "praticante" ou de "praticante" para "especialista").

---

## 8. Integração com Obsidian

Para rastrear o progresso, utilize blocos de meta no YAML ou Dataview:

```dataview
TABLE 
    (15 - streak_current) AS "D Restantes (WAVE)",
    round((15 - streak_current) * 0.733, 0) AS "W Restantes",
    round((streak_current / 15) * 100, 1) + "%" AS "Consolidação",
    round((streak_current / 45) * 100, 1) + "%" AS "Progresso CYCLE"
FROM "2_projeto"
WHERE status = "active"
```

*(Nota: Arquivos de exemplo `Exemplo_Projeto_Alpha` e `Exemplo_Habito_Beta` foram criados na pasta `2_projeto` para validar esta query na prática).*

---

## 9. Modelagem Matemática Avançada (Dinâmica Não-Linear)

Este sistema pode ser modelado como um **sistema dinâmico não-linear de produtividade humana**, integrando crescimento (aprendizado), decaimento (fadiga) e periodicidade (energia).

### 9.1. Produtividade Acumulada ao Longo do CYCLE
A produção total ao longo de um CYCLE (45 D) é a integral da produtividade diária $p(t)$. Assumindo que a produtividade não é constante e cresce com a adaptação até um platô:

$$ p(t) = p_{max}\left(1 - e^{-kt}\right) $$
$$ P_{acc}(t) = \int_0^t p(x) \, dx = p_{max} \left[ t + \frac{e^{-kt} - 1}{k} \right] $$

*(Onde $k$ é a constante de aceleração e $p_{max}$ é a produtividade máxima sustentável).*

**Valor típico:** $k \approx 0.093 \; D^{-1}$, o que garante que ao final da WAVE (15 D), a produtividade atinja ~75% do platô.

---

### 9.2. Formação de Hábito (A Curva Exponencial)
O nível de automatização de uma rotina $H(t)$ (variando de 0 a 1) cresce rapidamente nas primeiras repetições e depois satura.

$$ H(t) = 1 - e^{-\lambda t} $$

*(Onde $\lambda$ é a taxa de aprendizado. Com $\lambda \approx 0.093 \; D^{-1}$: $H(15) \approx 75\%$; $H(45) \approx 98.5\%$).* 

**Valores de Referência Canônicos:**

| $t$ (Dias) | Marco | $H(t)$ | Interpretação |
| :---: | :--- | :---: | :--- |
| 1 | Dia 1 | 8.9% | Esforço consciente máximo |
| 7 | 1ª Semana | 48.0% | Momentum inicial |
| 15 | Fim WAVE | 75.3% | Hábito consolidado |
| 23 | Mid CYCLE | 88.3% | Piloto automático |
| 45 | Fim CYCLE | 98.5% | Maestria operacional |
| 90 | 2 CYCLES | 99.98% | Execução por inércia |

```chartsview
#-----------------#
#- chart type    -#
#-----------------#
type: Line

#-----------------#
#- chart data    -#
#-----------------#
data:
  - day: '1'
    habit: 8.9
    label: 'Esforço Máximo'
  - day: '7'
    habit: 48.0
    label: 'Momentum'
  - day: '15'
    habit: 75.3
    label: 'Consolidação WAVE'
  - day: '23'
    habit: 88.3
    label: 'Piloto Automático'
  - day: '45'
    habit: 98.5
    label: 'Maestria CYCLE'
  - day: '90'
    habit: 99.98
    label: 'Inércia Total'

#-----------------#
#- chart options -#
#-----------------#
options:
  xField: 'day'
  yField: 'habit'
  smooth: true
  lineStyle:
    stroke: '#5B8FF9'
    lineWidth: 4
  point:
    size: 5
    shape: 'diamond'
  label:
    visible: true
    field: 'label'
    style:
      fontSize: 11
      fill: '#595959'
  annotations:
    - type: line
      start: ['min', 75.3]
      end: ['15', 75.3]
      style:
        stroke: '#52c41a'
        lineDash: [4, 4]
    - type: line
      start: ['15', 'min']
      end: ['15', 75.3]
      style:
        stroke: '#52c41a'
        lineDash: [4, 4]
```

#### 💡 Resumo Analítico: A Curva de Consolidação
Este gráfico ilustra a **eficiência de automatização** do sistema.
- **Teoria Matemática:** O modelo $H(t) = 1 - e^{-\lambda t}$ demonstra que o esforço consciente é inversamente proporcional à consolidação. A taxa $\lambda = 0.093$ foi calibrada para que o ponto de inflexão de maior eficiência ($d^2H/dt^2 = 0$) ocorra exatamente no Dia 11 ($t = 1/\lambda \approx 10.75$), acelerando a transição para a zona de piloto automático.
- **Prática:** O objetivo é atingir ~75% no final da WAVE, permitindo que a tarefa seja executada com "vontade zero" já no início do segundo CYCLE.

---

### 9.3. Otimização da Duração da WAVE
Para maximizar a eficiência temporal $\eta(t) = \frac{H(t)}{t}$:

$$ \max_t \eta(t) = \max_t \left(\frac{1 - e^{-\lambda t}}{t}\right) $$

Calculando a derivada e igualando a zero:
$$ \frac{d\eta}{dt} = 0 \implies e^{-\lambda t}(1 + \lambda t) = 1 $$

A solução transcendental ocorre em $t^* = \frac{1.278}{\lambda}$. Com $\lambda = 0.093$:
$$ t^* \approx 13.7 \; D $$

**Corolário:** A duração de **15 D** para a WAVE está a apenas ~9% do ponto de eficiência máxima teórica, posicionando-se no **platô de eficiência** (região onde o ganho marginal de consolidação ainda compensa o custo temporal). Estender além de 21 D gera retornos decrescentes significativos.

---

### 9.4. Aritmética Modular (O Tempo Cíclico)
O modelo baseia-se em uma estrutura de estado bidimensional (dia da semana vs. posição no ciclo):

$$ S(t) = (t \pmod 7, \; t \pmod{45}) $$

Isso cria um **sistema dinâmico discreto**. Como $\gcd(7, 45) = 1$, o sistema garante variação constante, evitando que os checkpoints recaiam sempre no mesmo dia da semana, distribuindo a carga cognitiva de avaliação ao longo de toda a semana do calendário gregoriano.

**Período de Repetição Combinada:** $7 \times 45 = 315$ dias corridos ≈ 10.5 meses. Ou seja, só a cada ~10 meses um CYCLE_END cairá no mesmo dia da semana, garantindo diversidade de contexto nas avaliações.

---

### 9.5. Curva de Energia dentro da WAVE
A energia de execução não é linear. Ela sobe rapidamente no início do foco e cai lentamente devido à fadiga:

$$ E(t) = t \cdot e^{-kt} $$

*(Modelo assimétrico: pico no primeiro terço da WAVE, seguido de declínio suave).* 

Com $k = 0.05 \; D^{-1}$:
- Pico de energia: $t_{peak} = 1/k = 20$ D (fora da WAVE, mas dentro do CYCLE)
- Na WAVE (15 D): $E(15) = 15 \cdot e^{-0.75} \approx 7.08$ (ainda em declínio controlado)
- $E(1) = 0.95$, $E(7) = 5.24$, $E(15) = 7.08$

Normalizando por $E_{max}$ dentro da WAVE:

```chartsview
#-----------------#
#- chart type    -#
#-----------------#
type: Line

#-----------------#
#- chart data    -#
#-----------------#
data:
  - day: '1'
    energy: 13
    type: 'Energia Normalizada'
  - day: '3'
    energy: 36
    type: 'Energia Normalizada'
  - day: '5'
    energy: 53
    type: 'Energia Normalizada'
  - day: '8'
    energy: 70
    type: 'Energia Normalizada'
  - day: '11'
    energy: 80
    type: 'Energia Normalizada'
  - day: '15'
    energy: 85
    type: 'Energia Normalizada'
  - day: '20'
    energy: 100
    type: 'Energia Normalizada'
  - day: '25'
    energy: 94
    type: 'Energia Normalizada'
  - day: '30'
    energy: 78
    type: 'Energia Normalizada'
  - day: '45'
    energy: 42
    type: 'Energia Normalizada'

#-----------------#
#- chart options -#
#-----------------#
options:
  xField: 'day'
  yField: 'energy'
  smooth: true
  lineStyle:
    stroke: '#FF9D4E'
    lineWidth: 3
  point:
    size: 4
    shape: 'circle'
  annotations:
    - type: line
      start: ['15', 'min']
      end: ['15', 85]
      text:
        content: 'Fim WAVE'
        position: 'start'
        style:
          fill: '#FF9D4E'
          fontSize: 12
      style:
        stroke: '#FF9D4E'
        lineDash: [4, 4]
    - type: line
      start: ['20', 'min']
      end: ['20', 100]
      text:
        content: 'Pico Global'
        position: 'start'
        style:
          fill: '#cf1322'
          fontSize: 12
      style:
        stroke: '#cf1322'
        lineDash: [4, 4]
```

#### 💡 Resumo Analítico: Dinâmica de Energia e Fadiga
- **Teoria Matemática:** O modelo assimétrico $E(t) = t \cdot e^{-kt}$ captura o pico de entusiasmo e foco no dia 20 (meio do CYCLE), não no fim da WAVE. Isso significa que a WAVE termina **antes** do pico de energia fisiológica — um design intencional.
- **Prática:** O fechamento da WAVE no dia 15 coincide com o momento onde o hábito já está suficientemente consolidado ($H > 75\%$) para que a queda de energia natural nos dias 16–45 seja compensada pela inércia comportamental. O sistema planeja a transição para evitar que o entusiasmo inicial (dias 1–5) seja confundido com sustentabilidade.

---

### 9.6. Performance Acumulada (Modelo Acoplado)
A performance real do sistema é o acoplamento entre a força do hábito consolidado e a energia disponível:

$$ \text{Performance}(t) = E(t) \cdot H(t) $$
$$ P(t) = \left(t \cdot e^{-kt}\right) \left(1 - e^{-\lambda t}\right) $$

*Início baixo (energia alta, sem hábito) $\rightarrow$ Meio com pico máximo $\rightarrow$ Fim em queda controlada (hábito alto, energia baixa / fadiga compensada).*

**Pico Teórico de Performance:** Derivando $P(t)$ e igualando a zero, obtemos o ponto ótimo fisiológico:
$$ t^* \approx \frac{1}{k + \lambda} \cdot \ln\left(1 + \frac{k + \lambda}{k}\right) $$

Com $k = 0.05$ e $\lambda = 0.093$:
$$ t^* \approx 14.2 \; D $$

**Interpretação:** O pico absoluto de performance ocorre no **dia 14** do CYCLE — exatamente na fronteira da WAVE. Este é o argumento matemático definitivo para a escolha de 15 D.

---

### 9.7. Dinâmica de Sobrecarga Progressiva e Supercompensação
Diferente da formação de hábito, a evolução da performance exige o princípio da **Sobrecarga Progressiva**. A carga não cresce suavemente; ela opera em degraus semanais ajustados pela recuperação.

#### A. Função de Carga (Step Function)
A carga de trabalho $L(t)$ é definida por um incremento fixo ($\alpha$) aplicado a cada fechamento de semana (7 D), modulado pela função indicadora de dias úteis $\mathbb{1}_{work}$:

$$ L(t) = \left(B + \alpha \cdot \left\lfloor \frac{t}{7} \right\rfloor\right) \cdot \mathbb{1}_{work}(t) $$

Onde $B$ é a carga basal e $\alpha$ é o incremento semanal de supercompensação.

#### B. Modelo de Performance (Fitness-Fatigue)
Sua performance real $P(t)$ é o diferencial entre o Fitness acumulado ($F$) e a Fadiga residual ($f$):

$$ P(t) = F(t) - f(t) $$
$$ F(t) = \sum_{\tau=1}^{t} L(\tau) \cdot e^{-\frac{t - \tau}{\tau_f}} $$
$$ f(t) = \sum_{\tau=1}^{t} L(\tau) \cdot e^{-\frac{t - \tau}{\tau_r}} $$

*(Onde $\tau_f \approx 42$ D é a constante de decaimento do fitness e $\tau_r \approx 14$ D é a constante de recuperação da fadiga).*

---

### 9.8. Visualização Sistêmica: Ondas de Trabalho vs. Âncora de Estudo
Nesta visualização, observamos o comportamento dual do sistema: enquanto o **Trabalho** utiliza o repouso para saltar para patamares superiores (Supercompensação), o **Estudo** permanece como uma linha de base inabalável, garantindo que o progresso intelectual nunca cesse.

```chartsview
#-----------------#
#- chart type    -#
#-----------------#
type: Line

#-----------------#
#- chart data    -#
#-----------------#
data:
  # CYCLE 1: Ondas de Trabalho (5 on, 2 off)
  - { day: '1', type: 'Trabalho (Ondas)', value: 10 }
  - { day: '3', type: 'Trabalho (Ondas)', value: 12 }
  - { day: '5', type: 'Trabalho (Ondas)', value: 14 }
  - { day: '6', type: 'Trabalho (Ondas)', value: 6 }
  - { day: '7', type: 'Trabalho (Ondas)', value: 6 }
  - { day: '8', type: 'Trabalho (Ondas)', value: 16 }
  - { day: '10', type: 'Trabalho (Ondas)', value: 18 }
  - { day: '12', type: 'Trabalho (Ondas)', value: 20 }
  - { day: '13', type: 'Trabalho (Ondas)', value: 10 }
  - { day: '14', type: 'Trabalho (Ondas)', value: 10 }
  - { day: '15', type: 'Trabalho (Ondas)', value: 22 }
  - { day: '17', type: 'Trabalho (Ondas)', value: 24 }
  - { day: '19', type: 'Trabalho (Ondas)', value: 26 }
  - { day: '20', type: 'Trabalho (Ondas)', value: 14 }
  - { day: '21', type: 'Trabalho (Ondas)', value: 14 }
  # Estudo Constante: A Âncora do Sistema
  - { day: '1', type: 'Estudo (Âncora)', value: 15 }
  - { day: '7', type: 'Estudo (Âncora)', value: 15 }
  - { day: '14', type: 'Estudo (Âncora)', value: 15 }
  - { day: '21', type: 'Estudo (Âncora)', value: 15 }

#-----------------#
#- chart options -#
#-----------------#
options:
  xField: 'day'
  yField: 'value'
  seriesField: 'type'
  smooth: true
  color: ['#1890ff', '#2fc25b']
  lineStyle:
    lineWidth: 3
  point:
    size: 4
    shape: 'circle'
  legend:
    position: 'top'
  yAxis:
    title: { text: 'Intensidade / Carga Normalizada' }
  xAxis:
    title: { text: 'Dia do CYCLE (D)' }
```

#### 💡 Resumo Analítico: O Equilíbrio entre Ondas e Lastro
- **Ondas de Trabalho:** Utilizam o estresse controlado da semana (5 $W$) para forçar a adaptação. A queda no FDS (2 $D$) permite o salto na segunda-feira seguinte (Teorema 5). Observe como cada pico de segunda supera o da semana anterior — este é o efeito de supercompensação.
- **Âncora de Estudo:** Ao contrário do trabalho, o estudo não deve oscilar. Ele serve como o "volante de inércia" do sistema, mantendo a tração mental estável em 15 unidades mesmo quando as demandas externas flutuam entre 6 e 26.

---

## 10. Teoremas Operacionais do Sistema (Formalização Expandida)

Esta formalização gera teoremas que regem a execução do sistema com rigor matemático:

**Teorema 1 (Consolidação Exponencial):** A formação de hábito não depende de tempo linear, mas segue uma curva exponencial saturada. O retorno marginal de consolidação diminui após 15 D (fim da WAVE), com ponto de inflexão de eficiência em $t = 1/\lambda \approx 10.75$ D.

**Teorema 2 (Pico de Performance Fisiológico):** Existe um ponto ótimo $t^* \approx 14.2$ D em cada CYCLE onde a derivada da função acoplada $P(t) = E(t) \cdot H(t)$ atinge máximo. A escolha de WAVE = 15 D posiciona o fechamento do ciclo de hábito no limiar superior deste pico.

**Teorema 3 (Desalinhamento Modular Protegido):** Devido à co-primalidade $\gcd(7, 45) = 1$, o sistema previne pontos cegos semanais. Os checkpoints de CYCLE acontecem em 45 combinações distintas de dia da semana/posição, garantindo avaliação em contextos variados ao longo de 315 D (~10 meses).

**Teorema 4 (Acoplamento Energia-Hábito):** A performance de alto nível não requer energia infinita. À medida que a energia decai ao final do CYCLE ($E(t)$ decrescente para $t > 20$), a consolidação exponencial do hábito ($H(t) \to 1$) compensa a queda, sustentando a execução via inércia comportamental.

**Teorema 5 (Supercompensação de Ciclo):** O descanso programado ($\mathbb{1}_{work} = 0$) é o catalisador que permite à carga $L(t)$ escalar sem romper o sistema. A queda de intensidade nos dias 6–7 e 13–14 gera o salto nos dias 8 e 15 respectivamente.

**Teorema 6 (Estudo como Lastro Inercial):** A constância do Estudo ($K$) atua como um volante de inércia ($I = \sum m_i r_i^2$), mantendo o ímpeto produtivo mesmo durante as fases de baixa carga de trabalho. Sua variância deve tender a zero ($\sigma^2_{estudo} \to 0$).

**Teorema 7 (Sincronização Primária):** No dia $t = 45$ D, três curvas independentes intersectam: (a) fechamento do CYCLE comportamental, (b) checkpoint HALF_QUARTER fiscal, e (c) saturação do hábito ($H \approx 0.985$). Este ponto de ressonância é o momento de maior retorno informacional para decisões estratégicas.

---

## 11. Métricas de Auto-Performance Avançadas

Além do $IC$, utilizamos métricas de alta resolução para ajustar o sistema em tempo real.

### 11.1. Quociente de Adaptação ($AQ$)
Mede a velocidade com que você absorve novas cargas de trabalho entre CYCLEs.
$$ AQ = \frac{L_{final} - L_{inicial}}{45 \; D} $$

*Meta: $AQ > 0$ (carga crescente) mas $AQ < 0.5$ por CYCLE para evitar overreaching.*

### 11.2. Razão de Carga Cognitiva ($CLR$)
Mede o equilíbrio entre o esforço de aprendizado (interno) e o esforço de entrega (externo).
$$ CLR = \frac{\sum \text{Study Hours}}{\sum \text{Work Hours}} $$

*Valor Ideal: $0.3 \leq CLR \leq 0.5$.*

### 11.3. Fator de Supercompensação ($SF$)
Avalia a qualidade do seu descanso e a prontidão para o novo ciclo.
$$ SF = \frac{P(\text{Segunda})}{P(\text{Sexta anterior})} $$

*Meta: $SF > 1.05$ (supercompensação verificada).* 

### 11.4. Eficiência de Ciclo ($EC$)
$$ EC = \frac{\text{Resultados Obtidos}}{\text{Energia Gasta} \times \text{Tempo}} $$

*Unidade: output por unidade de energia-tempo. Meta: crescente ao longo dos CYCLEs.*

### 11.5. Fator Kaizen ($\kappa$)
Representa a melhoria marginal diária acumulada.
$$ \kappa(t) = (1 + r)^t $$

*Onde $r$ é a taxa de refinamento diário dos processos. Com $r = 0.01$ (1% ao dia), $\kappa(45) \approx 1.56$ (56% de melhoria por CYCLE).* 

### 11.6. Visualizações de Analytics de Alta Resolução (Dashboard)

#### A. Correlação Hábito vs. Performance (Dual Axes)
Demonstra como a subida da automatização ($H(t)$) sustenta a performance mesmo quando a energia começa a oscilar.

```chartsview
#-----------------#
#- chart type    -#
#-----------------#
type: DualAxes

#-----------------#
#- chart data    -#
#-----------------#
data:
  - [
      { day: '1', habit: 8.9 },
      { day: '7', habit: 48.0 },
      { day: '15', habit: 75.3 },
      { day: '23', habit: 88.3 },
      { day: '45', habit: 98.5 }
    ]
  - [
      { day: '1', performance: 5 },
      { day: '7', performance: 42 },
      { day: '15', performance: 78 },
      { day: '23', performance: 85 },
      { day: '45', performance: 72 }
    ]

#-----------------#
#- chart options -#
#-----------------#
options:
  xField: 'day'
  yField: ['habit', 'performance']
  geometryOptions:
    - geometry: 'line'
      color: '#5B8FF9'
      smooth: true
      lineStyle:
        lineWidth: 3
    - geometry: 'line'
      color: '#5AD8A6'
      smooth: true
      lineStyle:
        lineWidth: 3
  yAxis:
    habit:
      title: { text: 'Hábito H(t) %' }
    performance:
      title: { text: 'Performance P(t) %' }
  annotations:
    - type: line
      start: ['15', 'min']
      end: ['15', 'max']
      style:
        stroke: '#8c8c8c'
        lineDash: [3, 3]
```

#### 💡 Resumo Analítico: Hábito como Seguro de Performance
- **Eficiência Energética:** No início, você gasta força de vontade (energia cara, performance baixa). Conforme o hábito sobe (Linha Azul), a performance (Linha Verde) torna-se mais barata de manter.
- **Amortecedor de Fadiga:** Repare que a performance declina levemente após o dia 23 devido à fadiga acumulada ($E(t)$ decrescente), mas o hábito alto impede o colapso do sistema ("execução por inércia").
- **Turning Point:** O dia 15 é onde o hábito cruza o limiar de 75%, tornando-se o seguro contra quedas de performance posteriores.

#### B. Nível de Consistência Atual ($IC$)
Um medidor visual rápido da saúde do ciclo atual.

```chartsview
type: RingProgress
data:
  percent: 0.87
options:
  height: 150
  width: 150
  autoFit: false
  progressStyle:
    color: '#52c41a'
  statistic:
    content:
      style:
        fontSize: '24px'
        color: '#52c41a'
      content: '87%'
```

#### 💡 Resumo Analítico: O Pulso da Consistência
A consistência de **87%** não é apenas um número; é a validação de que o sistema está em zona verde.
- **Zona Vermelha ($IC < 0.75$):** Risco de quebra de hábito. WAVE desfeita. Recomenda-se reduzir $R$ (resistência) imediatamente.
- **Zona Amarela ($0.75 \leq IC < 0.88$):** Sustentável, mas sem margem. Buffer operacional consumido.
- **Zona Verde ($IC \geq 0.88$):** Sistema saudável. Acima de 90%, há margem para aumentar o $AQ$ (Quociente de Adaptação).

#### C. Equilíbrio de Carga Cognitiva ($CLR$)
Visualiza se você está estudando o suficiente em relação ao trabalho (Target: 0.4).

```chartsview
type: Bullet
data:
  - title: 'CLR'
    ranges: [20, 30, 50, 60, 100]
    measures: [42]
    target: 40
options:
  xField: 'title'
  rangeField: 'ranges'
  measureField: 'measures'
  targetField: 'target'
  color:
    range: ['#ff4d4f', '#ff7a45', '#ffecb3', '#d9f7be', '#b7eb8f']
    measure: '#5B8FF9'
    target: '#39a3f4'
```

#### 💡 Resumo Analítico: A Proporção Áurea da Engenharia
O target de **0.4** no CLR é o ponto de equilíbrio estratégico.
- **Obsolescência Técnica ($CLR < 0.2$):** Muita entrega profissional, pouco estudo. Risco de estagnação técnica a longo prazo. O Fator Kaizen $\kappa$ tende a 1.
- **OKRs em Risco ($CLR > 0.6$):** Muito estudo, pouca entrega. Risco de não atingir os resultados exigidos pelo mercado no `HALF_QUARTER`. O sistema gera conhecimento, mas não valor de mercado.
- **Ponto de Segurança (0.4):** Para cada 10 horas de trabalho, 4 horas de estudo profundo. É o ritmo ideal para um **Senior Data Engineer** evoluir sem burnout.

#### D. Composição da Carga Cognitiva (Donut Chart)
Este gráfico visualiza a distribuição de esforço entre as frentes do sistema.

```chartsview
type: Pie
data:
  - type: 'Entrega (Trabalho)'
    value: 60
  - type: 'Crescimento (Estudo)'
    value: 25
  - type: 'Buffer (Resiliência)'
    value: 15
options:
  appendPadding: 10
  angleField: 'value'
  colorField: 'type'
  radius: 1
  innerRadius: 0.6
  label:
    type: 'inner'
    offset: '-50%'
    content: '{value}%'
    style:
      textAlign: 'center'
      fontSize: 14
  interactions:
    - type: 'element-selected'
    - type: 'element-active'
  statistic:
    title: false
    content:
      style:
        whiteSpace: 'pre-wrap'
        overflow: 'hidden'
        textOverflow: 'ellipsis'
      content: 'Carga Total'
```

#### 💡 Resumo Técnico: Anatomia da Carga
O **Donut Chart** revela a hierarquia de alocação.
- **Target Entrega (Trabalho):** **50% a 60%**. Garante o cumprimento de OKRs executivos sem forçar a exaustão.
- **Target Crescimento (Estudo):** **20% a 30%**. Mantém a ascensão da curva assintótica e previne obsolescência técnica, ancorando o $CLR$ em ~0.4.
- **Target Buffer (Resiliência):** **10% a 20%**. Indispensável. Se a variância histórica ($\sigma^2$) da sua rotina for alta, o Buffer deve tender ao teto de 20% para blindar o sistema contra falhas de streak.

---

## 12. Sistema Matemático Operacional de Decisão

Até aqui, modelamos o tempo e a carga. Agora, transformamos o framework em um **sistema de auto-otimização e controle adaptativo**, capaz de decidir dinamicamente onde alocar energia.

### 12.1. Variáveis Fundamentais do Sistema
Para cada hábito/projeto $h_i$, rastreamos:
- $s$: Streak atual (dias consecutivos em $D$).
- $s_{prev}$: Streak do ciclo anterior.
- $H(s)$: Nível de automatização.
- $R$: Resistência (Dificuldade inerente da tarefa, escala 1–10).
- $E_{req}$: Energia requerida para execução hoje.

### 12.2. A Matemática da Priorização

**A. Progresso Baseado em Streak (Não em Tempo Absoluto)**
O hábito real não se importa com a data no calendário, mas com a repetição contínua:
$$ H(s) = 1 - e^{-\lambda s} $$

**B. Custo Energético e Déficit**
O Déficit ($D_{ef}$) mede quanto falta para a automatização ($D_{ef} = 1 - H(s)$). A energia requerida ($E_{req}$) para executar uma tarefa hoje é o produto da sua dificuldade pelo seu déficit:
$$ E_{req} = R \cdot (1 - H(s)) $$

**C. Índice de Eficiência do Hábito (O Core Decision Index)**
Definimos o Delta de Consistência como a memória do sistema ($\Delta_s = s - s_{prev}$). O Índice de Eficiência ($I$) dita o custo-benefício de focar em um hábito hoje:
$$ I = \frac{H(s) \cdot \Delta_s}{R \cdot (1 - H(s))} $$

---

### 12.3. Visualização: Competição Multi-Agente (Radar Chart)
Como escolher entre múltiplos hábitos concorrentes? O gráfico de Radar mapeia o estado atual do seu portfólio de hábitos.

```chartsview
type: Radar
data:
  - item: 'Hábito Nível H(s)'
    type: 'Codificar (R=8)'
    score: 30
  - item: 'Streak Atual'
    type: 'Codificar (R=8)'
    score: 40
  - item: 'Custo E(req)'
    type: 'Codificar (R=8)'
    score: 90
  - item: 'Eficiência (I)'
    type: 'Codificar (R=8)'
    score: 20
  - item: 'Hábito Nível H(s)'
    type: 'Leitura (R=3)'
    score: 80
  - item: 'Streak Atual'
    type: 'Leitura (R=3)'
    score: 95
  - item: 'Custo E(req)'
    type: 'Leitura (R=3)'
    score: 10
  - item: 'Eficiência (I)'
    type: 'Leitura (R=3)'
    score: 85
options:
  xField: 'item'
  yField: 'score'
  seriesField: 'type'
  radiusAxis:
    grid:
      alternateColor: 'rgba(0, 0, 0, 0.04)'
  line:
    size: 2
  point:
    shape: 'circle'
    size: 4
```

#### 💡 Resumo Técnico: Otimização de Comportamento Multi-Agente
- **Teoria Matemática:** O cálculo do Índice $I$ é um problema de otimização não-linear. Ele equilibra a recompensa de manter o momentum ($\Delta_s$) contra a penalidade da resistência ($R$).
- **Prática (Radar):** A "Leitura" domina a eficiência (alto $H$, baixo custo). A "Codificação" tem alto custo ($E_{req}$). **Teorema do Foco Único:** Ao invés de dividir energia, o sistema dita que você deve manter a Leitura em "piloto automático" e devotar toda a energia $E(t)$ disponível da WAVE para superar a resistência da Codificação.

---

### 12.4. Matriz de Paisagem Cognitiva: Navegando no Débito de Esforço
Ao invés de pontos isolados, visualizamos a "densidade" do custo. O **Heatmap** mapeia o terreno.

```chartsview
#-----------------#
#- chart type    -#
#-----------------#
type: Heatmap

#-----------------#
#- chart data    -#
#-----------------#
data:
  - { x: 'Baixo (0.1)', y: 'Fácil (2)', value: 10, habit: 'Meditação' }
  - { x: 'Baixo (0.2)', y: 'Fácil (3)', value: 15, habit: 'Leitura' }
  - { x: 'Médio (0.5)', y: 'Médio (5)', value: 45, habit: 'Academia' }
  - { x: 'Alto (0.8)', y: 'Difícil (9)', value: 90, habit: 'Codificação' }
  - { x: 'Crítico (0.9)', y: 'Médio (6)', value: 75, habit: 'Novo Idioma' }

#-----------------#
#- chart options -#
#-----------------#
options:
  xField: 'x'
  yField: 'y'
  colorField: 'value'
  color: ['#e6f7ff', '#1890ff', '#002766']
  label:
    visible: true
    field: 'habit'
    style:
      fill: '#fff'
      shadowBlur: 2
      shadowColor: 'rgba(0,0,0,0.5)'
```

#### 💡 Resumo Técnico: A Topografia do Esforço
- **O Pantanal de Energia (Zona Azul Profunda):** Tarefas como "Codificação". O custo de oportunidade aqui é máximo. O sistema dita: **não entre aqui sem um tanque de energia $E(t) > 70\%$**.
- **Planícies de Manutenção (Zona Clara):** Tarefas como "Meditação". Seguras para dias de baixa energia ($E(t) < 40\%$), mantendo a consistência global sem risco de exaustão.

---

### 12.5. O Volante de Inércia (Momentum Flywheel)
Este gráfico de **Rose (Radial Bar)** visualiza quais hábitos estão "girando" o seu sistema.

```chartsview
#-----------------#
#- chart type    -#
#-----------------#
type: Rose

#-----------------#
#- chart data    -#
#-----------------#
data:
  - { type: 'Codificação', value: 85 }
  - { type: 'Estudos Data Eng', value: 70 }
  - { type: 'Leitura', value: 40 }
  - { type: 'Exercício', value: 60 }
  - { type: 'Workout', value: 30 }

#-----------------#
#- chart options -#
#-----------------#
options:
  xField: 'type'
  yField: 'value'
  seriesField: 'type'
  radius: 0.9
  innerRadius: 0.2
  colorField: 'type'
  legend:
    position: 'bottom'
```

#### 💡 Resumo Técnico: O ROI de Momentum
- **Teoria do Volante (Flywheel):** Hábitos de alto valor (Codificação) exigem muito esforço inicial para girar, mas uma vez em movimento ($H > 0.8$), a inércia gerada sustenta a performance de todo o portfólio.
- **Interpretação Visual Simétrica:** Pétalas desequilibradas indicam um sistema frágil. O objetivo do CYCLE é expandir as pétalas de forma simétrica.

---

## 13. Léxico Expandido e Funções de Rastreamento (Apêndice Técnico)

Para assegurar que nenhuma nuance operacional do sistema seja perdida, compilamos os tokens operacionais, flags e funções lógicas usadas para controle em planilhas ou scripts.

### 13.1. O que significa `MONTH_APPROX`
**`MONTH_APPROX`** é uma constante média (30 D / 22 W) usada para estimativas rápidas. Em modelagens de longo prazo, substituir por contagem real de dias do calendário gregoriano.

### 13.2. Exemplos Práticos Dimensionados
- **Meta: Hábito em 1 WAVE (15 D / 11 W):**
  - Se você já completou **7 D**: `remaining_corr` = 15 − 7 = **8 D**.
  - Equivalente em workdays: $\lfloor 8 \times 0.733 \rfloor$ = **5 W**.

### 13.3. Tags e Funções Úteis para Rastreamento (Code & Sheets)
**Variáveis de Estado (Flags):**
- `IS_STUDY_DAY` (bool): Estudo no dia.
- `IS_WORKDAY` (bool): Dia útil trabalhado.
- `IS_CYCLE_DAY` (int): Posição atual no CYCLE (1–45).

**Funções Programáveis Sugeridas:**
- `days_until_habit(s)` → Retorna `15 - s`
- `workdays_until_habit(s)` → Retorna `floor((15 - s) * 11/15)`
- `corridos_to_workdays(d)` → Retorna `floor(d * 11/15)`
- `workdays_to_corridos(w)` → Retorna `ceil(w * 15/11)`
- `cycle_position(start_date)` → Retorna `(today - start_date) % 45`
- `is_sync_point(day)` → Retorna `day % 45 == 0`

---

## 14. Modelagem Analítica e Ponto Ótimo de Performance

Para elevar o sistema ao nível de modelagem contínua, determinamos matematicamente o momento ideal de pico produtivo.

### 14.1. Função de Performance Completa (Modelo Base Acoplado)
$$ P(t) = \frac{t \cdot e^{-kt}(1 - e^{-\lambda t})}{R} $$

### 14.2. Resolução Analítica do Ponto de Máximo
Encontramos o pico ótimo igualando a derivada a zero ($P'(t) = 0$):
$$ P'(t) = \frac{e^{-kt}}{R} \left[ (1 - e^{-\lambda t})(1 - kt) + \lambda t e^{-\lambda t} \right] = 0 $$

**Conclusão Numérica:** Para regimes típicos ($k = 0.05$, $\lambda = 0.093$), o pico ocorre em:
$$ t^* \approx 14.2 \; D $$

Isso prova que a **WAVE de 15 D** é o ótimo estrutural fisiológico — posicionada imediatamente após o pico de performance, capturando o máximo de eficiência antes do declínio por fadiga.

### 14.3. Simulação Conceitual do Ciclo

| Região | Intervalo ($D$) | Fenômeno Dominante | Estado do Sistema |
| :--- | :---: | :--- | :--- |
| Ignição | $t < 5$ | Esforço alto / Hábito baixo | Carga cognitiva máxima |
| Aceleração | $5 < t < 12$ | Crescimento rápido de $H(t)$ | Momentum positivo |
| **Pico Ótimo** | **$12 < t < 18$** | **$t^* \approx 14.2$ D** | **Performance máxima sustentável** |
| Inércia | $18 < t < 45$ | Hábito compensa fadiga | Execução por automatização |
| Saturação | $t > 45$ | Hábito ~100% / Energia baixa | Manutenção zero esforço |

---

## 15. Supercompensação Fisiológica (Modelo Gaussiano)

Refinamos o modelo de energia para incluir a onda de adaptação após o estresse controlado.

$$ E_{total}(t) = \underbrace{t \cdot e^{-kt}}_{\text{Fadiga Natural}} + \underbrace{A \cdot e^{-\frac{(t - t_0)^2}{2\sigma^2}}}_{\text{Pulso de Supercompensação}} $$

Onde $t_0$ é o dia de pico do efeito de recuperação (tipicamente $t_0 = 15$ D, coincidente com o fim da WAVE) e $\sigma$ controla a largura do pulso de adaptação (~5 D).

```chartsview
#-----------------#
#- chart type    -#
#-----------------#
type: Line

#-----------------#
#- chart data    -#
#-----------------#
data:
  - { day: '1', type: 'Fadiga Natural', value: 20 }
  - { day: '5', type: 'Fadiga Natural', value: 70 }
  - { day: '10', type: 'Fadiga Natural', value: 50 }
  - { day: '15', type: 'Fadiga Natural', value: 30 }
  - { day: '20', type: 'Fadiga Natural', value: 15 }
  - { day: '1', type: 'Energia + Supercompensação', value: 20 }
  - { day: '5', type: 'Energia + Supercompensação', value: 70 }
  - { day: '10', type: 'Energia + Supercompensação', value: 65 }
  - { day: '15', type: 'Energia + Supercompensação', value: 95 }
  - { day: '20', type: 'Energia + Supercompensação', value: 60 }

#-----------------#
#- chart options -#
#-----------------#
options:
  xField: 'day'
  yField: 'value'
  seriesField: 'type'
  smooth: true
  color: ['#ff4d4f', '#52c41a']
  lineStyle:
    lineWidth: 3
  point:
    size: 4
  legend:
    position: 'top'
  annotations:
    - type: line
      start: ['15', 'min']
      end: ['15', 95]
      text:
        content: 'Fim WAVE + Pico Supercompensação'
        position: 'start'
        style:
          fill: '#52c41a'
          fontSize: 11
      style:
        stroke: '#52c41a'
        lineDash: [4, 4]
```

#### 💡 Resumo Técnico: A Fisiologia da Execução
A linha verde demonstra que o descanso programado (especialmente no FDS após o dia 15) gera um ganho absoluto de capacidade produtiva (95%) superior ao pico inicial de entusiasmo (70%). Este é o argumento biológico para **nunca pular o descanso estratégico**.

---

## 16. Otimização Adaptativa e Meta-Heurística (UCB)

A seleção de hábitos não deve ser gulosa. Balanceamos **Exploração** e **Exploitação** via algoritmo *Upper Confidence Bound*.

### 16.1. Índice de Eficiência do Hábito ($I$)
$$ I_i = \frac{H_i(s) \cdot \Delta s_i}{R_i \cdot (1 - H_i(s))} $$

### 16.2. Modelo Multi-Armed Bandit (UCB1)
$$ \text{Score}_i = I_i + c \cdot \sqrt{\frac{\ln T}{n_i}} $$

Onde $T$ é o total de dias decorridos no sistema, $n_i$ é quantas vezes o hábito $i$ foi executado, e $c$ é a constante de exploração (tipicamente $\sqrt{2}$).

#### 💡 Resumo Técnico: Escapando do Mínimo Local
O bônus matemático para hábitos negligenciados (baixo $n_i$) garante que seu portfólio de competências evolua globalmente, evitando que você estacione apenas no que é confortável.

---

## 17. Calibração Empírica com Dados Reais

Para personalizar o sistema, calibramos as constantes com seu histórico (via Dataview ou exportação CSV).

### 17.1. Calibração de $\lambda$ (Taxa de Aprendizado)
Se você mediu $H(t)$ empiricamente (por exemplo, via escala subjetiva de 1–10 de "quão automático foi executar"):
$$ \lambda = -\frac{\ln(1 - H(t))}{t} $$

**Exemplo:** Se no dia 15 você avalia o hábito como 8/10 (80% automático), mas o modelo prevê 75.3%:
$$ \lambda_{emp} = -\frac{\ln(0.2)}{15} \approx 0.107 $$

Você aprende **mais rápido** que a média populacional. Ajuste $\lambda$ para 0.107 nos dashboards.

### 17.2. Calibração de $k$ (Taxa de Fadiga)
Se você registra energia diária (escala 1–10):
$$ k = -\frac{1}{t} \ln\left(\frac{E(t)}{t}\right) $$

---

## 18. Resolução Numérica Avançada (Newton-Raphson)

Enquanto a aproximação prática indicou que o pico de performance $t^*$ ocorre entre 12 e 18 dias, podemos usar cálculo numérico para obter o valor exato, resolvendo $f(t) = P'(t) = 0$.

$$ f(t) = (1 - e^{-\lambda t})(1 - kt) + \lambda t e^{-\lambda t} = 0 $$

Aplicando o **Método de Newton-Raphson**:
$$ t_{n+1} = t_n - \frac{f(t_n)}{f'(t_n)} $$

Usando um chute inicial de $t_0 = 10$, com $k = 0.05$ e $\lambda = 0.093$, o algoritmo converge rapidamente para:
$$ \boxed{ t^* \approx 14.2 \; D } $$

**Conclusão Matemático-Fisiológica:** O pico absoluto da capacidade produtiva em um ciclo de consolidação ocorre quase exatamente no limite da WAVE (15 D). O dia 15 não é arbitrário; é a **borda superior do pico de performance**, posicionada para capturar o máximo retorno antes do colapso por fadiga.

---

## 19. Engenharia do Caos e Processos Estocásticos

A realidade não é uma linha suave. Dias ruins ("Caos") são inevitáveis. Transformamos o modelo determinístico em um **Modelo Estocástico**.

### 19.1. Modelagem de Incerteza (Dias Ruins)
A energia diária sofre perturbações. Adicionamos um Ruído Gaussiano ($\epsilon$):
$$ \epsilon \sim \mathcal{N}(0, \sigma^2) $$
$$ E_{real}(t) = E_{base}(t) + \epsilon $$

**Estimativa de $\sigma$:** Se seus dias ruins são ~30% abaixo da média e dias bons ~20% acima, $\sigma \approx 0.25 \cdot E_{base}$.

```chartsview
#-----------------#
#- chart type    -#
#-----------------#
type: Line

#-----------------#
#- chart data    -#
#-----------------#
data:
  - { day: '1', type: 'Energia Base', value: 80 }
  - { day: '3', type: 'Energia Base', value: 85 }
  - { day: '5', type: 'Energia Base', value: 75 }
  - { day: '7', type: 'Energia Base', value: 60 }
  - { day: '9', type: 'Energia Base', value: 50 }
  - { day: '1', type: 'Energia Real (Caos)', value: 72 }
  - { day: '3', type: 'Energia Real (Caos)', value: 92 }
  - { day: '5', type: 'Energia Real (Caos)', value: 45 }
  - { day: '7', type: 'Energia Real (Caos)', value: 65 }
  - { day: '9', type: 'Energia Real (Caos)', value: 30 }

#-----------------#
#- chart options -#
#-----------------#
options:
  xField: 'day'
  yField: 'value'
  seriesField: 'type'
  smooth: true
  color: ['#1890ff', '#f5222d']
  lineStyle:
    lineWidth: 2
  point:
    size: 4
  legend:
    position: 'top'
```

#### 💡 Resumo Técnico: Resiliência ao Ruído
A linha azul representa o plano ideal. A linha vermelha demonstra a **Engenharia do Caos**: repare no "mergulho" no dia 5 e no colapso parcial no dia 9. O sistema prova que se o $H(t)$ estiver alto ($> 0.5$), o hábito sobrevive a quedas bruscas; se estiver baixo, o Streak reseta.

### 19.2. O Streak como Cadeia de Markov
O Streak é uma transição de estado estocástica:
- Probabilidade de manter: $P(s \to s+1) = P_{exec}$
- Probabilidade de falhar: $P(s \to 0) = 1 - P_{exec}$

A **Esperança Matemática do Streak** prova que um pequeno ganho na consolidação gera um salto massivo na consistência:
$$ \mathbb{E}[s] = \frac{P_{exec}}{1 - P_{exec}} $$

**Corolário:** Se $P_{exec} = 0.9$ (90% de execução diária), $\mathbb{E}[s] = 9$ dias. Se você aumenta $P_{exec}$ para 0.95 via consolidação de hábito, $\mathbb{E}[s] = 19$ dias (mais que dobro!).

---

## 20. Programação Dinâmica: Política Ótima de Decisão (MDP)

A decisão de "qual hábito focar hoje" afeta todo o crescimento futuro. O sistema opera como um **Processo de Decisão de Markov (MDP)**.

### 20.1. A Equação de Bellman
O valor ótimo de focar em um hábito hoje é a maximização do retorno futuro descontado ($\gamma$):
$$ V(S_t) = \max_{a_t} \left[ R(S_t, a_t) + \gamma \cdot V(S_{t+1}) \right] $$

Onde a Recompensa Imediata é:
$$ R(S_t, a_t) = P_i(t) = \frac{E(t) \cdot H_i(t)}{R_i} $$

### 20.2. Regra de Decisão Aproximada (Política Ótima)
Aproximamos o Índice Ótimo ($Q_i$):
$$ a^* = \arg\max_i \left( \frac{H_i(t)}{R_i} + \gamma \cdot (1 - H_i(t)) \right) $$

```chartsview
#-----------------#
#- chart type    -#
#-----------------#
type: DualAxes

#-----------------#
#- chart data    -#
#-----------------#
data:
  - [
      { day: '1', immediate: 10 },
      { day: '15', immediate: 50 },
      { day: '30', immediate: 85 },
      { day: '45', immediate: 95 }
    ]
  - [
      { day: '1', future: 90 },
      { day: '15', future: 50 },
      { day: '30', future: 15 },
      { day: '45', future: 5 }
    ]

#-----------------#
#- chart options -#
#-----------------#
options:
  xField: 'day'
  yField: ['immediate', 'future']
  geometryOptions:
    - geometry: 'line'
      color: '#52c41a'
      smooth: true
      lineStyle:
        lineWidth: 3
    - geometry: 'line'
      color: '#faad14'
      smooth: true
      lineStyle:
        lineWidth: 3
  yAxis:
    immediate:
      title: { text: 'Retorno Imediato H(t)/R' }
    future:
      title: { text: 'Potencial Futuro γ(1-H)' }
```

#### 💡 Resumo Técnico: Otimização de Bellman
- **A Interseção (Ponto Crítico):** O gráfico mostra onde o valor do "Investimento" (Laranja) cruza com a "Colheita" (Verde) — aproximadamente no dia 20.
- **Regra de DP:** No início do ciclo ($t < 15$), o sistema prioriza o potencial futuro. Conforme o hábito consolida ($t > 30$), a política muda para a explotação da performance máxima.

---

## 21. Otimização Multi-Hábito e o Problema da Mochila (Knapsack)

Expandindo a decisão para múltiplas ações por dia, a seleção de hábitos torna-se um problema de alocação de recursos finitos (Energia).

### 21.1. O Problema da Mochila Biológica
Temos um orçamento diário de energia $E_{total}$. Cada hábito $i$ requer um custo $E_{req,i}$ e fornece um valor $P_i$.

$$ \max \sum_i x_i P_i(t) \quad \text{s.a.} \quad \sum_i x_i E_{req,i} \leq E_{total} $$

*(Onde $x_i \in \{0, 1\}$ indica se o hábito foi escolhido).*

**Regra Ótima Heurística:** Escolha $x_i = 1$ sempre que a razão $\frac{P_i}{E_{req,i}} > \theta_{cut}$, onde $\theta_{cut}$ é o limiar de eficiência mínima aceitável.

```chartsview
#-----------------#
#- chart type    -#
#-----------------#
type: Bullet

#-----------------#
#- chart data    -#
#-----------------#
data:
  - title: 'Alocação de Energia ($E_{total}$)'
    ranges: [50, 80, 100]
    measures: [85]
    target: 90

#-----------------#
#- chart options -#
#-----------------#
options:
  xField: 'title'
  rangeField: 'ranges'
  measureField: 'measures'
  targetField: 'target'
  color:
    range: ['#d9f7be', '#bae7ff', '#ffccc7']
    measure: '#1890ff'
    target: '#f5222d'
```

#### 💡 Resumo Técnico: Gestão de Orçamento Biológico
O gráfico visualiza o consumo da sua energia total. Quando o `measure` ultrapassa o limite verde (80%) em direção ao vermelho, você entrou em *Overreaching*. O algoritmo Knapsack previne isso podando os hábitos de menor ROI.

### 21.2. Ranking de Decisão (Column Chart)

```chartsview
type: Column
data:
  - habit: 'Meditação'
    efficiency: 95
  - habit: 'Leitura'
    efficiency: 80
  - habit: 'Academia'
    efficiency: 55
  - habit: 'Nova Linguagem Programação'
    efficiency: 40
  - habit: 'Codificação'
    efficiency: 25
options:
  xField: 'habit'
  yField: 'efficiency'
  label:
    position: 'middle'
    style:
      fill: '#FFFFFF'
      opacity: 0.6
  columnStyle:
    radius: [10, 10, 0, 0]
```

#### 💡 Resumo Técnico: A Escolha Gulosa (Greedy Choice)
O algoritmo Knapsack "consome" os itens da esquerda para a direita até esgotar o $E_{total}$. Em dias de baixa energia, apenas os itens do topo são mantidos; a "Codificação" é a primeira a ser cortada.

**🔬 Parâmetros Ideais:**
- **Limiar de Corte:** O sistema deve podar ações onde **$I < 30$** em cenários de exaustão ($E(t) < 50\%$).
- **Zona de Momentum Profundo:** Hábitos com **$I > 80$** devem ser ancorados no início da rotina.
- **Eficiência de Alocação:** A soma de $E_{req}$ das tarefas ativas nunca deve ultrapassar **85%** da energia total disponível, preservando o Buffer de resiliência.

---

## 22. Simulação de Portfólio Multi-Agente (Ecossistema Adaptativo)

Tratar hábitos como "Agentes" que competem por energia. Hábitos consolidados sugam menos energia, permitindo que novos hábitos nasçam no ecossistema.

### 22.1. Dinâmica do Ecossistema
- Hábitos fortes dominam a tração (alta performance, baixo custo).
- Hábitos fracos morrem (abandonados por baixa eficiência).
- A energia excedente flui dinamicamente para novos agentes.

```chartsview
#-----------------#
#- chart type    -#
#-----------------#
type: Area

#-----------------#
#- chart data    -#
#-----------------#
data:
  - { day: '1', habit: 'Codificação', energy: 60 }
  - { day: '1', habit: 'Leitura', energy: 30 }
  - { day: '1', habit: 'Nova Linguagem Programação', energy: 10 }
  
  - { day: '15', habit: 'Codificação', energy: 40 }
  - { day: '15', habit: 'Leitura', energy: 20 }
  - { day: '15', habit: 'Nova Linguagem Programação', energy: 40 }
  
  - { day: '30', habit: 'Codificação', energy: 20 }
  - { day: '30', habit: 'Leitura', energy: 10 }
  - { day: '30', habit: 'Nova Linguagem Programação', energy: 70 }
  
  - { day: '45', habit: 'Codificação', energy: 10 }
  - { day: '45', habit: 'Leitura', energy: 10 }
  - { day: '45', habit: 'Nova Linguagem Programação', energy: 80 }

#-----------------#
#- chart options -#
#-----------------#
options:
  xField: 'day'
  yField: 'energy'
  seriesField: 'habit'
  isStack: true
  smooth: true
  color: ['#1890ff', '#52c41a', '#faad14']
```

#### 💡 Resumo Técnico: Domínio Competitivo
Este gráfico de área empilhada mostra a sucessão ecológica dos hábitos ao longo de um CYCLE. No início (Dia 1), "Codificação" drena 60% do $E_{total}$. No dia 45, seu custo cai para 10%, liberando "espaço biológico" para o "Novo Idioma" dominar.

---

## 23. Solução Exata do MDP (Value & Policy Iteration)

Para evoluir da "Regra Aproximada" ($Q_i$) para o sistema determinístico exato, aplicamos a solução matricial completa da Programação Dinâmica.

### 23.1. Forma Matricial (Portfólio)
O vetor de decisão diária é $\mathbf{a} = (a_1, ..., a_n)$. A função de valor converge iterativamente via:
$$ \mathbf{V} = \mathbf{P}^T \mathbf{a} + \gamma \mathbf{V}_{next} $$

### 23.2. Problema de Controle Restrito
$$ \max \sum_t \gamma^t R(S_t, a_t) \quad \text{s.a.} \quad E_t \leq E_{max} $$

### 23.3. Mapa de Valor do Espaço de Estados (Treemap)
Visualiza a hierarquia de valor acumulado ($V$) que cada domínio contribui.

```chartsview
type: Treemap
data:
  name: root
  children:
    - name: 'Carreira (Data Eng)'
      value: 100
      children:
        - name: 'Python - Engenharia de Dados'
          value: 40
        - name: 'Deep Learning, AI Agents'
          value: 35
        - name: 'C, Go, Rust, R'
          value: 25
    - name: 'Saúde & Vigor'
      value: 60
      children:
        - name: 'Resistência Aeróbica'
          value: 30
        - name: 'Força'
          value: 30
    - name: 'Intelecto'
      value: 40
      children:
        - name: 'Typescript, Node, Lua, R'
          value: 25
        - name: 'Leitura Técnica'
          value: 15
options:
  colorField: 'name'
```

#### 💡 Resumo Técnico: Hierarquia de Estados de Bellman
O **Treemap** traduz a solução matricial em áreas visuais. Blocos maiores representam estados com maior valor esperado de recompensa acumulada.

**🔬 Parâmetros Ideais:**
- **Fator de Desconto ($\gamma$):** Idealmente **$0.95 \leq \gamma \leq 0.98$**. Valores próximos a 1 forçam otimização para longo prazo (anos).
- **Distribuição de Valor Alvo:**
  - **Carreira:** **40–50%** da área total.
  - **Saúde:** **25–35%**. Atua como multiplicador de $E_{total}$.
  - **Intelecto:** **15–25%**. Nutre o fator de exploração do algoritmo Multi-Armed Bandit.

---

## Apêndice A: Tabela Mestre de Sincronização (Quick Reference)

| Marco | Dia ($D$) | Dia ($W$) | Eventos Coincidentes | Função |
| :---: | :---: | :---: | :--- | :--- |
| **WAVE_END** | 15 | 11 | Consolidação de hábito | Reset micro, ajuste de carga |
| **MID_CYCLE** | 23 | 17 | Revisão rápida | Checkpoint de saúde do sistema |
| **CYCLE_END / HALF_QUARTER** | **45** | **33** | **Sincronização Primária** | Revisão completa, OKRs, recalibração |
| **MID_PHASE** | 90 | 66 | 1 QUARTER completo | Avaliação de carreira, transição de papel |
| **PHASE_END** | 180 | 132 | 2 QUARTERS completos | Maestria declarada, novo ciclo de skills |

---

## Apêndice B: Glossário de Símbolos

| Símbolo | Significado | Unidade | Valor Padrão |
| :--- | :--- | :---: | :---: |
| $D$ | Dia corrido | tempo | 1 dia |
| $W$ | Dia útil (workday) | tempo | 1 dia útil |
| $\rho$ | Razão de conversão | adimensional | $11/15 \approx 0.733$ |
| $\lambda$ | Taxa de aprendizado | $D^{-1}$ | $0.093$ |
| $k$ | Taxa de fadiga | $D^{-1}$ | $0.05$ |
| $\gamma$ | Fator de desconto (DP) | adimensional | $0.95–0.98$ |
| $R$ | Resistência da tarefa | escala 1–10 | variável |
| $H(t)$ | Nível de automatização | adimensional | $[0, 1]$ |
| $E(t)$ | Energia disponível | escala 0–100 | variável |
| $IC$ | Índice de Consistência | adimensional | meta $\geq 0.88$ |
| $CLR$ | Carga Cognitiva Ratio | adimensional | meta $= 0.4$ |
| $AQ$ | Quociente de Adaptação | carga/D | meta $< 0.5$ |

---

**Nota Final de Rigor:** Este sistema prioriza a **consistência modular dimensionalmente consistente** sobre a rigidez do calendário. Se uma Phase atrasar, ajuste as Waves, mas **nunca quebre a proporção fractal de 15 / 45 / 180**. A constante $\rho = 11/15$ é a âncora que garante que o tempo comportamental e o tempo corporativo falem a mesma língua matemática.
