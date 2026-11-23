---
type: revisao
quarter: 2026-Q3
date: 2026-11-08
status: consolidada
proveniencia: evidencia-do-repositorio
escopo: 12 semanas ISO, W28-W39
---

# Revisão consolidada do Q3-2026

> **O que esta revisão é.** Não é uma das doze revisões semanais — essas não
> existem. É a **única revisão do trimestre**, escrita a 2026-11-08, que
> classifica o que o plano previa contra o que o repositório prova.
>
> Regra aplicada: cada classificação cita evidência. Um item sem evidência fica
> `aberto`. Memória não é evidência.

---

## 1. O denominador do trimestre

12 revisões semanais previstas. **0 escritas.** É o número que domina tudo o resto
neste documento.

| Semana | Datas | Commits | Classe da semana | Evidência |
|---|---|---:|---|---|
| W28 | 07-06 → 07-12 | 0 | **vazia** | nenhum commit na janela |
| W29 | 07-13 → 07-19 | 0 | **vazia** | idem |
| W30 | 07-20 → 07-26 | 0 | **vazia** | idem |
| W31 | 07-27 → 08-02 | 0 | **vazia** | idem |
| W32 | 08-03 → 08-09 | 0 | **vazia** | idem |
| W33 | 08-10 → 08-16 | 0 | **vazia** | idem |
| W34 | 08-17 → 08-23 | 0 | **vazia** | idem |
| W35 | 08-24 → 08-30 | 224 | **rajada** | merge de sessão 2026-08-27 |
| W36 | 08-31 → 09-06 | 119 | **rajada** | `feat(loop): M4…M33` |
| W37 | 09-07 → 09-13 | 104 | **rajada** | `feat(loop): M33…M80`, `M14` (pin `mcp<2`) |
| W38 | 09-14 → 09-20 | 174 | **rajada** | pico; `ADJUST` ×4 no master review de 09-21 |
| W39 | 09-21 → 09-27 | 83 | **rajada** | fecho com M148 (`26e208da`) |

**Contagem por classe de semana:** 7 vazias · 5 rajada · 0 regulares.

---

## 2. Classificação das ondas

As ondas do `README.md` do trimestre, confrontadas com a atividade real:

### Onda 1 — 2026-07-06 → 2026-08-09 (5 semanas)

| Item previsto | Classe | Evidência |
|---|---|---|
| Plano da onda escrito | **não iniciado** | `02-onda-1/placeholder.md` |
| Revisões semanais W28–W32 | **não iniciado** | 0 ficheiros |
| Trabalho de código | **não iniciado** | 0 commits em 5 semanas |

### Onda 2 — 2026-08-10 → 2026-09-13 (5 semanas)

| Item previsto | Classe | Evidência |
|---|---|---|
| Plano da onda escrito | **não iniciado** | `02-onda-2/placeholder.md` |
| Loop de orquestração | **concluído** | `feat(loop): M4…M80`; 10/10 daemons RUNNING (M80) |
| Ponte taskdog leitura | **concluído** | `M142` — 6 tools de leitura |
| Revisões semanais W33–W37 | **não iniciado** | 0 ficheiros |

### Onda 3 — 2026-09-14 → 2026-09-27 (2 semanas)

| Item previsto | Classe | Evidência |
|---|---|---|
| Plano da onda escrito | **não iniciado** | `02-onda-3/placeholder.md` |
| Ponte taskdog escrita + produção | **concluído** | `M144`, `M146`, `M147`, `M148` |
| Master review com veredito | **concluído** | `vault/run-continuation/2026-09-21-master-review-revisited.json` |
| Revisões semanais W38–W39 | **não iniciado** | 0 ficheiros |
| Relatórios diários | **parcial (3 de ~60)** | `04-relatórios-diários/2026-09-05…07.md` |

---

## 3. Contagem final

| Classe | Itens |
|---|---:|
| Concluídos | 4 |
| Parciais | 1 |
| Não iniciados | 11 |
| Descartados | 0 |
| Abertos (sem evidência) | 0 |

Os 4 concluídos são todos de **código**. Os 11 não iniciados são todos de
**registo**. Não há um único item em que o código tenha ficado atrás do registo —
o padrão é o inverso, e é sistemático.

---

## 4. O achado que muda a próxima série

O método pressupõe um ritmo de 5 dias de execução por 3 semanas de análise. A
produção real deste trimestre tem outro formato:

```
semana:  28 29 30 31 32 33 34  35   36   37   38   39
commits:  0  0  0  0  0  0  0  224  119  104  174   83
```

**O problema não é disciplina, é desenho.** Uma rotina diária ou semanal aplicada
a uma produção em rajada tem duas opções, ambas más: escrever 7 notas a zero por
semana, ou escrever nada e ficar 5 meses sem registo — que é o que aconteceu.

A série seguinte (`2026-W45` e o plano Q4 v2) adopta a cadência compatível com a
rajada: **a unidade de registo é a rajada, não o dia.**

---

*Ficheiro novo, 2026-11-08. Append-only: não edita as semanas que não existem.*
