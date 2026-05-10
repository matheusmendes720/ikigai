# 🎯 Vetor Market: Conteúdo, Visibilidade e Networking

## Significado Estratégico

O vetor **Market** representa a tração no mercado — a ponte entre o que você sabe fazer e o que o mundo precisa. É o vetor de *"Missão"*: o quanto o mundo precisa do que você oferece, e o quanto você está visível para quem precisa.

No modelo IKIGAi, este vetor responde à pergunta: *"Do que o mundo precisa?"*

- **Atividades:** Criar conteúdo técnico, postar no LinkedIn, participar de comunidades, networking ativo, mentorias, palestras
- **Função sistêmica:** O amplificador de sinal. Transforma o conhecimento acumulado no vetor Skill em oportunidades concretas (vagas, freelas, parcerias).
- **Máxima:** *"O melhor código do mundo não gera valor se ninguém souber que você escreveu."*

---

## Bloco Operacional: Content Lab (Build to Share)

| Tipo de Dia | Janela | Setpoint | Pomodoros |
|:------------|:-------|:---------|:----------|
| Com Curso (Seg-Sex) | 17:15-18:00 | 45 min | 1 round (25+5) ou contínuo |
| Sem Curso (Sáb-Dom) | 17:35-18:35 | 60 min | 1 round (50+10) |
| Overclocking (Emergência) | 17:15-17:45 | 30 min | Mínimo absoluto |

### Sub-blocos de Content Lab

| Sub-bloco | Duração | Atividade | Ferramenta |
|:----------|:--------|:----------|:-----------|
| Raw Capture | 10 min | Selecionar nota/código do dia | Obsidian |
| Polimento | 15-20 min | Transformar em post técnico | Obsidian / Markdown |
| Publicação | 10 min | Postar no LinkedIn / Blog / GitHub | Browser |
| Engajamento | 10 min | Responder comentários, interagir | Browser |

---

## Contrato de Dados no Data-Mesh

### Frontmatter (Sonho/Objetivo)

```yaml
ikigai_vectors:
  market: 0.7   # Quanto este sonho/objetivo atende à demanda do mercado
```

### Taskwarrior

Tasks deste vetor são tarefas de produção de conteúdo e networking:

```bash
# Injetada pelo pipeline:
# task add "Post: Como usei Graph Algorithms para otimizar rotas" project:S1.O2.M3.proj_content +phase:share +content +linkedin

# Tarefas ad-hoc de networking:
task add "Responder DMs de recrutadores" +phase:share +networking
```

**Tags recomendadas:**
- `phase:share` — Fase IKIGAi
- `content` — Produção de conteúdo
- `networking` — Interação social/profissional
- `linkedin`, `github`, `blog` — Plataforma
- `@browser` — Contexto de ferramenta

**UDAs injetadas pelo pipeline:**
- `upstream_id` — FK para o planning
- `size` — Estimativa: `30min`, `1h`
- `revenue_impact` — `MEDIUM` ou `HIGH` (networking gera oportunidades)

### Timewarrior

```bash
# Iniciar sessão de Content Lab
timew start @browser phase:share content linkedin

# Sessão de networking
timew start @browser phase:share networking

# Relatório semanal
timew summary @browser phase:share :week
```

**Tags oficiais do vetor no Timewarrior:**
- `phase:share` — Fase IKIGAi
- `@browser` — Contexto de navegador
- `content`, `networking`, `mentoria` — Sub-atividade
- `linkedin`, `github`, `blog` — Plataforma

---

## Pydantic Model (Referência)

```python
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List
from enum import Enum

class Platform(str, Enum):
    LINKEDIN = "linkedin"
    GITHUB = "github"
    BLOG = "blog"
    YOUTUBE = "youtube"
    COMMUNITY = "community"

class ContentSession(BaseModel):
    """
    Modelo para uma sessão de Content Lab registrada no Timewarrior.
    Usado no Reverse Sync para popular DailyMetrics.hours_share.
    """
    date: date
    content_type: str = Field(..., description="post | article | gist | video | comment")
    platform: Platform
    duration_minutes: int = Field(gt=0, le=120)
    phase_tag: str = "phase:share"
    topic: Optional[str] = None  # Tópico técnico do conteúdo
    upstream_note_id: Optional[str] = None  # FK para nota no Obsidian

    @property
    def duration_hours(self) -> float:
        return self.duration_minutes / 60

class NetworkingSession(BaseModel):
    """
    Modelo para sessões de networking.
    """
    date: date
    activity: str = Field(..., description="dm | call | event | mentorship | forum")
    platform: Optional[str] = None  # linkedin, discord, meetup
    duration_minutes: int = Field(gt=0, le=180)
    contacts_made: int = Field(ge=0, default=0)
    opportunities_generated: int = Field(ge=0, default=0)

    @property
    def roi_score(self) -> float:
        """Networking ROI: oportunidades por hora investida."""
        hours = self.duration_minutes / 60
        return self.opportunities_generated / hours if hours > 0 else 0.0
```

---

## KPIs e Métricas

### Input Manual (End-of-Session)

| Métrica | Tipo | Frequência | Fonte |
|:--------|:-----|:-----------|:------|
| `content_published` | bool | Por sessão | Checkbox manual |
| `engagement_score` | int (1-10) | Por post | Likes + comentários + shares (normalizado) |
| `contacts_made` | int | Por sessão | Contagem manual |

### Computado (Reverse Sync)

| Métrica | Fórmula | Alvo Semanal |
|:--------|:--------|:-------------|
| `hours_share` | Soma de Timewarrior `phase:share` | ≥ 5.75h |
| `posts_published` | COUNT WHERE content_published = true | ≥ 3 posts |
| `networking_hours` | Soma de `phase:share` + `networking` | ≥ 2h |
| `content_conversion_rate` | `posts_published / content_ready_sessions` | ≥ 60% |

### Métricas de Impacto

| Métrica | Fórmula | Interpretação |
|:--------|:--------|:--------------|
| `visibility_index` | `posts_published × AVG(engagement_score)` | Tração de marca pessoal |
| `network_velocity` | `contacts_made / networking_hours` | Eficiência de networking |
| `opportunity_rate` | `opportunities_generated / networking_hours` | Conversão de networking |

### Alertas do Hypervisor

| Condição | Ação |
|:---------|:-----|
| `hours_share < 3h/semana` | 🔴 Alerta: "Invisibilidade crítica — mercado não sabe que você existe" |
| `content_conversion_rate < 30%` | 🟡 Alerta: "Muitas notas, poucos posts — publicar é mais importante que perfeccionar" |
| `network_velocity < 2` | 🟡 Mudar estratégia: eventos > DMs frias |
| `opportunity_rate = 0` por 4 semanas | 🔴 Reduzir Skill em 10%, aumentar Market em 20% |

---

## Equação de Eficiência do Vetor

A eficiência do vetor Market é calculada como:

```
η_market = (hours_share_real / hours_share_setpoint) × content_conversion_rate × visibility_index_normalized
```

- Se `η_market < 0.4`: O operador é invisível no mercado. Aumentar setpoint em 50%.
- Se `η_market > 1.0`: Tração está no pico. Converter oportunidades em Revenue.

---

## Conexão com Skill (Input de Conteúdo)

O vetor Market consome o **output do vetor Skill** como matéria-prima:

```
Deep Work Session
  ├── notes_extracted ──→ Content Lab
  │                       ├── Polimento (15-20min)
  │                       └── Publicação (10min)
  └── code_snippets ────→ GitHub Gist
                          └── Post técnico
```

**Regra de Ouro:** *"O conteúdo de valor deve ser o log de erro e solução do seu dia."*

---

## Dashboard: Visualização do Vetor

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    🎯 DASHBOARD MARKET — SEMANA 19                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  HORAS DE CONTENT LAB                                                   │
│  ├── Meta: 5.75h   │    Real: 3.1h    │    Status: 🔴 54%               │
│  ██████████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░           │
│                                                                         │
│  POSTS PUBLICADOS                                                       │
│  ├── Meta: 3       │    Real: 2       │    Status: 🟡 67%               │
│  ├── Seg: "Graph Algorithms na prática" (LinkedIn)                     │
│  └── Sex: "DuckDB + Python para analytics local" (Blog)                │
│                                                                         │
│  ENGAGEMENT MÉDIO                                                       │
│  ├── 47 likes │ 12 comentários │ 3 shares │ Score: 6.2/10 🟡            │
│                                                                         │
│  NETWORKING                                                             │
│  ├── Horas: 1.5h                                                        │
│  ├── Contatos: 4                                                        │
│  └── Oportunidades: 1 (freela de data pipeline)                         │
│                                                                         │
│  CONVERSÃO DE CONTEÚDO                                                  │
│  ├── Sessões Deep Work: 19                                              │
│  ├── Notas prontas: 14                                                  │
│  ├── Posts publicados: 2                                                │
│  └── Taxa de conversão: 14% 🔴                                          │
│                                                                         │
│  🧠 RECOMENDAÇÃO DO HYPERVISOR:                                        │
│  "Market está 46% abaixo do alvo. Alocar 1h extra de Content Lab       │
│   na próxima semana. Converter 2 das 14 notas prontas em posts."       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Recomendações do Hypervisor por Fase

| Fase do Sistema | Ação no Vetor Market |
|:----------------|:---------------------|
| **Fundação** (Build to Learn) | Manter 60% — foco é acumular, não vender |
| **Busca** (Market/Networking) | **Aumentar para 150%** — prioridade máxima |
| **Hackathon** (Build to Earn) | Manter 80% — documentar o que está sendo construído |
| **Overclocking** (Emergência) | Reduzir para 30% — mínimo de visibilidade |

---

> **Conexão com Data-Mesh:** Tasks de conteúdo são criadas ad-hoc ou pelo pipeline (`planning/`). O Reverse Sync captura horas do Timewarrior (`phase:share`) e popula `DailyMetrics.hours_share`. O Hypervisor cruza `content_ready_sessions` (do vetor Skill) com `posts_published` para calcular `content_conversion_rate` e gerar recomendações.
