# Estratégia de Arquitetura: Data-Mesh e Desacoplamento de Sistemas

Este documento delineia a visão estratégica para um ecossistema de produtividade interoperável. A premissa central é abandonar a abordagem monolítica ("Fully Bounded") onde uma única ferramenta tenta resolver tudo, movendo-nos para uma **Arquitetura de Data-Mesh**.

Nesse novo paradigma, teremos múltiplos sistemas independentes, fortemente tipados e conectados através de contratos de dados específicos. Cada sistema foca exclusivamente em extrair o máximo de performance de sua "faceta" principal.

## A Grande Divisão: Planejamento vs. Execução

Para resolver o atrito e a fragilidade de tentar manter toda a lógica estratégica em formato de tags e hooks, o sistema será dividido em duas esferas principais através de um "pipeline" de fluxo de dados.

### 1. Sistema Upstream: Planejamento & Backlogger
Este é o cérebro onde as definições organizacionais habitam.

*   **Natureza:** Estrutura flexível usando documentos em Markdown organizados em múltiplos níveis (Ex: Diretório `strategics/`).
*   **Função:** 
    *   Lidar com a elicitação de requisitos, engenharia de especificações (Specs-first + PDR).
    *   Conectar o *PAE (Plano de Ação Estratégico)* e a *Hierarquia Operacional* a checklists e formulários para dividir grandes objetivos.
    *   Processar algoritmos de alocação de tempo: gerar o planejamento do ano, semana, ou dia baseado nas métricas de tempo de calendário viáveis (Time-Blocking em nível Macro).
    *   Gerar o "Backlog Master".
*   **Banco de Dados:** Terá seu próprio formato relacional para organizar (Sonhos -> Objetivos -> Metas -> Entregas).

### 2. Sistema Downstream: Execução & Rastreamento (Taskwarrior + Timewarrior)
Esta é a esteira de montagem, focada especificamente nas tarefas de software e entregáveis operacionais.

*   **Natureza:** Máquina de Estados binária em linha de comando.
*   **Função:**
    *   "Rastrear" o andamento das tarefas de software vindas do Backlogger.
    *   Cronometrar o esforço de entrega rigorosamente com o **Timewarrior** para extração precisa de relatórios de ROI (Retorno de Investimento de Tempo vs. Renda).
    *   Focar estritamente na ótica `Project -> Task`.
*   **Banco de Dados:** O banco nativo (`.task`), operando no seu pico de abstração com a usabilidade mais refinada (sem penduricalhos).

---

## O Desafio dos Contratos: Evitando o "Garçom de Dados"

A conexão entre o *Planejador* e o *Executor* se dará através do **Data-Mesh**, que compartilhará estruturas de dados via APIs e algoritmos dedicados. O desafio aqui é evitar que a comunicação entre sistemas se transforme em uma obrigatoriedade de entrada manual (data entry) excessiva no Taskwarrior.

### Trade-offs de UDAs Puras (A Fricção Manual)

Tentar espelhar o banco de dados do Planejamento dentro do Taskwarrior gerou problemas anteriormente:

*   **A Fricção no Dia-a-Dia:** A necessidade de preencher manualmente UDAs (`sonho_id:S1 objetivo_id:O2`) a cada nova tarefa consome a agilidade do Taskwarrior e eleva a carga cognitiva.
*   **Margem de Erro Humano:** Aumenta a propensão de quebrar a filtragem e as ligações relacionais de contrato devido a um erro de digitação (gerando uma "Metadado Órfão", pois o TW não tem *Foreign Keys* para validação instantânea sem scripts externos massivos).

### Estratégia de Mitigação: Vínculos Enxutos por Contrato

Para manter o TW focado exclusivamente e proteger sua usabilidade, mitigaremos o uso extensivo de UDAs manuais.

**O Contrato Relacional Forte, mas "Off-Chain":**
O Taskwarrior deve carregar apenas o "Minimo Produto Viável" de metadados necessários para ligar-se à malha central (O Data-Mesh).

*   **Chave Estrangeira Única (Single FK):** Em vez do TW exigir `sonho`, `objetivo`, `meta` e `projeto`, o TW recebe apenas o "Nó Folha" do Backlogger em forma do UDA nativo `project` (Ex: `project:O2.M3.Backlog`).
*   **Resolução pelo Data-Mesh:** Quando o algoritmo do Data-Mesh puxa o JSON do Taskwarrior para gerar métricas, ele lê a Chave. *Ele (o Mesh)* já conhece toda a árvore relacional (`S1 -> O2 -> M3`) em seu próprio banco. O Data-Mesh enriquece os dados downstream unindo o *Task Status* e o *Time Log* com o *Strategic Map* automaticamente.
*   **Sem Fricção:** O usuário no dia a dia do Taskwarrior digita `task add "Implementar API" project:O2.M3` e dá play. O sistema de Planejamento garante as ligações acima. Caso haja erro de digitação (`project:O2.M9`), o script do Data-Mesh emitirá um alerta de integridade no momento da sincronização/leitura dos dados, garantindo consistência sem onerar a ferramenta de execução de comando.

**Conclusão:** Taskwarrior e seu irmão Timewarrior existirão em perfeita sincronia com a macro-organização por meio dessa arquitetura tipada de Contratos, sem a fragilidade de hooks locais excessivos, operando seu ciclo vital independentemente.
