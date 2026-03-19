# Relatório: Propostas de Soluções e Extensões para Taskwarrior

Este relatório apresenta soluções técnicas para superar as limitações do Taskwarrior "Vanilla" identificadas na análise anterior, utilizando hooks, plugins e ferramentas da comunidade.

---

## 1. Automação de Herarquia e Metadados (Orquestração)

**Problema:** Fadiga ao preencher múltiplos UDAs manualmente.
**Solução:** **Hooks de Auto-Propagação (`on-add`)**.

- **Mecânica:** Utilizar a nomenclatura do projeto como "Parser". Exemplo: Ao criar uma tarefa no projeto `S1.O2.M3.T4`, um hook em Python quebra a string e preenche automaticamente os UDAs `sonho_id:S1`, `objetivo_id:O2`, etc.
- **Ferramenta:** [tasklib (Python API)](https://github.com/GothenburgBitFactory/tasklib).
- **Benefício:** Reduz o comando de 50 caracteres para 10, mantendo a integridade analítica.

## 2. O Vazio Narrativo e Journaling

**Problema:** Taskwarrior não é bom para anotações qualitativas extensas.
**Solução:** **[Taskwiki (Integração Vim/Neovim)](https://github.com/tools-life/taskwiki)**.

- **Mecânica:** Permite que você visualize e edite suas tarefas do Taskwarrior dentro de arquivos Markdown do Vimwiki. Você pode escrever parágrafos inteiros de "Rotina Final" abaixo de uma tarefa, e o Taskwiki sincroniza o status.
- **Benefício:** Une o rigor do banco de dados (TW) com a flexibilidade da escrita (Markdown/Journaling).

## 3. Inteligência Temporal (Dias Úteis)

**Problema:** `due:today+15d` não respeita dias úteis ou feriados.
**Solução:** **Hook de Ajuste de Boundary (`on-add/on-modify`)**.

- **Mecânica:** Um hook intercepta a data de vencimento e utiliza a biblioteca **[Python-Business-Days](https://pypi.org/project/business-days/)** para "empurrar" o prazo para o próximo dia útil.
- **Benefício:** Automação total dos ciclos de 45 dias úteis sem cálculo manual do usuário.

## 4. Visualização e Dashboards (Feedback Loop)

**Problema:** Falta de interface visual e métricas em tempo real.
**Soluções:**

- **[VIT (Visual Interactive Taskwarrior)](https://github.com/vit-project/vit):** Interface TUI que permite navegar por projetos e objetivos com comandos rápidos.
- **[Taskwarrior-tui](https://github.com/kdheepak/taskwarrior-tui):** Dashboard moderno para terminal com suporte a mouse e visualização em colunas.
- **[Taskwarrior-web](https://github.com/tmahmood/taskwarrior-web):** Interface web leve para visualização rápida.

## 5. Integridade Relacional (Validação)

**Problema:** Possibilidade de criar IDs de sonhos/objetivos inválidos.
**Solução:** **Hook de Validação (`on-add`)**.
- **Mecânica:** O hook consulta um arquivo central de configuração (`strategics/hierarquia.json`) e rejeita a criação da tarefa se o `objetivo_id` não for válido.
- **Benefício:** Garante que o banco de dados do Taskwarrior nunca fique "sujo" com referências órfãs.

## 6. Rastreamento de Tempo e ROI (Retorno sobre Investimento)

**Problema:** Dificuldade em medir o tempo real gasto em relação ao planejado (Time Blocking).
**Solução:** **[Timewarrior (Nativo)](https://timewarrior.net/)** + **[Trackwarrior](https://github.com/gkssjovi/trackwarrior)**.
- **Mecânica:** O Timewarrior integra-se perfeitamente com o Taskwarrior. Ao iniciar uma tarefa (`task 1 start`), o cronômetro começa automaticamente.
- **Benefício:** Permite gerar relatórios de "Custo x Benefício" (ROI), essencial para o objetivo de "fonte de renda com programação".

---

## Limitações do Modelo "Fully Bounded" (Somente Taskwarrior)

Embora as extensões acima resolvam a maioria dos problemas, manter-se **estritamente** dentro do ecossistema Taskwarrior traz riscos:

1. **Complexidade de Manutenção:** Quanto mais hooks você adiciona, mais "frágil" o sistema se torna. Um erro em um script Python de validação pode impedir você de adicionar qualquer tarefa até que o bug seja corrigido.
2. **Dependência de Ambiente:** O sistema deixa de ser "portável apenas com o binário". Você precisará garantir que o Python, as bibliotecas (`tasklib`, `business_days`) e os scripts de hooks estejam presentes em toda máquina que usar.
3. **User Experience (UX) Silenciada:** O Taskwarrior nunca será uma "ferramenta de planejamento visual" (como um Gantt ou Mindmap). Tentar forçar visualizações complexas no terminal via `task export` + scripts de desenho sempre será inferior a ferramentas nativas de visualização.
4. **Silo de Dados:** Se no futuro você precisar integrar seus dados com ferramentas de finanças (GnuCash) ou levantamento de renda, o formato JSON do Taskwarrior precisará de yet-another-bridge.

## Veredito Técnico

A melhor estratégia **não é** tentar fazer o Taskwarrior fazer tudo, mas sim usá-lo como o **Motor de Estados (State Machine)** e delegar a **Narrativa** para o Taskwiki e a **Análise** para scripts de exportação desacoplados.

---

## Referências e Links Oficiais

Aqui estão os links para as ferramentas e bibliotecas mencionadas:

- **Taskwarrior (Core):** [taskwarrior.org](https://taskwarrior.org/)
- **Timewarrior (Time Tracking):** [timewarrior.net](https://timewarrior.net/)
- **Tasklib (Python API):** [github.com/GothenburgBitFactory/tasklib](https://github.com/GothenburgBitFactory/tasklib)
- **Taskwiki (Vim/Neovim Integration):** [github.com/tools-life/taskwiki](https://github.com/tools-life/taskwiki)
- **VIT (Visual Interactive Taskwarrior):** [github.com/vit-project/vit](https://github.com/vit-project/vit)
- **Taskwarrior-tui:** [github.com/kdheepak/taskwarrior-tui](https://github.com/kdheepak/taskwarrior-tui)
- **Taskwarrior-Kusarigama (Plugin System):** [github.com/yanick/Taskwarrior-Kusarigama](https://github.com/yanick/Taskwarrior-Kusarigama)
- **Tasksh (Shell Interactive):** [github.com/GothenburgBitFactory/tasksh](https://github.com/GothenburgBitFactory/tasksh)
- **Trackwarrior (Integração TW-TimeW):** [github.com/gkssjovi/trackwarrior](https://github.com/gkssjovi/trackwarrior)
- **Python-Business-Days (Lógica de dias úteis):** [pypi.org/project/business-days/](https://pypi.org/project/business-days/)
