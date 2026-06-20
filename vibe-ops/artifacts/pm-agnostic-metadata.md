# ⚙️ Project Management via Metadata: An Agnostic Foundation

> Fonte: Referência arquitetural para tooling PM agnóstico — compatível com Dataview, scripts Python e agentes MCP.  
> Injetado em: 2026-05-18

---

## Objetivo

Tratar o vault Obsidian como um **data store estruturado**. Separar o conteúdo bruto (o "quê") do estado estrutural (o "onde no workflow"). Ao padronizar o frontmatter e a estrutura de diretórios, o vault se torna legível por qualquer automação futura, servidor MCP agentic ou linguagem de query simples.

---

## Foundational PM Schema

Schema que descreve o estado de uma entidade, não a ferramenta. Bloco de workflow unificado para consistência entre arquivos de projeto.

```yaml
---
type: project-task
project-id: <uuid-or-shortcode>
status: [backlog, ready, in-progress, blocked, done]
phase: [initiation, design, execution, validation, closure]
priority: [P0, P1, P2]
effort-estimate: <number>
assigned-to: [self, agent-x]
last-updated: 2026-05-16
---
```

### Por que este schema é agentic-ready:
- **`type` field**: Permite filtragem programática (`WHERE type = "project-task"`), garantindo que scripts não processem notas destinadas a outros fins.
- **Valores enumerados**: Agentes performam melhor com um conjunto fechado de transições de estado.
- **`project-id`**: Habilita mapeamento relacional mesmo que notas sejam movidas entre pastas — essencial para análise por agentes baseados em grafos.

---

## Desenvolvendo Tooling Agnóstico

### 1. O Padrão "State Machine"

Não apenas rastrear `status`; rastrear **transições**. Usar propriedade `log` ou nota vinculada com timestamp.

- **Estratégia agnóstica**: Em vez de depender da UI de um plugin para mover uma tarefa, escrever um script simples (Python/Node/DataviewJS) que atualiza o campo `status` e adiciona um timestamp a um campo de metadata `audit-trail`.
- **Benefício**: Quando um agente AI acessa o vault, ele lê o `audit-trail` para entender o histórico, não apenas o status estático atual.

### 2. MOCs Padronizados (Metadata Orchestration Centers)

Criar notas "Orchestrator" que servem como entry point para os agentes.

```yaml
---
orchestrator-type: project-board
target-project: <project-id>
---
```

- **Benefício**: Um agente pode escanear o vault por todas as notas onde `orchestrator-type` está definido, construindo automaticamente seu próprio knowledge graph das estruturas de projeto ativas.

### 3. Lógica Desacoplada (A Abordagem MCP)

Ao desenvolver tooling, construir **servidores MCP** em vez de plugins específicos do Obsidian.

- Ao criar um servidor MCP que interage com o filesystem, você pode trocar Obsidian por qualquer outro editor de markdown no futuro, e o "agentic workflow" continuará funcionando perfeitamente porque ele faz interface com o **data schema**, não com a interface da aplicação.

---

## Queries de Integridade de Dados

### Encontrando Metadata Inconsistente

```dataview
TABLE status, phase
FROM "Projects"
WHERE type = "project-task"
AND (status = null OR phase = null)
```

### Relatório de Saúde do Projeto

```dataview
TABLE rows.file.link AS "Tasks"
FROM "Projects"
WHERE type = "project-task"
GROUP BY status
```

---

## Pro-Tips para Workflows Customizados

- **Evitar Dados Aninhados**: Manter metadata flat. Agentes têm dificuldade para parsear objetos YAML profundamente aninhados. Se precisar de dados complexos, use uma nota vinculada.
- **Timestamping**: Sempre incluir campos `created-at` e `updated-at`. Agentes usam estes para calcular "drift" (quanto tempo uma tarefa ficou presa em `in-progress`).
- **Auto-documentação**: Criar uma nota `000SchemaDefinition.md` no vault. Quando um agente é inicializado, alimentar esta nota primeiro para que ele entenda suas convenções de tagging customizadas e estados de workflow.

---

## Explorações Futuras

- **Graph Traversal**: Se migrar para agentes Python customizados (ex: via LangChain ou OpenAI API padrão), considerar armazenar o frontmatter como JSON-LD dentro do markdown — padrão ouro para dados web legíveis por máquina.
- **Feedback Loop**: Se você se encontrar corrigindo metadata manualmente, construir um "Validation Agent" — um script que roda diariamente para verificar se todos os `project-tasks` têm um `project-id` e `status` válidos.

---

## Mapeamento para vibe-ops

| Conceito PM Agnóstico | Implementação atual no vibe-ops |
|---|---|
| `type: project-task` | `entity_type` no frontmatter do Obsidian → `planning_entities.entity_type` |
| `status` enum | `roadmap_sync.status` (pending / completed) |
| `audit-trail` | `IMPLEMENTATION_LOG.md` append-only |
| Orchestrator note | `CyberneticDailyLoop` como entry point programático |
| MCP server agnóstico | `SyncEngine` desacoplado do Obsidian — lê via frontmatter puro |
| Validation Agent | `BinaryKnowledgeTree` + `GapSearchEngine` |
| `project-id` relacional | `upstream_id` SHA-256 idempotente via `UEID Manager` |
