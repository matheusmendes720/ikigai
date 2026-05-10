# Vetores IKIGAi × Data-Mesh

Este diretório expande os 4 vetores do modelo IKIGAi (`base/IKIGAi.md`) em especificações operacionais que se conectam diretamente ao pipeline do Data-Mesh.

Cada vetor define:
- **Significado estratégico** (o que representa no Ikigai)
- **Bloco operacional** (qual time-block da rotina)
- **Contrato de dados** (como é representado no Frontmatter, Pydantic, Taskwarrior e Timewarrior)
- **Setpoints e KPIs** (metas numéricas por tipo de dia)
- **Tags e UDAs** (como rastrear no CLI)

---

## Os 4 Vetores

| Vetor | Símbolo | Bloco Principal | Arquivo |
|:-----:|:-------:|:----------------|:--------|
| ❤️ **Passion** | `passion` | Training (Reset de Cache) | `vector-passion.md` |
| 💼 **Skill** | `skill` | Deep Work (Build to Learn) | `vector-skill.md` |
| 🎯 **Market** | `market` | Content Lab (Build to Share) | `vector-market.md` |
| 💰 **Revenue** | `revenue` | Laborative (Build to Earn) | `vector-revenue.md` |

## Integração com o Pipeline

Todos os vetores compartilham a mesma estrutura de dados no Data-Mesh:

```yaml
# No Frontmatter do Sonho/Objetivo:
ikigai_vectors:
  passion: 0.8
  skill: 0.9
  market: 0.7
  revenue: 0.6
```

```python
# No Pydantic Model:
class IKIGAiVectors(BaseModel):
    passion: float = Field(ge=0.0, le=1.0)
    skill: float = Field(ge=0.0, le=1.0)
    market: float = Field(ge=0.0, le=1.0)
    revenue: float = Field(ge=0.0, le=1.0)
```

O Reverse Sync cruza horas do Timewarrior (via tags `phase:train`, `phase:learn`, `phase:share`, `phase:earn`) com os vetores do Sonho raiz para calcular o **ROI Multidimensional**.

---

> **Regra Append-Only:** Estes documentos podem ser expandidos com novos setpoints, KPIs ou integrações, mas o conteúdo existente nunca deve ser deletado.
