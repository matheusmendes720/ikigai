# PRD-03: Study Backlog
**Versão:** 1.0.0 | **Status:** Draft | **Data:** 2026-05-10

> **Standalone Memory Machine** — Especificação autônoma do subgrafo de aprendizado. Cobre o pipeline completo: Skills → Topics → Materials → Sessions. Inclui integração com NLP tracker para chunking e retrieval semântico de conteúdo.

---

## 1. Domínio & Escopo

O **Study Backlog** gerencia todo o capital de aprendizado — desde a definição de competências-alvo até o registro granular de cada sessão de estudo. É o subgrafo que alimenta o vetor **Skill** do IKIGAi.

### Hierarquia Canônica
```
Skill (competência)
  └── StudyTopic (tópico de aprendizado)
        └── StudyMaterial (recurso: livro, curso, artigo)
              └── StudySession (evento de estudo discreto)
```

### Responsabilidades
- Gerenciar o backlog priorizado de tópicos de estudo
- Rastrear progresso granular por material (minutos concluídos)
- Registrar sessões com métricas de energia e pomodoros
- Computar horas investidas por skill e projetar target de maestria
- Conectar-se ao NLP tracker para indexar notas de estudo (semântico)

### Fora do Escopo
- Scheduling de sessões (Temporal Engine + TimeBlock)
- Tracking de tempo real (Timewarrior)
- Avaliações financeiras de skills (Revenue Vector)

---

## 2. Entidades & Schema

### Skill — Competência Acumulada
```python
class Skill(BaseModel):
    id: str                     # ^skill_[a-z0-9_]+$  Ex: "skill_python"
    name: str                   # min 3, max 100
    entity_type: Literal["skill"] = "skill"
    category: Literal["programming","ai_ml","data_engineering","frontend","soft_skills","language"]
    current_level: Literal["beginner","intermediate","advanced","expert"] = "beginner"
    target_level: Literal["beginner","intermediate","advanced","expert"] = "intermediate"
    status: Literal["active","paused","mastered"] = "active"
    study_topics: List[str]     # FKs → StudyTopic.ids
    projects_applied: List[str] # FKs → Project.ids
    hours_invested: float = 0.0 # ≥ 0
    hours_target: float = 100.0 # ≥ 0.5

    @property
    def progress_pct(self) -> float:
        level_map = {"beginner":0,"intermediate":25,"advanced":50,"expert":75}
        cur = level_map[self.current_level]
        tgt = level_map[self.target_level]
        if tgt == cur: return 100.0
        return min((cur / tgt) * 100, 100.0)
```

### StudyTopic — Conjunto Temático
```python
class StudyTopic(BaseModel):
    id: str                     # ^st_[a-z0-9_]+$  Ex: "st_pydantic_v2"
    name: str                   # min 3, max 200
    entity_type: Literal["study_topic"] = "study_topic"
    category: Literal["programming","ai_agents","frontend","productivity","soft_skills"]
    difficulty: Literal["beginner","intermediate","advanced"] = "beginner"
    priority: Literal["P0","P1","P2","P3"] = "P2"
    status: Literal["active","paused","completed","backlog"] = "backlog"
    parent_skill: Optional[str] = None  # FK → Skill.id
    estimated_hours: float = 10.0       # ≥ 0.5
    completed_hours: float = 0.0        # ≥ 0
    materials: List[str] = []           # FKs → StudyMaterial.ids
    created_at: date
    target_completion: Optional[date] = None

    @property
    def progress_pct(self) -> float:
        return min((self.completed_hours / self.estimated_hours) * 100, 100.0)
```

### StudyMaterial — Recurso de Estudo
```python
class StudyMaterial(BaseModel):
    id: str                     # ^sm_[a-z0-9_]+$
    title: str                  # min 3, max 300
    entity_type: Literal["study_material"] = "study_material"
    material_type: Literal["book","course","video","article","documentation","project"]
    url: Optional[str] = None
    file_path: Optional[str] = None
    topic_id: str               # FK → StudyTopic
    status: Literal["unread","reading","completed","reference"] = "unread"
    priority: Literal["P0","P1","P2","P3"] = "P2"
    estimated_minutes: Optional[int] = None
    completed_minutes: int = 0  # ≥ 0
    notes: str = ""
    tags: List[str] = []

    @property
    def progress_pct(self) -> float:
        if not self.estimated_minutes: return 0.0
        return min((self.completed_minutes / self.estimated_minutes) * 100, 100.0)
```

### StudySession — Evento Discreto
```python
class StudySession(BaseModel):
    id: str                     # ^ss_[a-z0-9_]+$
    entity_type: Literal["study_session"] = "study_session"
    topic_id: str               # FK → StudyTopic
    date: date
    start_time: time
    end_time: Optional[time] = None
    duration_minutes: Optional[int] = None  # auto-computed se end_time fornecido
    material_refs: List[str] = []           # FKs → StudyMaterial
    pomodoros_completed: int = 0            # ≥ 0
    notes: str = ""
    energy_level_before: Optional[int] = None  # 1-10
    energy_level_after: Optional[int] = None   # 1-10

    @model_validator(mode='after')
    def compute_duration(self):
        if self.end_time and self.start_time and not self.duration_minutes:
            start = datetime.combine(self.date, self.start_time)
            end = datetime.combine(self.date, self.end_time)
            self.duration_minutes = int((end - start).total_seconds() / 60)
        return self
```

---

## 3. Frontmatter Contracts (YAML)

### Skill
```yaml
---
entity_type: skill
id: skill_python
name: "Python Engineering"
category: programming
current_level: intermediate
target_level: advanced
status: active
study_topics: [st_pydantic_v2, st_duckdb_analytics, st_async_patterns]
projects_applied: [proj_vibe_ops_pipeline]
hours_invested: 47.5
hours_target: 200.0
created_at: 2026-01-01
---
```

### StudyTopic
```yaml
---
entity_type: study_topic
id: st_pydantic_v2
name: "Pydantic v2 — Schema Design & Validation"
category: programming
difficulty: intermediate
priority: P0
status: active
parent_skill: skill_python
estimated_hours: 15.0
completed_hours: 8.5
materials: [sm_pydantic_docs, sm_pydantic_tutorial_yt]
created_at: 2026-01-05
target_completion: 2026-02-01
---
```

### StudyMaterial
```yaml
---
entity_type: study_material
id: sm_pydantic_docs
title: "Pydantic v2 Official Documentation"
material_type: documentation
url: "https://docs.pydantic.dev/latest/"
topic_id: st_pydantic_v2
status: reading
priority: P0
estimated_minutes: 240
completed_minutes: 120
notes: "Cobriu validators, model_config, field_serializers"
tags: [python, pydantic, validation, data-modeling]
---
```

### StudySession
```yaml
---
entity_type: study_session
id: ss_20260110_pydantic
topic_id: st_pydantic_v2
date: 2026-01-10
start_time: "06:00"
end_time: "07:30"
duration_minutes: 90
material_refs: [sm_pydantic_docs]
pomodoros_completed: 3
notes: "Estudei computed_fields e model_validator. Dúvida: como combinar com discriminated unions."
energy_level_before: 8
energy_level_after: 7
---
```

---

## 4. Fluxos no Data-Mesh

### Upstream
```
[Obsidian notes / reading highlights]
  → FrontmatterParser → Pydantic Validation
  → completed_minutes update em StudyMaterial
  → completed_hours update em StudyTopic
  → hours_invested update em Skill
  → SQLite study_* tables
```

### Downstream
```
[StudySession records]
  → DailyMetrics.hours_learn += session.duration_minutes / 60
  → Timewarrior tag "phase:learn" via TWAdapter
  → IKIGAiVectors.skill score update
```

### NLP Integration (Dream Logger Context)
```
[StudySession.notes]
  → Chunker (1500 tokens, 100 overlap)
  → Embedding (SBERT / local model)
  → VectorIndex (FAISS local)
  → FindMissingSnippets vs baseline_docs
  → SnippetsCatalog append
```

---

## 5. SQLite Schema

```sql
CREATE TABLE skills (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    category        TEXT NOT NULL,
    current_level   TEXT DEFAULT 'beginner',
    target_level    TEXT DEFAULT 'intermediate',
    status          TEXT DEFAULT 'active',
    hours_invested  REAL DEFAULT 0.0,
    hours_target    REAL DEFAULT 100.0,
    created_at      DATE,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE study_topics (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    category            TEXT NOT NULL,
    difficulty          TEXT DEFAULT 'beginner',
    priority            TEXT DEFAULT 'P2',
    status              TEXT DEFAULT 'backlog',
    parent_skill        TEXT REFERENCES skills(id),
    estimated_hours     REAL DEFAULT 10.0,
    completed_hours     REAL DEFAULT 0.0,
    created_at          DATE,
    target_completion   DATE,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE study_materials (
    id                  TEXT PRIMARY KEY,
    title               TEXT NOT NULL,
    material_type       TEXT NOT NULL,
    url                 TEXT,
    file_path           TEXT,
    topic_id            TEXT NOT NULL REFERENCES study_topics(id),
    status              TEXT DEFAULT 'unread',
    priority            TEXT DEFAULT 'P2',
    estimated_minutes   INTEGER,
    completed_minutes   INTEGER DEFAULT 0,
    notes               TEXT,
    tags_json           TEXT,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE study_sessions (
    id                  TEXT PRIMARY KEY,
    topic_id            TEXT NOT NULL REFERENCES study_topics(id),
    session_date        DATE NOT NULL,
    start_time          TIME,
    end_time            TIME,
    duration_minutes    INTEGER,
    pomodoros           INTEGER DEFAULT 0,
    notes               TEXT,
    energy_before       INTEGER,
    energy_after        INTEGER,
    material_refs_json  TEXT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sessions_date ON study_sessions(session_date, topic_id);
CREATE INDEX idx_topics_skill ON study_topics(parent_skill, status);
CREATE INDEX idx_materials_topic ON study_materials(topic_id, status);
```

---

## 6. KPIs do Domínio

| KPI | Fórmula | Alvo |
|:----|:--------|:-----|
| Daily Study Hours | sum(session.duration) / 60 | ≥ 1.5h/dia |
| Topic Progress Rate | completed_hours / estimated_hours | monotônico ↑ |
| P0 Material Progress | completados / P0 totais | 100% antes de P1 |
| Pomodoro Yield | pomodoros * 25min / duration | ≥ 0.85 (foco) |
| CLR (Cognitive Load Ratio) | hours_learn / hours_earn | 0.3-0.7 ideal |
| Skill Level Velocity | level_changes / months | ≥ 1 nível por Phase |

---

## 7. CLI Commands

```bash
# Estado do backlog de estudos
python3 -m vibe_ops.cli study status

# Registrar sessão de estudo
python3 -m vibe_ops.cli study log \
  --topic st_pydantic_v2 \
  --start 06:00 --end 07:30 \
  --pomodoros 3 \
  --energy-before 8 --energy-after 7 \
  --notes "Estudei validators"

# Atualizar progresso de material
python3 -m vibe_ops.cli study material-progress sm_pydantic_docs --minutes 120

# Ver backlog priorizado
python3 -m vibe_ops.cli study backlog --priority P0,P1

# Progresso por skill
python3 -m vibe_ops.cli study skill-progress skill_python

# Sessões dos últimos 7 dias
python3 -m vibe_ops.cli study sessions --days 7

# Métricas NLP (notas de sessão)
python3 -m vibe_ops.cli study nlp-index --topic st_pydantic_v2
```

---

## 8. Integração NLP (Dream Logger)

Baseado no contexto do `Dream_Logger-algo-data_struct.md`, as notas de sessão alimentam um pipeline NLP local:

```python
class StudyNLPPipeline:
    """Pipeline NLP para indexação de notas de estudo."""

    CHUNK_SIZE = 1500   # tokens
    OVERLAP = 100       # tokens
    SIMILARITY_THRESHOLD = 0.80  # para dedup vs baseline

    def process_session(self, session: StudySession) -> List[Snippet]:
        if len(session.notes) < 50: return []
        chunks = self.chunker(session.notes)
        embeddings = [self.embed(c) for c in chunks]
        missing = self.find_missing(embeddings, self.baseline_index)
        return missing

    def chunker(self, text: str) -> List[str]:
        tokens = text.split()
        chunks, start = [], 0
        while start < len(tokens):
            end = start + self.CHUNK_SIZE
            chunks.append(" ".join(tokens[start:end]))
            start = end - self.OVERLAP
        return chunks
```

---

## 9. Anti-Patterns

### Proibido
- Criar StudyMaterial sem `topic_id` válido
- `completed_hours > estimated_hours` sem atualizar `estimated_hours`
- Sessões com duração > 240 min sem break documentation
- Skills com `current_level > target_level`

### Obrigatório
- `completed_hours` em StudyTopic atualizado após cada sessão
- `hours_invested` em Skill sincronizado com soma dos topics
- StudySession com `notes` mínimas para rastreabilidade

---

## 10. Roadmap

| Fase | Entregável | Estimativa |
|:-----|:-----------|:-----------|
| MVP | Pydantic models (Skill, Topic, Material, Session) | ✅ Feito |
| v0.2 | SQLite schema + insert/update adapters | 5h |
| v0.3 | CLI `study log` + `study backlog` | 6h |
| v0.4 | Auto-sync hours_invested para Skill | 3h |
| v0.5 | NLP pipeline para notas de sessão | 12h |
| v1.0 | FAISS local index + similarity search | 16h |

---
> **Regra Append-Only:** Novas descobertas devem ser anexadas. Nada pode ser deletado.
