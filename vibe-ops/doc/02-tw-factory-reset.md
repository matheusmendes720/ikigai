# Rollback Estratégico e Prática Vanilla

Antes de orquestrar a malha complexa de integrações e APIs detalhada nos documentos anteriores, é imperativo que o operador domine profundamente as engrenagens básicas do Taskwarrior e do Timewarrior.

Este documento formaliza a fase temporal atual: **Um "Rollback" metodológico completo**.

## O Objetivo: Domínio do Terminal e Ciclo Basilar

1. **Por que o Rollback?** Não se pode otimizar o que não se compreende perfeitamente em sua essência. O excesso de aliases (ex: comandos aglutinados que fazem três coisas simultâneas) e URIs repletos de ganchos obscurecem como o sistema calcula urgência, dependências e filtros em seu código base (Vanilla).
2. **Ambiente Escolhido:** A prática diária ocorrerá estritamente através do binário executando em ambiente nativo Linux via *WSL (Windows Subsystem for Linux)* interligado pelo Windows Terminal, proporcionando a experiência raiz e estável com bash/zsh sem complexidades de adaptação para Windows.

## O Escopo do Rollback ("Factory Reset")

A restauração de um estado purista (Vanilla) exige desativar temporariamente as adaptações prévias do `.taskrc` e de `bashrc/profile`:

### 1. Limpeza de Arquivos de Extensão e Relatórios
- **Remover UDAs excessivos do config:** O arquivo `~/.taskrc` deve ser "limpo" de todo formulário ou atributo que tente emular árvores hierárquicas. Retornaremos ao padrão (`project`, `due`, `tags`, `priority`, `depends`).
- **Desativar Scripts de Hooks (`on-add`, `on-modify`, etc.):** Para que nenhuma mágica assíncrona aconteça por trás dos panos sem a permissão explícita do usuário. Queremos observar o comportamento puro de cada comando `task add`.
- **Exclusão de Aliases de Terminal:** Desfazer os atalhos mágicos (`t`, `tadd`, etc.) para criar memória muscular nativa nos comandos literais da documentação original.

### 2. O Processo de Prática e Estudo Isolado

As próximas etapas concentram-se na documentação oficial e na operação manual (o oposto da visão de automação final, mas essencial para chegar lá com integridade):

*   **Leitura Contínua da Documentação Oficial:** Aprofundamento no "urgency_polynomial", em como `virtual tags` funcionam (como `+OVERDUE`) e dominar o `task filter` e comandos complexos de manipulação em lote.
*   **Gestão de Tarefas Reais em Lote Mínimo:** Processar demandas reais e controladas do dia a dia diretamente no terminal Linux sem o auxílio de integrações Markdown.

## Caminho para a Interoperabilidade (Next Steps)

Assim que o domínio sobre o uso interativo manual na linha de comando estiver enraizado (memória mecânica e intuição de dependências/filtros naturalizada):

1. Compreenderemos com clareza cristalina **onde** o Data-Mesh deve intervir.
2. Reconectaremos os blocos de dados gradualmente através da API Push, não como UDAs inflados no `.taskrc`, mas como scripts off-chain que geram o JSON/Comandos prontos e os entregam ao sistema.

**Conclusão Temporária:** Desconstruir para reconstruir melhor. A execução diária a partir de agora é no terminal purista dentro do WSL. A construção da Engenharia Estratégica (Arquitetura Mesh) permanecerá como documentação no plano de fundo até o amadurecimento mecânico do uso.
