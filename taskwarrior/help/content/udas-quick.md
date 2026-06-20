# UDAs - Quick Reference

## Hierarchy UDAs

| UDA | Type | Level | Values | Purpose |
|-----|------|-------|--------|---------|
| `sonho_id` | string | Sonhos | any | Sonho identification |
| `objetivo_id` | string | Objetivos | obj_XXX_QX | Objetivo identification |
| `objetivo_trimestre` | string | Objetivos | Q1, Q2, Q3, Q4 | Quarter identification |
| `meta_ciclo` | numeric | Metas | 1-4 | Meta cycle (15 days) |
| `tarefa_microciclo` | numeric | Tarefas | 1-3 | Microcycle (5 days) |
| `bloco_tempo` | string | Atividades | Manhã, Tarde, Noite, Planejamento, Revisão | Time block |

## Strategic UDAs

| UDA | Type | Level | Values | Purpose |
|-----|------|-------|--------|---------|
| `ciclo` | numeric | Strategic | 1-4 | Strategic cycle (45 days) |
| `onda_numero` | numeric | Strategic | 1-3 | Wave number |

## Metrics & Analysis UDAs

| UDA | Type | Level | Values | Purpose |
|-----|------|-------|--------|---------|
| `taxa_conclusao` | numeric | Metrics | 0.00-100.00 | Completion rate |
| `barreira` | string | Analysis | Estrutural, Recurso, Habilidade, Motivacional | Barrier type |
| `teste_fogo_dimensao` | string | Teste de Fogo | Resiliência, Coerência, Eficiência, Adaptabilidade | Fire test dimension |

## Usage Examples

```bash
# Hierarchy
ta sonho_id:publicar-livro objetivo_id:obj_001_Q1 meta_ciclo:1 tarefa_microciclo:1 bloco_tempo:Tarde "Task"

# Strategic
ta ciclo:1 onda_numero:1 "Strategic task"

# Metrics
ta taxa_conclusao:75.5 barreira:Recurso "Task with metrics"
```
