# Análise: Limites do Taskwarrior "Vanilla" vs. Modelo Estratégico

Esta análise responde à questão: **Até onde é possível ir com as definições do modelo estratégico (PAE + Estrutura Hierárquica Operacional) utilizando estritamente o Taskwarrior via CLI (Vanilla), sem plugins, scripts externos ou integrações via API? O que NÃO pode ser feito ou não funciona tão bem?**

A base desta análise são as próprias documentações do workspace ([TASKWARRIOR_PITFALLS_AND_WORKAROUNDS.md](file:///c:/Users/mathe/code_space/produtividade/taskwarrior/docs/TASKWARRIOR_PITFALLS_AND_WORKAROUNDS.md), [INDEX-TW.md](file:///c:/Users/mathe/code_space/produtividade/INDEX-TW.md) e os arquivos dentro de `strategics/`).

---

## 1. O Abismo Estrutural: Hierarquia de 5 Níveis

O seu modelo estratégico (detalhado em `Modelagem Operacional.md` e [Integracao_Tatica.md](file:///c:/Users/mathe/code_space/produtividade/strategics/Integracao_Tatica.md)) exige 5 níveis lógicos de granularidade:
1. **Sonhos** (6 a 12 meses)
2. **Objetivos** (Quinzenal / 3 meses dependendo da lente)
3. **Metas** (Semanal)
4. **Tarefas** (Diário)
5. **Atividades** (Checklists diários)

**Limitação do Vanilla:**
O Taskwarrior *vanilla* possui uma estrutura estritamente bidimensional (Flat): **Projetos -> Tarefas**.
Você pode usar "Subprojetos" (ex: `project:sonho.objetivo`), mas isso rapidamente se torna verboso e inflexível para 5 níveis.

**O que dá para fazer (mas não fica bom):**
Criar múltiplos **UDAs** (User Defined Attributes) como `sonho_id`, `objetivo_id`, e `meta_ciclo`.
**Por que não funciona tão bem:** Você terá que preencher *manualmente* cada UDA para toda tarefa criada para não quebrar as filtragens. O Taskwarrior vanilla **não** vai avisar se você criar uma "Meta" órfã (sem objetivo atrelado) ou se cometer um erro de digitação no ID do sonho. Não existe validação relacional nativa.

---

## 2. A Incompatibilidade Temporal: Dias Úteis vs. Dias Corridos

A base do seu `Planejamento (Estratégico e Tático).md` define ciclos de trabalho extremamente específicos:
- Ciclos de **45 dias úteis**
- Ondas de **3 semanas (15 dias úteis)**
- Semanas focadas em **5 dias úteis**

**Limitação do Vanilla:**
O motor de cálculo de datas e recorrência (`recur:`) do Taskwarrior só entende **dias corridos** (calendário gregoriano tradicional).

**O que NÃO pode ser feito:**
Você não consegue dizer para o Taskwarrior vanilla: *"Crie essa meta e coloque a data de vencimento (due date) para daqui a 15 dias úteis"*. Ele incluirá sábados e domingos no cálculo. Fazer o Taskwarrior pular feriados ou finais de semana automaticamente para os limites (boundaries) das suas Ondas e Ciclos é impossível sem um script de Bash ou Python passando por fora.

---

## 3. O Vazio Qualitativo: Sistema de Narrativas e Revisão

Seu modelo exige formulários narrativos diários (A Rotina Inicial e a Rotina Final):
- *"O que eu fiz hoje que correu bem?"*
- *"Que tarefa de ontem deve tornar-se um hábito?"*

**Limitação do Vanilla:**
O Taskwarrior foi projetado para *to-do lists* atômicos, não para *journaling* ou anotações qualitativas extensas.

**O que dá para fazer (mas não fica bom):**
Criar uma "tarefa-zumbi" temporária chamada "Rotina Final" e responder às perguntas usando _Annotations_ (`task <id> annotate "1. Hoje a produtividade foi... "`).
**Por que não funciona tão bem:** O formato fica poluído na linha de comando e é péssimo para revisões semanais longas. Ler um histórico longo de `annotations` de tarefas passadas no terminal é difícil e não permite buscas ricas ou formatação (como Markdown).

---

## 4. O Ponto Cego Analítico: Ausência de Métricas Nativas

A "Análise Tática e Operacional" requer métricas, como a **Taxa de Conclusão (%)** e **Eficiência Sistêmica**.

**Limitação do Vanilla:**
O Taskwarrior não calcula estatísticas ou porcentagens. Ele apenas filtra e lista tarefas (com o `task summary` fornecendo apenas contagens brutas e um rudimentar _progress bar_ geral do projeto).

**O que NÃO pode ser feito:**
Saber a "Taxa de Produtividade" da sua Onda de 15 dias. O CLI não te dirá "Você concluiu 71% das metas da Fase 2". Para isso, é absolutamente obrigatório despejar os dados com `task export` (que gera um JSON) e processá-los com uma linguagem externa (Python/Bash) - o que você já documentou nos seus planos via `calculate-metrics.py`.

---

## 5. Falta de Capacidade Preditiva e de Agendamento Rígido (Blocos)

Seu planejamento dita blocos de tempo diários (**Manhã, Tarde, Noite**).

**Limitação do Vanilla:**
O Taskwarrior é voltado para *Task Management* orientado a prazos (`due`), e não *Time Blocking* ou calendário.
Você pode usar a meta-tag `bloco_tempo:Manhã`, mas o CLI vanilla não emite notificações quando a "Tarde" começa, nem entende se você "superlotou" a Manhã com 40 horas de tarefas. Ele é cego à capacidade real do seu tempo naquele dia, agindo apenas como um banco de dados de pendências.

---

### Resumo: O Veredito do Vanilla

**Até onde podemos ir unicamente via `taskwarrior cli`?**
Você pode ir até a **captura estrita, listagem, priorização e organização das pendências**. Ele é um motor de banco de dados no terminal excelente para agir como o "cérebro das tarefas do dia".

**Onde ele quebra (e onde os scripts/hooks são indispensáveis):**
1. **Validação e Integridade do Modelo:** O Vanilla não sustentará os 5 níveis hierárquicos à prova de erros. Exige que o humano aja como banco de dados relacional.
2. **Cálculos Baseados no Calendário Útil:** Não vai suportar sozinhos os ciclos de 45 dias úteis e ondas de 15 dias.
3. **Análise de Performance:** Não fornecerá taxas de conclusão nem métricas de coerência estratégica.
4. **Registro Narrativo / Journaling:** Péssimo para as "rotinas de entrada e saída" qualitativas.

Para que seu Modelo Estratégico ganhe vida no terminal, **a camada de scripts (`.sh`, `.ps1` e `.py`) e a instrumentação customizada que você definiu (UDAs, Reports e Hooks) não são apenas perfumaria, são requisitos arquiteturais fundamentais** para complementar o que falta no binário puro do Taskwarrior.
