# ❤️ Vetor Passion: Saúde, Treino e Bem-Estar

## Significado Estratégico

O vetor **Passion** representa a sustentação física e emocional do sistema. É o "Reset de Cache" metabólico que impede o thermal throttling (burnout) do operador. Sem este vetor, todos os outros colapsam.

No modelo IKIGAi, este vetor responde à pergunta: *"O que você ama fazer?"*

- **Atividades:** Artes Marciais, Calistenia, Cardio, Meditação, Alongamento
- **Função sistêmica:** Dissipador de calor cognitivo. O treino físico quebra o ciclo de sobrecarga mental e restaura a capacidade de foco profundo.
- **Máxima:** *"O corpo é a infraestrutura sobre a qual todo o software roda."*

---

## Bloco Operacional: Training

| Tipo de Dia | Janela | Setpoint | Pomodoros |
|:------------|:-------|:---------|:----------|
| Com Curso (Seg-Sex) | 03:00-06:00 | 180 min (3h) | N/A (contínuo) |
| Sem Curso (Sáb-Dom) | 03:00-06:00 | 180 min (3h) | N/A (contínuo) |
| Overclocking (Emergência) | 03:00-05:00 | 120 min (2h) | N/A (reduzido) |

### Sub-blocos de Training

| Sub-bloco | Duração | Atividade | Intensidade |
|:----------|:--------|:----------|:------------|
| Boot Sequence | 15 min | Meditação + Hidratação | Baixa (preparação) |
| Strength | 60 min | Calistenia / Artes Marciais | Alta |
| Cardio | 30 min | Corrida / Pular corda | Média-Alta |
| Cool Down | 15 min | Alongamento / Respiração | Baixa |

---

## Contrato de Dados no Data-Mesh

### Frontmatter (Sonho/Objetivo)

```yaml
ikigai_vectors:
  passion: 0.8   # Quanto este sonho/objetivo alimenta sua paixão/saúde
```

### Taskwarrior

Tasks deste vetor são raras (o tracking é feito principalmente no Timewarrior), mas quando existem:

```bash
# Exemplo: tarefa de planejamento de treino
task add "Revisar programa de calistenia - Semana 3" project:S1.O2.M3.proj_health +phase:train +training
```

**Tags recomendadas:**
- `phase:train` — Fase IKIGAi
- `training` — Domínio
- `calistenia`, `muaythai`, `cardio` — Modalidade
- `morning` — Janela do dia

### Timewarrior

O tracking de tempo do vetor Passion é feito via Timewarrior:

```bash
# Iniciar bloco de training
timew start @training calistenia phase:train

# Parar
timew stop

# Relatório semanal de training
timew summary @training :week
```

**Tags oficiais do vetor no Timewarrior:**
- `@training` — Categoria principal
- `calistenia`, `muaythai`, `cardio`, `meditation` — Modalidades
- `phase:train` — Fase IKIGAi (para cruzamento com analytics)

---

## Pydantic Model (Referência)

```python
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional

class TrainingSession(BaseModel):
    """
    Modelo para uma sessão de training registrada no Timewarrior.
    Usado no Reverse Sync para popular DailyMetrics.hours_train.
    """
    date: date
    modality: str = Field(..., description="calistenia | muaythai | cardio | meditation")
    duration_minutes: int = Field(gt=0, le=300)
    intensity: str = Field(default="medium", pattern=r'^(low|medium|high|amrap|emom)$')
    phase_tag: str = "phase:train"
    energy_before: Optional[int] = Field(ge=1, le=10, default=None)
    energy_after: Optional[int] = Field(ge=1, le=10, default=None)

    @property
    def duration_hours(self) -> float:
        return self.duration_minutes / 60
```

---

## KPIs e Métricas

### Input Manual (Morning Survey)

| Métrica | Tipo | Frequência | Fonte |
|:--------|:-----|:-----------|:------|
| `energy_level` | int (1-10) | Diário | Auto-indagação matinal |
| `sleep_quality` | int (1-10) | Diário | Auto-indagação matinal |
| `sleep_hours` | float | Diário | Tracker de sono |

### Computado (Reverse Sync)

| Métrica | Fórmula | Alvo Semanal |
|:--------|:--------|:-------------|
| `hours_train` | Soma de Timewarrior `@training` | ≥ 7.0h |
| `training_consistency` | Dias com training / 7 | ≥ 85% |
| `energy_delta` | `energy_after - energy_before` (média) | > 0 |

### Alertas do Hypervisor

| Condição | Ação |
|:---------|:-----|
| `hours_train < 5h/semana` | 🔴 Alerta: "Reset de Cache insuficiente — risco de burnout" |
| `energy_level < 4` por 3 dias seguidos | 🟡 Reduzir setpoints em 50%, priorizar recovery |
| `sleep_hours < 6` | 🟡 Aviso: "Sonho insuficiente — reduzir carga cognitiva" |
| `training_consistency < 50%` | 🔴 Alerta: " inconsistência de treino detectada" |

---

## Equação de Eficiência do Vetor

A eficiência do vetor Passion é calculada como:

```
η_passion = (hours_train_real / hours_train_setpoint) × (energy_avg / 10)
```

- Se `η_passion < 0.6`: O sistema está em risco de colapso físico. Reduzir todos os outros setpoints.
- Se `η_passion > 1.0`: O operador está em estado ótimo. Pode aumentar setpoints de Skill e Revenue.

---

## Dashboard: Visualização do Vetor

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ❤️ DASHBOARD PASSION — SEMANA 19                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  HORAS DE TREINO                                                        │
│  ├── Meta: 7.0h    │    Real: 6.5h    │    Status: 🟡 93%               │
│  ████████████████████████████████████████████████░░░░                   │
│                                                                         │
│  CONSISTÊNCIA (7 dias)                                                  │
│  ├── Seg  Ter  Qua  Qui  Sex  Sáb  Dom                                  │
│  ├──  ✅   ✅   ✅   ❌   ✅   ✅   ✅   =  6/7 (86%)                   │
│                                                                         │
│  MODALIDADES                                                            │
│  ├── Calistenia: 4.0h ████████████████████████████████                  │
│  ├── Muay Thai:  2.0h ████████████████                                  │
│  └── Meditação:  0.5h ████                                              │
│                                                                         │
│  ENERGIA MÉDIA MATINAL                                                  │
│  ├── 6.8/10  │  Tendência: ↗️ (+0.3 vs semana anterior)                 │
│                                                                         │
│  SONO MÉDIO                                                             │
│  ├── 7.2h/noite  │  Status: ✅                                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Recomendações do Hypervisor por Fase

| Fase do Sistema | Ação no Vetor Passion |
|:----------------|:----------------------|
| **Fundação** (Build to Learn) | Manter 100% do setpoint — o corpo sustenta a mente |
| **Busca** (Market/Networking) | Manter 100% — networking consome energia social |
| **Hackathon** (Build to Earn) | Aumentar cooldown em 50% — dissipar stress de deadline |
| **Overclocking** (Emergência) | Reduzir para 60% e agendar recovery obrigatório |

---

> **Conexão com Data-Mesh:** Os dados deste vetor fluem do Timewarrior (`@training` tags) → Middleware Python → SQLite `DailyMetrics.hours_train` → Dashboard Streamlit. O Hypervisor consome `energy_level` e `sleep_hours` da Morning Survey para ajustar os setpoints diários.
