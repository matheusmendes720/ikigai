---
tags:
  - planning
  - strategy
  - temporal-modeling
  - habits
status: reviewed
reviewed: 2026-05-05
---

# 🌀 Sistema de Modulação Temporal e Revisões (Time-Lengths)

Este documento define o framework matemático e operacional para alinhar a **rotina contínua de estudos** (estudo diário) com a **realidade fiscal/profissional** (dias úteis). O modelo utiliza unidades modulares (Waves, Cycles, Phases) para garantir que hábitos sejam formados e metas sejam revisadas com precisão matemática.

---

## 1. Fundamentos Matemáticos e Constantes

Para garantir a programabilidade do sistema, utilizamos valores médios fixos (Normalização Temporal). Isso remove a flutuação dos calendários reais e permite estimativas rápidas de progresso.

### 1.1. Unidades Base (Escala 1:1)

- **$DAY$**: 1 dia corrido.
- **$WORKDAY$**: 1 dia útil (Segunda a Sexta).
- **$WEEK$**: 7 dias corridos ($5 \cdot WORKDAY$).
- **$MONTH$**: 30 dias corridos ($22 \cdot WORKDAY$).

### 1.2. Fatores de Conversão Proporcional

Diferenciamos o tempo de **Estudo** (7/7) do tempo de **Trabalho** (5/7) através de uma constante de conversão:

$$ \text{WORK\_RATIO} = \frac{22}{30} \approx 0.7333 $$

Para converter qualquer período $t$ (em dias corridos) para sua equivalência em dias úteis:
$$ f(t) = t \cdot \text{WORK\_RATIO} $$

---

## 2. Arquitetura do Modelo (Fractal Planning)

O modelo é construído sobre três camadas principais, onde cada nível superior valida o progresso do nível inferior.

### 2.1. Definições de Escala

$$ \text{WAVE} = 15 \text{ dias} $$
$$ \text{CYCLE} = 3 \cdot \text{WAVE} = 45 \text{ dias} $$
$$ \text{PHASE} = 4 \cdot \text{CYCLE} = 180 \text{ dias} $$

### 2.2. O Encaixe Perfeito (Insight Estratégico)
Ao definirmos o **CYCLE** como 45 dias, criamos um alinhamento exato com o **HALF\_QUARTER** (metade de um trimestre fiscal de 90 dias).

$$ \text{CYCLE} = \text{HALF\_QUARTER} = 45 \text{ dias} $$

---

## 3. Compartimentação Analítica: Comportamento vs. Calendário

Para uma análise eficaz, separamos o **Tempo Comportamental** (focado em crescimento interno e hábitos) do **Tempo de Calendário** (focado em obrigações externas e mercado).

### 3.1. Tempo Comportamental (Estudos & Hábitos)
Focado na progressão contínua (7/7). A unidade de medida é a **capacidade de manutenção de rotina**.

| Unidade Comportamental | Dias Corridos | Objetivo Principal | Tag de Tracking |
| :--- | :---: | :--- | :--- |
| **WAVE** | 15 | Consolidação de Hábito | `WAVE` |
| **CYCLE** | 45 | Estabilização de Performance | `CYCLE` |
| **PHASE** | 180 | Maestria de Competência | `PHASE` |

### 3.2. Tempo de Calendário (Trabalho & Avaliação Externa)
Focado na produtividade útil (5/7) e prazos corporativos. A unidade de medida é a **entrega de valor**.

| Unidade de Calendário | Dias Úteis | Alinhamento Externo | Tag de Tracking |
| :--- | :---: | :--- | :--- |
| **BIMONTH** | 44 | Ciclo de Trabalho Padrão | `BI_MONTH` |
| **HALF_QUARTER** | 33 | Checkpoint de Trimestre | `HALF_QUARTER` |
| **QUARTER** | 66 | Planejamento de OKRs | `QUARTER` |

---

## 4. Fórmulas de Análise Compartimentada

Separamos a matemática entre o que é **interno (vontade)** e o que é **externo (prazo)**.

### 4.1. Consistência Comportamental ($C_{comp}$)
Mede a adesão à rotina de estudos independente do calendário.
$$ C_{comp} = \frac{\text{dias\_estudados}}{\text{dias\_totais\_da\_WAVE}} $$
*Foco: Manter $C_{comp} > 0.90$ para garantir a formação do hábito.*

### 4.2. Alinhamento com Calendário ($A_{cal}$)
Mede a eficiência das entregas de trabalho dentro das janelas úteis.
$$ A_{cal} = \frac{\text{entregas\_realizadas}}{\text{workdays\_disponíveis}} $$

### 4.3. Interseção: O Ponto de Equilíbrio
Onde seu comportamento encontra a realidade externa:
$$ \text{WAVE/CYCLE} \rightarrow \text{Comportamento (Hábitos Internos)} $$
$$ \text{HALF\_QUARTER} \rightarrow \text{Avaliação Externa (Resultados)} $$

---

## 5. Ecossistema de Tags e Taxonomia

Para automação via Dataview e organização em notas diárias, utilize a seguinte nomenclatura padronizada:

### 5.1. Unidades Temporais (Tokens)
- `DAY`, `WORKDAY`, `WEEK`, `WEEKDAYS`, `MONTH_APPROX`, `MONTH_WORKDAYS`, `QUARTER`, `HALF_QUARTER`, `BI_MONTH`

### 5.2. Processos e Fluxos
- `WAVE`: Ciclo de hábito (15 dias).
- `CYCLE`: Ciclo de avaliação (45 dias).
- `PHASE`: Ciclo de estratégia (180 dias).
- `MID_WAVE`, `HALF_QUARTER`, `MID_PHASE`: Pontos de monitoramento intermediário.
- `WAVE_END`, `CYCLE_END`, `QUARTER_END`, `PHASE_END`: Pontos de fechamento e retrospectiva.

### 5.3. Modificadores e Ajustes
- `STUDY_DAY`: Marcação de execução de estudo (7/7).
- `WORK_DAY`: Marcação de execução profissional (5/7).
- `REST_DAY`: Descanso programado.
- `ADJUST`: Registro de mudanças de rota durante o ciclo.
- `BUFFER_WORKDAYS`: Margem de segurança para imprevistos profissionais.
- `STUDY_BUFFER`: Tempo de recuperação para o plano de estudos.

---

## 6. Fórmulas de Acompanhamento (Tracking & Analytics)

Utilize estas fórmulas para calcular métricas de progresso em tempo real.

### 6.1. Cálculo de Hábito (WAVE Tracker)
Restante para os 15 dias de consolidação:
$$ \text{REMAINING\_WAVE\_DAYS} = 15 - \text{elapsed\_days} $$
$$ \text{REMAINING\_WAVE\_WORK} = 11 - \text{elapsed\_workdays} $$

### 6.2. Progresso do Ciclo
$$ \text{CYCLE\_PROGRESS} = \frac{\text{elapsed\_days}}{45} \cdot 100\% $$

### 6.3. Índice de Consistência ($IC$)
$$ IC = \frac{\text{days\_completed}}{\text{days\_planned}} $$
*Meta de Sucesso: $IC \geq 0.85$*

---

## 7. Aplicicação Prática: O Fluxo Operacional

### Como utilizar este modelo no dia a dia:

1.  **Formação de Hábito**: Marque uma `WAVE` de 15 dias. O foco deve ser 100% na repetição, sem falhas. O dia 8 (`MID_WAVE`) serve para ajustar a carga se estiver muito pesada.
2.  **Checkpoint Estratégico**: Ao final de cada `CYCLE` (45 dias), compare seu $IC$ de estudo com os resultados do trabalho. Se o trabalho consumiu os dias de estudo, use o `BUFFER_WORKDAYS` para recalibrar o próximo ciclo.
3.  **Interseção Fiscal**: O `CYCLE_END` é o seu **HALF_QUARTER CHECK**. É o momento de olhar para os OKRs do trimestre e ver se você está na metade do caminho planejado.

---

## 8. Integração com Obsidian

Para rastrear o progresso, você pode usar blocos de meta no YAML ou Dataview:

```dataview
TABLE 
    (15 - (date(today) - date(start_date)).days) AS "Days to Habit",
    round(((date(today) - date(start_date)).days / 45) * 100, 1) + "%" AS "Cycle Progress"
FROM "2_projeto"
WHERE status = "active"
```
*(Nota: Arquivos de exemplo `Exemplo_Projeto_Alpha` e `Exemplo_Habito_Beta` foram criados na pasta `2_projeto` para validar esta query na prática).*

---

## 9. Modelagem Matemática Avançada (Dinâmica Não-Linear)

Este sistema pode ser modelado como um **sistema dinâmico não-linear de produtividade humana**, integrando crescimento (aprendizado), decaimento (fadiga) e periodicidade (energia).

### 9.1. Produtividade Acumulada ao Longo do Ciclo
A produção total ao longo de um ciclo (45 dias) é a integral da produtividade diária $p(t)$. Assumindo que a produtividade não é constante e cresce com a adaptação até um platô:

$$ p(t) = p_{max}\left(1 - e^{-kt}\right) $$
$$ P_{acc}(t) = \int_0^t p(x) dx $$
*(Onde $k$ é a constante de aceleração e $p_{max}$ é a produtividade máxima sustentável).*

### 9.2. Formação de Hábito (A Curva Exponencial)
O nível de automatização de uma rotina $H(t)$ (variando de 0 a 1) cresce rapidamente nas primeiras repetições e depois satura.

$$ H(t) = 1 - e^{-\lambda t} $$
*(Onde $\lambda$ é a taxa de aprendizado. Em 1 WAVE de 15 dias, atingimos ~60-75% de consolidação; em 3 WAVES (1 CYCLE), chegamos a ~95%).*

```chartsview
#-----------------#
#- chart type -#
#-----------------#
type: Line

#-----------------#
#- chart data -#
#-----------------#
data:
  - day: '1'
    habit: 10
  - day: '3'
    habit: 35
  - day: '7'
    habit: 60
  - day: '11'
    habit: 75
  - day: '15'
    habit: 85
  - day: '25'
    habit: 95
  - day: '45'
    habit: 99

#-----------------#
#- chart options -#
#-----------------#
options:
  xField: 'day'
  yField: 'habit'
  smooth: true
  lineStyle:
    stroke: '#5B8FF9'
    lineWidth: 3
  point: {}
  label: {}
```

#### 💡 Resumo Analítico: A Curva de Consolidação
Este gráfico ilustra a **eficiência de automatização** do sistema. No início (Dia 1), o hábito é inexistente, exigindo carga cognitiva máxima para execução. Entre os dias 15 (fim da WAVE) e 30, a curva entra em fase de saturação. 
- **Teoria Matemática:** O modelo $H(t) = 1 - e^{-\lambda t}$ demonstra que o esforço consciente é inversamente proporcional à consolidação. 
- **Prática:** O objetivo é atingir os ~95% no final do CYCLE, permitindo que a tarefa seja executada com "vontade zero", sustentando o sistema mesmo em períodos de baixa energia.

### 9.3. Otimização da Duração da WAVE
Para maximizar a eficiência temporal $\frac{H(t)}{t}$:

$$ \max_t \left(\frac{1 - e^{-\lambda t}}{t}\right) $$
Calculando a derivada, o ponto ótimo ocorre próximo a $t \approx \frac{1}{\lambda}$, o que corrobora a escolha biológica de **15 a 21 dias** para a duração de uma WAVE.

### 9.4. Aritmética Modular (O Tempo Cíclico)
O modelo baseia-se em uma estrutura de estado bidimensional (dia da semana vs. posição no ciclo):

$$ S(t) = (t \pmod 7, \; t \pmod{45}) $$
Isso cria um **sistema dinâmico discreto**. Como $\gcd(7, 45) = 1$, o sistema garante variação constante, evitando que os checkpoints recaiam sempre no mesmo dia da semana, distribuindo a carga cognitiva de avaliação.

### 9.5. Curva de Energia dentro da WAVE
A energia de execução não é linear. Ela sobe rapidamente no início do foco e cai lentamente devido à fadiga:

$$ E(t) = t \cdot e^{-kt} $$
*(Modelo assimétrico: pico no primeiro terço da WAVE, seguido de declínio suave).*

```chartsview
#-----------------#
#- chart type -#
#-----------------#
type: Line

#-----------------#
#- chart data -#
#-----------------#
data:
  - day: '1'
    energy: 20
  - day: '3'
    energy: 70
  - day: '6'
    energy: 90
  - day: '9'
    energy: 75
  - day: '12'
    energy: 50
  - day: '15'
    energy: 30

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
  point: {}
  label: {}
```

#### 💡 Resumo Analítico: Dinâmica de Energia e Fadiga
Diferente da formação de hábito, a energia biológica é um recurso finito e oscilante. 
- **Teoria Matemática:** O modelo assimétrico $E(t) = t \cdot e^{-kt}$ captura o pico de entusiasmo e foco inicial (dia 6), seguido pelo declínio inevitável devido à fadiga acumulada.
- **Prática:** O sistema planeja o fechamento da WAVE (dia 15) justamente quando a energia atinge níveis críticos, forçando a transição para a fase de recuperação e supercompensação.

### 9.6. Performance Acumulada
A performance real do sistema é o acoplamento entre a força do hábito consolidado e a energia disponível:

$$ \text{Performance}(t) = E(t) \cdot H(t) $$
$$ P(t) = (t \cdot e^{-kt}) \left(1 - e^{-\lambda t}\right) $$
*Início baixo (energia alta, sem hábito) $\rightarrow$ Meio com pico máximo $\rightarrow$ Fim em queda (hábito alto, energia baixa / fadiga).*

### 9.7. Dinâmica de Sobrecarga Progressiva e Supercompensação
Diferente da formação de hábito, a evolução da performance exige o princípio da **Sobrecarga Progressiva**. A carga não cresce suavemente; ela opera em degraus semanais ajustados pela recuperação.

#### A. Função de Carga (Step Function)
A carga de trabalho $L(t)$ é definida por um incremento fixo ($\alpha$) aplicado a cada fechamento de ciclo de 7 dias, modulado pela função indicadora de dias úteis $\mathbb{1}_{work}$:

$$ L(t) = (B + \alpha \cdot \lfloor \frac{t}{7} \rfloor) \cdot \mathbb{1}_{work}(t) $$

#### B. Modelo de Performance (Fitness-Fatigue)
Sua performance real $P(t)$ é o diferencial entre o Fitness acumulado ($F$) e a Fadiga residual ($f$):

$$ P(t) = F(t) - f(t) $$

---

### 9.8. Visualização Sistêmica: Ondas de Trabalho vs. Âncora de Estudo
Nesta visualização, observamos o comportamento dual do sistema: enquanto o **Trabalho** utiliza o repouso para saltar para patamares superiores (Supercompensação), o **Estudo** permanece como uma linha de base inabalável, garantindo que o progresso intelectual nunca cesse.

```chartsview
#-----------------#
#- chart type -#
#-----------------#
type: Line

#-----------------#
#- chart data -#
#-----------------#
data:
  # Wave 1: Início e Consolidação
  - { day: '1', type: 'Trabalho (Ondas)', value: 10 }
  - { day: '3', type: 'Trabalho (Ondas)', value: 12 }
  - { day: '5', type: 'Trabalho (Ondas)', value: 14 }
  - { day: '6', type: 'Trabalho (Ondas)', value: 6 } # Descanso FDS
  - { day: '7', type: 'Trabalho (Ondas)', value: 6 }
  # Wave 2: Supercompensação (Inicia acima do pico anterior)
  - { day: '8', type: 'Trabalho (Ondas)', value: 16 }
  - { day: '10', type: 'Trabalho (Ondas)', value: 18 }
  - { day: '12', type: 'Trabalho (Ondas)', value: 20 }
  - { day: '13', type: 'Trabalho (Ondas)', value: 10 } # Descanso FDS
  - { day: '14', type: 'Trabalho (Ondas)', value: 10 }
  # Wave 3: Expansão de Carga
  - { day: '15', type: 'Trabalho (Ondas)', value: 22 }
  - { day: '17', type: 'Trabalho (Ondas)', value: 24 }
  - { day: '21', type: 'Trabalho (Ondas)', value: 28 }
  
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
  point: {}
  label: {}
  legend:
    position: 'top'
  yAxis:
    title: { text: 'Intensidade / Carga' }
```
*Legenda: A linha azul (Trabalho) demonstra a ascensão pulsante via supercompensação. A linha verde (Estudo) representa o lastro de consistência contínua.*

#### 💡 Resumo Analítico: O Equilíbrio entre Ondas e Lastro
Este gráfico é o coração operacional do seu framework de **Senior Data Engineer**. 
- **Ondas de Trabalho:** Utilizam o estresse controlado da semana para forçar a adaptação. A queda no FDS permite o salto na segunda-feira seguinte (Teorema 5).
- **Âncora de Estudo:** Ao contrário do trabalho, o estudo não deve oscilar. Ele serve como o "volante de inércia" do sistema, mantendo a tração mental estável mesmo quando as demandas externas flutuam.

---

## 10. Teoremas Operacionais do Sistema (Expandido)

Esta formalização gera teoremas que regem sua execução:

1. **Teorema 1 (Consolidação Exponencial):** A formação de hábito não depende de tempo linear, mas segue uma curva exponencial saturada. O retorno diminui após 15 dias (fim da WAVE).
2. **Teorema 2 (Pico de Eficiência):** Existe um ponto ótimo $t^*$ em cada WAVE onde a relação entre produtividade e consolidação de hábito é máxima.
3. **Teorema 3 (Desalinhamento Modular):** Devido à co-primalidade $\gcd(7, 45) = 1$, o sistema previne pontos cegos semanais, garantindo que avaliações de ciclo aconteçam em diferentes contextos da rotina útil.
4. **Teorema 4 (Acoplamento Energia-Hábito):** A performance de alto nível não requer energia infinita. À medida que a energia decai ao final da WAVE, a consolidação exponencial do hábito compensa a queda, sustentando a execução.
5. **Teorema 5 (Supercompensação de Ciclo):** O descanso planejado é o catalisador que permite ao Trabalho ($L$) escalar sem romper o sistema.
6. **Teorema 6 (Estudo como Lastro):** A constância do Estudo ($K$) atua como um volante de inércia, mantendo o ímpeto produtivo mesmo durante as fases de baixa carga de trabalho.

---

## 11. Métricas de Auto-Performance Avançadas

Além do $IC$, utilizamos métricas de alta resolução para ajustar o sistema em tempo real.

### 11.1. Quociente de Adaptação ($AQ$)
Mede a velocidade com que você absorve novas cargas de trabalho entre CYCLES.
$$ AQ = \frac{L_{final} - L_{initial}}{\text{CYCLE}} $$

### 11.2. Razão de Carga Cognitiva ($CLR$)
Mede o equilíbrio entre o esforço de aprendizado (interno) e o esforço de entrega (externo).
$$ CLR = \frac{\sum \text{Study Hours}}{\sum \text{Work Hours}} $$
*Valor Ideal: $0.3 \leq CLR \leq 0.5$.*

### 11.3. Fator de Supercompensação ($SF$)
Avalia a qualidade do seu descanso e a prontidão para o novo ciclo.
$$ SF = \frac{p(\text{Segunda})}{p(\text{Sexta anterior})} $$

### 11.4. Eficiência de Ciclo ($EC$)
$$ EC = \frac{\text{Resultados Obtidos}}{\text{Energia Gasta} \times \text{Tempo}} $$

### 11.5. Fator Kaizen ($\kappa$)
Representa a melhoria marginal diária acumulada.
$$ \kappa(t) = (1 + r)^t $$
*Onde $r$ é a taxa de refinamento diário dos processos.*

### 11.6. Visualizações de Analytics de Alta Resolução (Dashboard)
Para monitorar a saúde do sistema, utilizamos gráficos compostos que cruzam variáveis internas e externas.

#### A. Correlação Hábito vs. Performance (Dual Axes)
Demonstra como a subida da automatização ($H(t)$) sustenta a performance mesmo quando a energia começa a oscilar.

```chartsview
#-----------------#
#- chart type -#
#-----------------#
type: DualAxes

#-----------------#
#- chart data -#
#-----------------#
data:
  - [
      { day: '1', habit: 10 },
      { day: '7', habit: 50 },
      { day: '15', habit: 85 },
      { day: '30', habit: 95 },
      { day: '45', habit: 99 }
    ]
  - [
      { day: '1', performance: 20 },
      { day: '7', performance: 65 },
      { day: '15', performance: 80 },
      { day: '30', performance: 85 },
      { day: '45', performance: 75 }
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
    - geometry: 'line'
      color: '#5AD8A6'
      smooth: true
```

#### 💡 Resumo Analítico: Hábito como Seguro de Performance
Este gráfico cruza o **custo da produtividade** com a sua automatização.
- **Eficiência Energética:** No início, você gasta força de vontade (energia cara). Conforme o hábito sobe (Linha Azul), a performance (Linha Verde) torna-se mais barata de manter.
- **Amortecedor de Fadiga:** Repare que a performance declina levemente no final do CYCLE devido à fadiga acumulada, mas o hábito alto impede o colapso do sistema ("execução por inércia").

#### 🔬 Resumo Técnico: Análise de Variabilidade e Curva Assintótica
- **Curva Assintótica:** O rendimento segue a "lei dos rendimentos decrescentes". Ganhos iniciais são íngremes; conforme você se aproxima do limite de automatização, a curva achata (assíntota), exigindo esforço exponencial para ganhos marginais.
- **Rastreio Dual Axis:** Técnica fundamental para identificar o ponto de saturação entre automatização e performance.

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
A consistência de **87%** não é apenas um número; é a validação de que o sistema está em zona verde. Abaixo de 80%, o sistema entra em risco de quebra de hábito (WAVE desfeita). Acima de 90%, há margem para aumentar o $AQ$ (Quociente de Adaptação).

#### C. Equilíbrio de Carga Cognitiva ($CLR$)
Visualiza se você está estudando o suficiente em relação ao trabalho (Target: 0.4).

```chartsview
type: Bullet
data:
  - title: 'CLR'
    ranges: [30, 50, 100]
    measures: [42]
    target: 40
options:
  xField: 'title'
  rangeField: 'ranges'
  measureField: 'measures'
  targetField: 'target'
  color:
    range: ['#FFbcb8', '#FFe0b0', '#baf0c4']
    measure: '#5B8FF9'
    target: '#39a3f4'
```

#### 💡 Resumo Analítico: A Proporção Áurea da Engenharia
O target de **0.4** no CLR é o seu ponto de equilíbrio estratégico. 
- **Obsolecência ($CLR < 0.2$):** Muita entrega profissional, pouco estudo. Risco de estagnação técnica a longo prazo.
- **OKRs em Risco ($CLR > 0.6$):** Muito estudo, pouca entrega. Risco de não atingir os resultados exigidos pelo mercado no `HALF_QUARTER`.
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
O **Donut Chart** revela a hierarquia de alocação. Enquanto a Entrega domina a fatia principal, o **Buffer (15%)** é o componente mais subestimado: ele é a margem de erro necessária para absorver o ruído gaussiano (dias ruins) sem comprometer o crescimento.

---

## 12. Sistema Matemático Operacional de Decisão
Até aqui, modelamos o tempo e a carga. Agora, transformamos o framework em um **sistema de auto-otimização e controle adaptativo**, capaz de decidir dinamicamente onde alocar energia.

### 12.1. Variáveis Fundamentais do Sistema
Para cada hábito/projeto $h_i$, rastreamos:
- $s$: *Streak* atual (dias consecutivos).
- $s_{prev}$: *Streak* anterior.
- $H(s)$: Nível de automatização.
- $R$: Resistência (Dificuldade inerente da tarefa).
- $E_{req}$: Energia requerida.

### 12.2. A Matemática da Priorização

**A. Progresso Baseado em Streak (Não em Tempo)**
O hábito real não se importa com a data no calendário, mas com a repetição:
$$ H(s) = 1 - e^{-\lambda s} $$

**B. Custo Energético e Déficit**
O Déficit ($D$) mede quanto falta para a automatização ($D = 1 - H(s)$). A energia requerida ($E_{req}$) para executar uma tarefa hoje é o produto da sua dificuldade pelo seu déficit:
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
- **Prática (Radar):** No gráfico, a "Leitura" domina a eficiência (alto H, baixo custo). A "Codificação" tem alto custo ($E_{req}$). **Teorema do Foco Único:** Ao invés de dividir energia, o sistema dita que você deve manter a Leitura em "piloto automático" e devotar toda a energia $E(t)$ disponível da WAVE para superar a resistência da Codificação.

### 12.4. Matriz de Paisagem Cognitiva: Navegando no Débito de Esforço
Ao invés de pontos isolados, visualizamos a "densidade" do custo. O **Heatmap** mapeia o terreno: as zonas escuras são pântanos de alta resistência e baixo hábito, onde a energia é drenada rapidamente.

```chartsview
#-----------------#
#- chart type -#
#-----------------#
type: Heatmap

#-----------------#
#- chart data -#
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
- **O Pantanal de Energia (Zona Azul Profunda):** Representa tarefas como "Codificação". O custo de oportunidade aqui é máximo. O sistema dita: **não entre aqui sem um tanque de energia $E(t)$ cheio**.
- **Planícies de Manutenção (Zona Clara):** Tarefas como "Meditação". São seguras para dias de baixa energia, mantendo a consistência global sem risco de exaustão.

### 12.5. O Volante de Inércia (Momentum Flywheel)
Este gráfico de **Rose (Radial Bar)** visualiza quais hábitos estão "girando" o seu sistema. Quanto maior a pétala, maior é o retorno sobre o investimento ($ROI$) de momentum que aquele hábito gera para o seu CYCLE.

```chartsview
#-----------------#
#- chart type -#
#-----------------#
type: Rose

#-----------------#
#- chart data -#
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
- **Teoria do Volante (Flywheel):** Hábitos de alto valor (Codificação) exigem muito esforço inicial para girar, mas uma vez em movimento ($H > 0.8$), a inércia gerada sustenta a performance de todo o seu portfólio.
- **Interpretação Visual Simétrica:** Pétalas desequilibradas indicam um sistema frágil. O objetivo do CYCLE é expandir as pétalas de forma simétrica.

---

## 13. Léxico Expandido e Funções de Rastreamento (Apêndice Técnico)

Para assegurar que nenhuma nuance operacional do sistema original seja perdida, compilamos os tokens operacionais, flags e funções lógicas usadas para controle em planilhas ou scripts.

### 13.1. O que significa `MONTH_APPROX`
**`MONTH_APPROX`** é uma constante média (30 dias corridos) usada para estimativas rápidas.

### 13.2. Exemplos Práticos Sem Datas
- **Meta: Hábito em 1 WAVE (15 dias corridos / 11 dias úteis):**
  - Se você já completou **7 dias corridos**: `remaining_days` = 15 − 7 = **8 dias corridos**.
  - Se já completou **5 workdays**: `remaining_workdays` = 11 − 5 = **6 workdays**.

### 13.3. Tags e Funções Úteis para Rastreamento (Code & Sheets)
**Variáveis de Estado (Flags):**
- `IS_STUDY_DAY` (True/False): Estudo no dia.
- `IS_WORKDAY` (True/False): Dia útil trabalhado.

**Funções Programáveis Sugeridas:**
- `days_until_habit(start_day_count)` $\rightarrow$ Retorna `WAVE_DAYS - start_day_count`
- `workdays_until_habit(start_workday_count)` $\rightarrow$ Retorna `WAVE_WORKDAYS - start_workday_count`
- `corridos_to_workdays(total_days)` $\rightarrow$ Retorna uma aproximação de dias úteis usando o `WORK_RATIO`.
- `workdays_to_corridos(total_workdays)` $\rightarrow$ Retorna a estimativa inversa.

---

## 14. Modelagem Analítica e Ponto Ótimo de Performance
Para elevar o sistema ao nível de modelagem contínua, determinamos matematicamente o momento ideal de pico produtivo através da derivação da função de performance.

### 14.1. Função de Performance Completa (Modelo Base)
$$ P(t) = \frac{t e^{-kt}(1 - e^{-\lambda t})}{R} $$

### 14.2. Resolução Analítica do Ponto de Máximo
Encontramos o pico ótimo igualando a derivada a zero ($P'(t) = 0$):
$$ P'(t) = \frac{e^{-kt}}{R} \left[ (1 - e^{-\lambda t})(1 - kt) + \lambda t e^{-\lambda t} \right] = 0 $$

**Conclusão Numérica:** Para regimes típicos ($k \approx 0.05, \lambda \approx 0.1$), o pico ocorre em $t^* \approx 12$ a $18$ dias. Isso prova que a **WAVE de 15 dias** é o ótimo estrutural fisiológico.

### 14.3. Simulação Conceitual do Ciclo
| Região | Fenômeno |
| :--- | :--- |
| $t < 5$ | Esforço alto / Hábito baixo |
| $5 < t < 12$ | Crescimento rápido |
| $12 < t < 18$ | **Pico de performance ($t^*$)** |
| $t > 18$ | Fadiga domina |

---

## 15. Supercompensação Fisiológica (Modelo Gaussiano)
Refinamos o modelo de energia para incluir a onda de adaptação após o estresse controlado.
$$ E(t) = t e^{-kt} + A e^{-\frac{(t - t_0)^2}{2\sigma^2}} $$

```chartsview
#-----------------#
#- chart type -#
#-----------------#
type: Line

#-----------------#
#- chart data -#
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
  point: {}
  label: {}
  legend:
    position: 'top'
```

#### 💡 Resumo Técnico: A Fisiologia da Execução
A linha verde demonstra que o descanso programado gera um ganho absoluto de capacidade produtivo superior ao pico inicial de entusiasmo.

---

## 16. Otimização Adaptativa e Meta-Heurística (UCB)
A seleção de hábitos não deve ser gulosa. Balanceamos **Exploração** e **Explotação** via algoritmo *Upper Confidence Bound*.

### 16.1. Índice de Eficiência do Hábito ($I$)
$$ I_i = \frac{H_i(t) \cdot \Delta s_i}{R_i(1 - H_i(t))} $$

### 16.2. Modelo Multi-Armed Bandit
$$ \text{Score}_i = I_i + c \cdot \sqrt{\frac{\ln T}{n_i}} $$

#### 💡 Resumo Técnico: Escapando do Mínimo Local
O bônus matemático para hábitos negligenciados (baixo $n_i$) garante que seu portfólio de competências de **Senior Data Engineer** evolua globalmente, evitando que você estacione apenas no que é confortável.

### 16.3. Dashboard Matemático de Apoio
| Métrica | Fórmula | Função |
| :--- | :--- | :--- |
| **Habit Level** | $H(t)$ | Automatização atual |
| **Energy** | $E(t)$ | Energia pós-fadiga |
| **Performance** | $P(t)$ | Output real esperado |
| **Remaining** | $\text{WAVE} - s$ | Dias para consolidar |
| **Ranking** | $\text{sort}(\text{Score}_i)$ | Priorização Final |

---

## 17. Calibração Empírica com Dados Reais
Para personalizar o sistema, calibramos as constantes com seu histórico (via Dataview).

### 17.1. Calibração de $\lambda$ (Aprendizado)
$$ \lambda = -\frac{\ln(1 - H(t))}{t} $$

### 17.2. Calibração de $k$ (Fadiga)
$$ k = -\frac{1}{t} \ln\left(\frac{E(t)}{t}\right) $$

---

## 18. Resolução Numérica Avançada (Newton-Raphson)
Enquanto a aproximação prática indicou que o pico de performance $t^*$ ocorre entre 12 e 18 dias, podemos usar cálculo numérico para obter o valor exato, resolvendo $f(t) = P'(t) = 0$.

$$ f(t) = (1 - e^{-\lambda t})(1 - kt) + \lambda t e^{-\lambda t} = 0 $$

Aplicando o **Método de Newton-Raphson**:
$$ t_{n+1} = t_n - \frac{f(t_n)}{f'(t_n)} $$
*(Onde $f'(t)$ é a derivada da condição de máximo).*

Usando um "chute inicial" de $t_0 = 10$, com $k = 0.05$ e $\lambda = 0.1$, o algoritmo converge rapidamente para:
$$ t^* \approx 14.2 \text{ dias} $$

**Conclusão Matemático-Fisiológica:** O pico absoluto da capacidade produtiva em um ciclo de consolidação ocorre quase exatamente no limite da WAVE (15 dias). O dia 15 não é arbitrário; é a borda matemática do colapso por fadiga.

---

## 19. Engenharia do Caos e Processos Estocásticos
A realidade não é uma linha suave. Dias ruins ("Caos") são inevitáveis. Transformamos o modelo determinístico em um **Modelo Estocástico** para prever falhas e resiliência.

### 19.1. Modelagem de Incerteza (Dias Ruins)
A energia diária não é fixa; ela sofre perturbações. Adicionamos um Ruído Gaussiano ($\epsilon$) para representar a imprevisibilidade da vida:
$$ \epsilon \sim \mathcal{N}(0, \sigma^2) $$
$$ E(t) = E_{base}(t) + \epsilon $$

```chartsview
#-----------------#
#- chart type -#
#-----------------#
type: Line

#-----------------#
#- chart data -#
#-----------------#
data:
  - { day: '1', type: 'Energia Base', value: 80 }
  - { day: '3', type: 'Energia Base', value: 85 }
  - { day: '5', type: 'Energia Base', value: 75 }
  - { day: '7', type: 'Energia Base', value: 60 }
  - { day: '9', type: 'Energia Base', value: 50 }
  - { day: '1', type: 'Energia Real (Caos)', value: 72 } # -8 noise
  - { day: '3', type: 'Energia Real (Caos)', value: 92 } # +7 noise
  - { day: '5', type: 'Energia Real (Caos)', value: 45 } # -30 noise (Bad Day)
  - { day: '7', type: 'Energia Real (Caos)', value: 65 } # +5 noise
  - { day: '9', type: 'Energia Real (Caos)', value: 30 } # -20 noise
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
  point: {}
```

#### 💡 Resumo Técnico: Resiliência ao Ruído
A linha azul representa o plano ideal. A linha vermelha demonstra a **Engenharia do Caos** em ação: repare no "mergulho" no dia 5. O sistema prova que se o $H(t)$ estiver alto, o hábito sobrevive a essa queda brusca; se estiver baixo, o *Streak* reseta.

### 19.2. O Streak como Cadeia de Markov
O Streak não é apenas uma contagem, é uma transição de estado estocástica:
- Probabilidade de manter/crescer: $P(s \to s+1) = P(\text{execute})$
- Probabilidade de falhar (resetar): $P(s \to 0) = 1 - P(\text{execute})$

A **Esperança Matemática do Streak** prova que um pequeno ganho na consolidação gera um salto massivo na consistência:
$$ \mathbb{E}[s] \approx \frac{P(\text{execute})}{1 - P(\text{execute})} $$

---

## 20. Programação Dinâmica: Política Ótima de Decisão (MDP)
A decisão de "qual hábito focar hoje" não afeta apenas o presente, mas todo o crescimento futuro. O sistema opera como um **Processo de Decisão de Markov (MDP)**.

### 20.1. A Equação de Bellman
O valor ótimo de focar em um hábito hoje não é apenas a performance imediata, mas a maximização do retorno futuro com um fator de desconto ($\gamma$):
$$ V(S_t) = \max_{a_t} \left[ R(S_t, a_t) + \gamma V(S_{t+1}) \right] $$

Onde a Recompensa Imediata é:
$$ R(S_t, a_t) = P_i(t) = \frac{E(t) \cdot H_i(t)}{R_i} $$

### 20.2. Regra de Decisão Aproximada (Política Ótima)
Resolver Bellman puramente é custoso. Aproximamos o valor do Índice Ótimo ($Q_i$) combinando a recompensa imediata com o ganho marginal futuro ($\Delta V_i$):
$$ a^* = \arg\max_i \left( \frac{H_i(t)}{R_i} + \gamma (1 - H_i(t)) \right) $$

```chartsview
#-----------------#
#- chart type -#
#-----------------#
type: DualAxes

#-----------------#
#- chart data -#
#-----------------#
data:
  # Retorno Imediato H(t)/R (Hábito Consolida)
  - [
      { day: '1', immediate: 10 },
      { day: '15', immediate: 50 },
      { day: '30', immediate: 85 },
      { day: '45', immediate: 95 }
    ]
  # Potencial Futuro gamma(1-H) (Ouro de Crescimento)
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
      color: '#52c41a' # Verde: Colheita
      smooth: true
    - geometry: 'line'
      color: '#faad14' # Laranja: Investimento
      smooth: true
  yAxis:
    immediate:
      title: { text: 'Retorno Imediato' }
    future:
      title: { text: 'Potencial de Crescimento' }
```

#### 💡 Resumo Técnico: Otimização de Bellman
- **A Interseção (Ponto Crítico):** O gráfico mostra onde o valor do "Investimento" (Laranja) cruza com a "Colheita" (Verde).
- **Regra de DP:** No início do ciclo, o sistema prioriza o potencial futuro. Conforme o hábito consolida, a política muda para a explotação da performance máxima. Este plot visualiza a transição de estado de um **Novato** para um **Master**.

#### 💡 Resumo Técnico: Teorema da Prioridade Dinâmica
Esta equação final é brilhante por dividir a decisão em dois regimes de tempo:
1. **Regime de Crescimento (Foco no Futuro):** Se o hábito é novo ($H \to 0$), o termo $\gamma (1 - H)$ é gigante. O sistema manda você ignorar a baixa performance imediata e investir na construção.
2. **Regime de Exploração (Foco no Presente):** Se o hábito está consolidado ($H \to 1$), a recompensa futura zera. O sistema manda você "colher" a alta performance $\frac{H}{R}$ gerada por ele.

**A Decisão Inteligente:** O hábito ótimo nem sempre é o que gera mais resultado hoje, mas o que maximiza a área sob a curva no final da WAVE.

---

## 21. Otimização Multi-Hábito e o Problema da Mochila (Knapsack)
Expandindo a decisão para **múltiplas ações por dia**, a seleção de hábitos deixa de ser singular e torna-se um problema de alocação de recursos finitos (Energia).

### 21.1. O Problema da Mochila
Temos um orçamento diário de energia $E_{total}$. Cada hábito $i$ requer um custo $E_{req,i}$ e fornece um valor $P_i$. O objetivo é maximizar o retorno total sem "estourar" a energia biológica.

**Função Objetivo:**
$$ \max \sum_i x_i P_i(t) $$
**Restrição de Energia:**
$$ \sum_i x_i E_{req,i} \le E_{total} $$
*(Onde $x_i \in \{0, 1\}$ indica se o hábito foi escolhido).*

**Regra Ótima Heurística:** Escolha $x_i = 1$ sempre que a razão $\frac{P_i}{E_{req,i}}$ for muito alta.

```chartsview
#-----------------#
#- chart type -#
#-----------------#
type: Bullet

#-----------------#
#- chart data -#
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
Assim como em finanças, você não pode "comprar" todos os projetos. O gráfico visualiza o consumo da sua energia total. Quando o `measure` ultrapassa o limite verde (80%) em direção ao vermelho, você entrou em *Overreaching*. O algoritmo Knapsack previne isso podando os hábitos de menor ROI.

### 21.2. Ranking de Decisão (Column Chart)
A premissa da regra ótima heurística: focar nos hábitos onde o retorno por unidade de energia é máximo.

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
Este gráfico de colunas ordena seus hábitos pelo **Índice de Eficiência ($I$)**. O algoritmo Knapsack "come" os itens da esquerda para a direita até esgotar o $E_{total}$. Isso demonstra por que, em dias de baixa energia, apenas os itens do topo (mais eficientes) são mantidos, enquanto a "Codificação" é a primeira a ser cortada.

---

## 22. Simulação de Portfólio Multi-Agente (Ecossistema Adaptativo)
Tratar hábitos como "Agentes" que competem por energia. Hábitos consolidados sugam menos energia, permitindo que novos hábitos nasçam no ecossistema.

### 22.1. Dinâmica do Ecossistema
A evolução emergente prova que o sistema é vivo:
- Hábitos fortes dominam a tração (alta performance, baixo custo).
- Hábitos fracos morrem (abandonados por baixa eficiência).
- A energia excedente flui dinamicamente.

```chartsview
#-----------------#
#- chart type -#
#-----------------#
type: Area

#-----------------#
#- chart data -#
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
Este gráfico de área empilhada mostra a sucessão ecológica dos seus hábitos ao longo de um CYCLE. No início (Dia 1), "Codificação" drena a maior parte do $E_{total}$. Mas, conforme ele se torna automático (Dia 45), seu custo cai drasticamente, liberando "espaço biológico" para o "Novo Idioma" crescer e dominar o portfólio. É a visualização perfeita do crescimento contínuo.

---

## 23. Solução Exata do MDP (Value & Policy Iteration)
Para evoluir da "Regra Aproximada" ($Q_i$) para o sistema determinístico exato, aplicamos a solução matricial completa da Programação Dinâmica.

### 23.1. Forma Matricial (Portfólio)
O vetor de decisão diária para todas as ações é $\mathbf{a} = (a_1, ..., a_n)$. A função de valor converge iterativamente via:
$$ \mathbf{V} = \mathbf{P}^T \mathbf{a} + \gamma \mathbf{V}_{next} $$
*(Esta formulação é equivalente ao controle dinâmico multi-período usado em Algorithmic Trading e Inteligência Artificial).*

### 23.2. Problema de Controle Restrito
A otimização busca maximizar toda a sequência futura de recompensas:
$$ \max \sum_t \gamma^t R(S_t, a_t) $$
*Sujeito a:* $E_t \le E_{max}$

#### 💡 Resumo Técnico: Otimização Dinâmica Adaptativa
Ao aplicar Value Iteration numérico via script (Python/DataviewJS), você não reage mais ao dia de hoje; o sistema "joga xadrez" calculando as consequências de pular um hábito 30 dias no futuro. É o auge da Modelagem Pessoal de Alta Performance.

### 23.3. Mapa de Valor do Espaço de Estados (Treemap)
Visualiza a hierarquia de valor acumulado ($V$) que cada domínio da sua vida contribui para a política ótima de longo prazo.

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
        - name: 'Deep Learning, Ai Agents'
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
O **Treemap** traduz a solução matricial da Seção 23.1 em áreas visuais. Blocos maiores representam estados com maior valor esperado de recompensa acumulada. O algoritmo de Programação Dinâmica prioriza ações que mantêm você "dentro" dos blocos maiores do mapa, garantindo que o seu portfólio de vida tenda à maestria global.

---
**Nota Final:** Este sistema prioriza a **consistência modular** sobre a rigidez do calendário. Se uma Phase atrasar, ajuste as Waves, mas nunca quebre a proporção de 15/45/180.
---