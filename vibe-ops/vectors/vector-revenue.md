# 💰 Vetor Revenue: Laborativo, Freelas e Geração de Renda

## Significado Estratégico

O vetor **Revenue** representa o fluxo de caixa e a monetização do sistema. É o vetor de *"Renda"*: o quanto você é pago pelo que faz, e o quanto você investe de tempo em atividades que geram retorno financeiro.

No modelo IKIGAi, este vetor responde à pergunta: *"Do que te pagam para fazer?"*

- **Atividades:** Codificação de projetos, freelas, entregáveis de clientes, busca ativa de vagas, entrevistas, propostas comerciais
- **Função sistêmica:** O motor econômico. Gera os recursos que permitem sustentar os outros vetores. Sem Revenue, Skill e Market não têm como se manter a longo prazo.
- **Máxima:** *"Build to Learn é sustentável; Build to Earn é necessário."*

---

## Bloco Operacional: Laborative (Build to Earn)

| Tipo de Dia | Janela | Setpoint | Pomodoros |
|:------------|:-------|:---------|:----------|
| Com Curso (Seg-Sex) | 14:00-17:00 | 180 min (3h) | 3 rounds (50+10) |
| Sem Curso (Sáb-Dom) | 12:45-17:45 | 300 min (5h) | 5 rounds (50+10) |
| Overclocking (Emergência) | 12:00-20:00 | 480 min (8h) | 8 rounds (50+10) |

### Sub-blocos de Laborative

| Sub-bloco | Duração | Atividade | Ferramenta |
|:----------|:--------|:----------|:-----------|
| Deep Code | 50 min | Codificação focada em entregáveis | VS Code |
| Client Sync | 25 min | Reuniões, feedback, revisões | Browser / Meet |
| Job Hunting | 50 min | Aplicações, networking direcionado | Browser |
| Proposta | 25 min | Escrever propostas, orçamentos | Markdown / Docs |

---

## Contrato de Dados no Data-Mesh

### Frontmatter (Sonho/Objetivo)

```yaml
ikigai_vectors:
  revenue: 0.6   # Quanto este sonho/objetivo gera retorno financeiro
```

### Taskwarrior

Tasks deste vetor são as entregas principais — projetos, freelas, e tarefas de busca de oportunidades:

```bash
# Injetada pelo pipeline:
# task add "Implementar endpoint de pagamentos" project:S1.O2.M3.proj_freela_01 +phase:earn +backend +freela size:8h

# Tarefas de job hunting:
task add "Aplicar para vaga de Backend na Empresa X" +phase:earn +jobhunting due:2026-07-20
```

**Tags recomendadas:**
- `phase:earn` — Fase IKIGAi
- `freela`, `jobhunting`, `project` — Tipo de atividade
- `backend`, `frontend`, `data` — Área técnica
- `@vscode`, `@browser` — Contexto de ferramenta

**UDAs injetadas pelo pipeline:**
- `upstream_id` — FK para o planning
- `size` — Estimativa: `4h`, `2d`, `1w`
- `revenue_impact` — `HIGH` ou `CRITICAL` (este vetor prioriza retorno)

### Timewarrior

```bash
# Iniciar sessão de Laborative
timew start @vscode phase:earn freela backend project:S1.O2.M3.proj_freela_01

# Job hunting
timew start @browser phase:earn jobhunting

# Relatório semanal de laborativo
timew summary @vscode @browser phase:earn :week
```

**Tags oficiais do vetor no Timewarrior:**
- `phase:earn` — Fase IKIGAi
- `@vscode` — Contexto de IDE (coding)
- `@browser` — Contexto de navegador (job hunting, client sync)
- `freela`, `jobhunting`, `project`, `proposal` — Sub-atividade

---

## Pydantic Model (Referência)

```python
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List
from enum import Enum

class RevenueType(str, Enum):
    FREELA = "freela"
    JOB_HUNTING = "jobhunting"
    PROJECT = "project"
    PROPOSAL = "proposal"
    CLIENT_SYNC = "client_sync"

class RevenueSession(BaseModel):
    """
    Modelo para uma sessão de Laborative registrada no Timewarrior.
    Usado no Reverse Sync para popular DailyMetrics.hours_earn.
    """
    date: date
    revenue_type: RevenueType
    client_or_company: Optional[str] = None
    duration_minutes: int = Field(gt=0, le=480)
    phase_tag: str = "phase:earn"
    project_key: Optional[str] = None  # S1.O2.M3.proj_freela_01
    billed: bool = False  # Se o tempo foi faturado
    hourly_rate: Optional[float] = None  # R$/hora

    @property
    def duration_hours(self) -> float:
        return self.duration_minutes / 60

    @property
    def estimated_revenue(self) -> Optional[float]:
        """Estimativa de receita para esta sessão."""
        if self.hourly_rate and self.billed:
            return self.duration_hours * self.hourly_rate
        return None

class JobApplication(BaseModel):
    """
    Modelo para rastrear aplicações de vagas.
    """
    date: date
    company: str
    role: str
    platform: Optional[str] = None  # linkedin, indeed, etc.
    status: str = Field(default="applied", pattern=r'^(applied|screening|interview|offer|rejected|ghosted)$')
    follow_up_date: Optional[date] = None

    @property
    def days_since_application(self) -> int:
        return (date.today() - self.date).days
```

---

## KPIs e Métricas

### Input Manual (End-of-Task)

| Métrica | Tipo | Frequência | Fonte |
|:--------|:-----|:-----------|:------|
| `hourly_rate` | float (R$) | Por freela | Contrato/fatura |
| `billed` | bool | Por sessão | Check manual |
| `application_count` | int | Semanal | Contagem manual |

### Computado (Reverse Sync)

| Métrica | Fórmula | Alvo Semanal |
|:--------|:--------|:-------------|
| `hours_earn` | Soma de Timewarrior `phase:earn` | ≥ 30.0h |
| `pomodoros_earn` | Soma de rounds 50+10 | ≥ 36 rounds |
| `revenue_estimated` | `SUM(estimated_revenue)` | ≥ R$ 500 (freela) |
| `applications_sent` | COUNT(JobApplication) | ≥ 5/semana |

### Métricas de Eficiência

| Métrica | Fórmula | Interpretação |
|:--------|:--------|:--------------|
| `revenue_per_hour` | `revenue_estimated / hours_earn` | Produtividade financeira |
| `application_conversion` | `interviews / applications_sent` | Eficácia de job hunting |
| `billable_ratio` | `hours_billed / hours_earn` | Quanto do tempo é faturável |

### Alertas do Hypervisor

| Condição | Ação |
|:---------|:-----|
| `hours_earn < 20h/semana` | 🔴 Alerta: "Fluxo de caixa em risco — ativar modo Busca" |
| `application_conversion < 5%` | 🟡 Revisar CV/portfólio; aumentar Skill em 20% |
| `billable_ratio < 30%` | 🟡 Muito tempo não-faturável — otimizar pipeline de propostas |
| `revenue_per_hour < R$ 30` | 🟡 Reavaliar precificação ou tipo de projeto |
| `applications_sent = 0` por 2 semanas | 🔴 Prioridade máxima: switch para fase Busca |

---

## Equação de Eficiência do Vetor

A eficiência do vetor Revenue é calculada como:

```
η_revenue = (hours_earn_real / hours_earn_setpoint) × billable_ratio × (revenue_per_hour / target_rate)
```

- Se `η_revenue < 0.5`: O motor econômico está falhando. Aumentar Market em 50%.
- Se `η_revenue > 1.0`: Sistema financeiro saudável. Pode investir mais em Skill.

---

## Integração com fin_ops

O vetor Revenue se conecta diretamente ao sistema financeiro (`fin_ops`):

```
Laborative Session
  ├── hours_earned ──→ fin_ops (tracking de horas)
  ├── revenue_estimated ──→ fin_ops (previsão de receita)
  └── billed = true ──→ fin_ops (faturamento real)
```

**Regra de Ouro:** *"Todo hora de Laborative deve ser rastreada no Timewarrior e refletida no fin_ops."*

---

## Dashboard: Visualização do Vetor

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    💰 DASHBOARD REVENUE — SEMANA 19                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  HORAS LABORATIVE                                                       │
│  ├── Meta: 30.0h   │    Real: 28.3h   │    Status: ✅ 94%               │
│  ████████████████████████████████████████████████████████████████░░░    │
│                                                                         │
│  RECEITA ESTIMADA                                                       │
│  ├── Meta: R$ 500  │    Real: R$ 480  │    Status: 🟡 96%               │
│  ├── Freela A: R$ 320 (16h @ R$ 20/h)                                  │
│  └── Freela B: R$ 160 (8h @ R$ 20/h)                                   │
│                                                                         │
│  TAXA HORÁRIA MÉDIA                                                     │
│  ├── R$ 20.00/h  │  Meta: R$ 25.00/h  │  Status: 🟡 80%                 │
│                                                                         │
│  JOB HUNTING                                                            │
│  ├── Aplicações: 5                                                      │
│  ├── Entrevistas: 1                                                     │
│  ├── Propostas: 1                                                       │
│  └── Taxa de conversão: 20% ✅                                          │
│                                                                         │
│  BILLABLE RATIO                                                         │
│  ├── Horas faturáveis: 24h                                              │
│  ├── Horas não-faturáveis: 4.3h                                         │
│  └── Ratio: 85% ✅                                                      │
│                                                                         │
│  🧠 RECOMENDAÇÃO DO HYPERVISOR:                                        │
│  "Revenue está no alvo. Aumentar taxa horária para R$ 25/h            │
│   na próxima proposta. Converter entrevista em oferta."               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Recomendações do Hypervisor por Fase

| Fase do Sistema | Ação no Vetor Revenue |
|:----------------|:----------------------|
| **Fundação** (Build to Learn) | Manter 40% — foco em portfólio, não em faturamento |
| **Busca** (Market/Networking) | Aumentar para 80% — aproveitar oportunidades geradas |
| **Hackathon** (Build to Earn) | **Aumentar para 120%** — prioridade máxima de entrega |
| **Overclocking** (Emergência) | **Aumentar para 150%** — deadline/crítico |

---

## Conexão com GnuCash / fin_ops

O pipeline do Data-Mesh deve exportar dados do vetor Revenue para o sistema contábil:

| Dado | Fonte | Destino | Formato |
|:-----|:------|:--------|:--------|
| Horas por projeto | Timewarrior `phase:earn` | fin_ops CLI | JSON |
| Receita estimada | RevenueSession | fin_ops | BRL float |
| Despesas operacionais | fin_ops track | GnuCash | SQLite/CSV |
| DRE mensal | fin_ops report | Dashboard | Consolidado |

---

> **Conexão com Data-Mesh:** Tasks de Laborative são injetadas pelo pipeline (`planning/`). O Reverse Sync captura horas do Timewarrior (`phase:earn`) e popula `DailyMetrics.hours_earn`. O Hypervisor cruza com `fin_ops` para calcular `revenue_per_hour` e `billable_ratio`, ajustando setpoints de Market e Skill conforme a saúde financeira.
