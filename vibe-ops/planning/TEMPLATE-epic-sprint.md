# Template: Planejamento de Épico e Sprint (PRD-04)

Este template é utilizado para desdobrar um Épico (Epic) em uma Sprint operável, mapeando o esforço (Burndown) e a relação com o Taskwarrior.

---

## 1. Definição do Épico (Epic)

- **Título do Épico:** [Nome claro do Épico]
- **Projeto Base:** [SoftwareProject ou StudyProject vinculado]
- **IKIGAi Vetores Focados:** [ ] Passion / [ ] Skill / [ ] Market / [ ] Revenue
- **Peso Estratégico (Weight 1.0 a 5.0):** [ ]
- **Estimativa Total (Epic):** [X] horas

### Critérios de Aceitação (Definition of Done)
1. [ ] Critério 1 (Ex: Pipeline de CI/CD rodando e aprovada)
2. [ ] Critério 2 (Ex: Cobertura de testes > 80%)
3. [ ] Critério 3 (Ex: Documentação de arquitetura atualizada)

---

## 2. Configuração da Sprint (Sensor de Capacidade)

- **Sprint ID/Nome:** `sprint-[numero]-[tema]`
- **Data de Início:** [YYYY-MM-DD]
- **Data de Término:** [YYYY-MM-DD]
- **Meta da Sprint (Goal):** [A única coisa que se não for feita, a sprint fracassou]
- **Velocity Alvo (Horas/Pts):** [Capacidade alocada para esta sprint]

---

## 3. Backlog da Sprint (Task Breakdown)
*Quebre o épico em tarefas atômicas (idealmente < 4h). Estas tarefas serão sincronizadas com o Taskwarrior.*

| Task (Título) | Prioridade (H/M/L) | Energia (H/M/L) | Estimativa (h) | Tags | Cognitive Debt | Status |
|---|:---:|:---:|:---:|---|:---:|---|
| [Ex: Configurar banco SQLite-vec] | H | H | 2.5 | `backend`, `db` | [x] Sim / [ ] Não | `[ ]` |
| [Ex: Criar Pydantic models] | M | M | 1.0 | `backend`, `models`| [ ] Sim / [x] Não | `[ ]` |
| [Ex: Escrever testes unitários] | L | L | 2.0 | `tests` | [ ] Sim / [x] Não | `[ ]` |
| ... | ... | ... | ... | ... | ... | ... |

*(Nota: Tarefas com Cognitive Debt "Sim" devem gerar um `TEMPLATE-micro-ciclo.md` associado para garantir o aprendizado focado).*

---

## 4. Avaliação de Risco e Dependências
- **Bloqueios Conhecidos:** [Ex: Preciso de aprovação de API externa?]
- **Dívida Técnica Adquirida (aceita):** [Ex: Vamos mockar o serviço X por enquanto]
- **Riscos de Tempo/Foco:** [Ex: Semana com muitas reuniões externas]

## 5. Revisão Pós-Sprint (Velocity & Burndown)
*Preenchido ao fechar a Sprint.*

- **Velocity Realizado:** [X] horas/pts
- **Epic Burndown Restante:** [Y] horas
- **Comentários Rápidos:** [Onde erramos a estimativa?]
