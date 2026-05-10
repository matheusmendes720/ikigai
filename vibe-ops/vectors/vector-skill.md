# 💼 Vetor Skill: Deep Work e Aprendizado Contínuo

## Significado Estratégico

O vetor **Skill** representa o torque técnico do sistema — a capacidade de gerar valor através do conhecimento e da execução de alta qualidade. É o vetor de *"Habilidade"*: o quanto você é bom no que faz, e o quanto você investe para ficar melhor.

No modelo IKIGAi, este vetor responde à pergunta: *"No que você é bom?"*

- **Atividades:** Estudo de algoritmos, leitura técnica, prototipagem, engenharia de software, revisão de código
- **Função sistêmica:** O substrato produtivo. Todo o valor gerado nos vetores Market e Revenue depende da qualidade do capital acumulado aqui.
- **Máxima:** *"O Deep Work é o único caminho para diferenciação em um mercado commodity."*

---

## Bloco Operacional: Deep Work (Build to Learn)

| Tipo de Dia | Janela | Setpoint | Pomodoros |
|:------------|:-------|:---------|:----------|
| Com Curso (Seg-Sex) | 04:45-06:15 | 90 min | 1 round (50+10) |
| Sem Curso (Sáb-Dom) | 04:45-09:45 | 300 min (5h) | 5 rounds (50+10) |
| Overclocking (Emergência) | 04:45-10:45 | 360 min (6h) | 6 rounds (50+10) |

### Sub-blocos de Deep Work

| Sub-bloco | Duração | Atividade | Ferramenta |
|:----------|:--------|:----------|:-----------|
| Lectio Densa | 25-50 min | Leitura de documentação/livro técnico | Obsidian + PDF |
| Codificação Algorítmica | 50 min | Implementar conceito estudado em código | VS Code |
| Prototipagem | 50 min | Construir MVP de ideia nova | VS Code / Jupyter |
| Revisão de Código | 25 min | Revisar código próprio ou de projetos | GitHub / Git |

---

## Contrato de Dados no Data-Mesh

### Frontmatter (Sonho/Objetivo)

```yaml
ikigai_vectors:
  skill: 0.9   # Quanto este sonho/objetivo desenvolve sua habilidade técnica
```

### Taskwarrior

Tasks deste vetor são injetadas pelo pipeline a partir dos checklists Markdown de estudo:

```bash
# Injetada pelo pipeline:
# task add "Estudar: Capítulo 7 — Graph Algorithms" project:S1.O2.M3.proj_study +phase:learn +study +algorithms size:4h

# Comandos do operador (Read-and-Execute Only):
task ready project:S1.O2.M3.proj_study
task 42 start   # Timewarrior liga automaticamente
task 42 done    # Atualiza burndown + reverse sync
```

**Tags recomendadas:**
- `phase:learn` — Fase IKIGAi
- `study` — Domínio de aprendizado
- `algorithms`, `backend`, `data`, `devops` — Área técnica
- `@vscode`, `@obsidian` — Contexto de ferramenta

**UDAs injetadas pelo pipeline:**
- `upstream_id` — FK para o planning
- `size` — Estimativa: `1h`, `4h`, `2d`
- `revenue_impact` — `NONE` ou `LOW` (investimento, não retorno imediato)

### Timewarrior

```bash
# Iniciar sessão de Deep Work
timew start @vscode phase:learn study algorithms project:S1.O2.M3.proj_study

# Parar
timew stop

# Relatório semanal de estudo
timew summary @vscode phase:learn :week
```

**Tags oficiais do vetor no Timewarrior:**
- `phase:learn` — Fase IKIGAi
- `@vscode` — Contexto de IDE
- `@obsidian` — Contexto de leitura/notas
- `study`, `prototyping`, `review` — Sub-atividade

---

## Pydantic Model (Referência)

```python
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List

class StudySession(BaseModel):
    """
    Modelo para uma sessão de Deep Work/Estudo registrada no Timewarrior.
    Usado no Reverse Sync para popular DailyMetrics.hours_learn.
    """
    date: date
    topic: str = Field(..., description="Tópico estudado: 'Graph Algorithms', 'JWT Auth'")
    modality: str = Field(..., description="lectio | coding | prototyping | review")
    duration_minutes: int = Field(gt=0, le=300)
    phase_tag: str = "phase:learn"
    context_tags: List[str] = Field(default_factory=list)  # @vscode, @obsidian
    project_key: Optional[str] = None  # S1.O2.M3.proj_study
    notes_extracted: Optional[str] = None  # Resumo do aprendizado (para Content Lab)

    @property
    def duration_hours(self) -> float:
        return self.duration_minutes / 60

    @property
    def content_ready(self) -> bool:
        """Retorna True se há notas suficientes para gerar conteúdo (Content Lab)."""
        return self.notes_extracted is not None and len(self.notes_extracted) > 100
```

---

## KPIs e Métricas

### Input Manual (Morning Survey + End-of-Session)

| Métrica | Tipo | Frequência | Fonte |
|:--------|:-----|:-----------|:------|
| `focus_level` | int (1-10) | Por sessão | Auto-avaliação pós-pomodoro |
| `comprehension_score` | int (1-10) | Por sessão | Quanto do material foi absorvido |
| `notes_extracted` | string | Por sessão | Resumo escrito no Obsidian |

### Computado (Reverse Sync)

| Métrica | Fórmula | Alvo Semanal |
|:--------|:--------|:-------------|
| `hours_learn` | Soma de Timewarrior `phase:learn` | ≥ 17.5h |
| `pomodoros_learn` | Soma de rounds 50+10 | ≥ 21 rounds |
| `topics_covered` | COUNT(DISTINCT topic) | ≥ 3 tópicos |
| `content_ready_sessions` | COUNT WHERE notes_extracted > 100 | ≥ 50% das sessões |

### Métricas de Qualidade

| Métrica | Fórmula | Interpretação |
|:--------|:--------|:--------------|
| `comprehension_rate` | `AVG(comprehension_score)` / 10 | > 0.7 = aprendizado efetivo |
| `focus_consistency` | Sessões com focus > 7 / total | > 0.8 = ritmo sustentável |
| `theory_practice_ratio` | `hours_lectio / hours_coding` | 0.4-0.6 = equilíbrio ideal |

### Alertas do Hypervisor

| Condição | Ação |
|:---------|:-----|
| `hours_learn < 10h/semana` | 🔴 Alerta: "Sub-investimento em habilidade — estagnação técnica" |
| `comprehension_rate < 0.5` | 🟡 Mudar modalidade: reduzir lectio, aumentar coding |
| `theory_practice_ratio > 1.0` | 🟡 Alerta: "Muito teoria, pouca prática — paralisia analítica" |
| `content_ready_sessions < 30%` | 🟡 Lembrete: "Documentar aprendizados para Content Lab" |

---

## Equação de Eficiência do Vetor

A eficiência do vetor Skill é calculada como:

```
η_skill = (hours_learn_real / hours_learn_setpoint) × comprehension_rate × focus_consistency
```

- Se `η_skill < 0.5`: O método de estudo está falhando. Diagnosticar e ajustar.
- Se `η_skill > 1.0`: Capacidade de absorção está no pico. Acelerar o pipeline de estudo.

---

## Conexão com Content Lab (Subproduto)

O vetor Skill gera o **input mais valioso** para o vetor Market:

```
Deep Work Session
  ├── notes_extracted → Content Lab Raw Material
  ├── code_snippets → GitHub Gist / Post técnico
  └── insights → LinkedIn / Blog post
```

**Regra de Ouro:** *"Não leia sem o VS Code aberto. Cada axioma teórico deve virar um comentário ou uma linha de código."*

---

## Dashboard: Visualização do Vetor

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    💼 DASHBOARD SKILL — SEMANA 19                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  HORAS DE DEEP WORK                                                     │
│  ├── Meta: 17.5h   │    Real: 15.2h   │    Status: 🟡 87%               │
│  ██████████████████████████████████████████████████████░░░░             │
│                                                                         │
│  POMODOROS COMPLETADOS                                                  │
│  ├── Meta: 21      │    Real: 19      │    Status: 🟡 90%               │
│  ████████████████████████████████████████████████░░░░                   │
│                                                                         │
│  TÓPICOS ESTUDADOS                                                      │
│  ├── Graph Algorithms      4.5h  ████████████████████████████████       │
│  ├── JWT Authentication    3.0h  ████████████████████████               │
│  ├── DuckDB Analytics      2.5h  ████████████████████                   │
│  └── System Design         5.2h  ████████████████████████████████████   │
│                                                                         │
│  QUALIDADE DAS SESSÕES                                                  │
│  ├── Compreensão média:  7.2/10  ✅                                     │
│  ├── Foco médio:         7.8/10  ✅                                     │
│  └── Sessões com notas:  14/19   (74%) 🟡                               │
│                                                                         │
│  SUBPRODUTOS GERADOS                                                    │
│  ├── Notas prontas para Content: 14                                     │
│  ├── Gists criados: 3                                                   │
│  └── Posts em draft: 2                                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Recomendações do Hypervisor por Fase

| Fase do Sistema | Ação no Vetor Skill |
|:----------------|:--------------------|
| **Fundação** (Build to Learn) | **Aumentar para 120%** — prioridade máxima |
| **Busca** (Market/Networking) | Manter 80% — tempo desviado para networking |
| **Hackathon** (Build to Earn) | Reduzir para 50% — foco em entrega |
| **Overclocking** (Emergência) | Reduzir para 40% — apenas manutenção |

---

> **Conexão com Data-Mesh:** Tasks de estudo são definidas em Markdown (`planning/`) com checklists tipadas. O pipeline compila para TaskPayload → injeta no TW com `phase:learn`. O Reverse Sync captura horas do Timewarrior e popula `DailyMetrics.hours_learn`. O Hypervisor usa `comprehension_score` e `focus_level` para ajustar setpoints.
