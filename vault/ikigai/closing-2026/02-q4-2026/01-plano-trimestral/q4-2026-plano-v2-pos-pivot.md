---
type: plano
quarter: 2026-Q4
date: 2026-11-08
status: ativo
proveniencia: spec-production-readiness-2026-11-06
companion: deep-agent-build-q4-2026.md
denominador: 6
---

# Q4-2026 — Plano trimestral v2, depois do pivô

> **Este plano não substitui o de 2026-08-28.** O
> `deep-agent-build-q4-2026.md` fica como foi escrito — é o registo do que se
> acreditava em 2026-08-28. Este é um artefacto novo, que o segue, porque o
> substrato mudou duas vezes desde então.
>
> **Denominador fixo na abertura: 6 metas.** Ao abrigo da Correção do Trajeto C2
> (`vault/ikigai/decisions/2026-11-08-fecho-q3-teste-de-fogo.md`), o plano só
> cresce por adição datada e justificada, e a adição não entra no denominador
> deste trimestre.

---

## 1. Porque é que o plano de 2026-08-28 não serve

Escrito a 2026-08-28, medido a 2026-11-08. Quatro divergências, todas verificáveis:

| # | O plano dizia | O repositório diz agora | Prova |
|---|---|---|---|
| 1 | B1 A2UI em `src/contracts/a2ui.py` *ou* `src/mesh/a2ui.py`; B3 gateway e B4 queue em `src/mesh/`; B2 CLI em `interfaces/cli/` | `src/mesh/`, `interfaces/`, `vibe-ops/`, `sys_ikigai/` têm **0 ficheiros versionados** | `git ls-files src/mesh` → 0 |
| 2 | B6 *vault sync* diferido para 2027-Q1 | o sync existe e está a ser corrigido: `feat(data)`, `fix(sync)`, `fix(data)` | commits de 2026-11-08 |
| 3 | Gate de decisão pré-B3: `AG3 Gateway Orphan`, ~1600 linhas no worktree `feat/data-model-unification` — MERGE ou DISCARD até 2026-11-09 | o worktree e o gateway saíram do escopo publicado; a decisão tornou-se sem objecto | `0b0906a1` (corte de 2026-11-05) |
| 4 | B2 (CLI) fechava a 2026-11-06, B3 (gateway) começava a 2026-11-09 | a linha activa é store → serviços → transporte → bot, não CLI → gateway → fila | `specs/production-readiness/ROADMAP.md` (2026-11-06) |

Há ainda duas datas que não fecham no próprio scaffold: o `README.md` do trimestre
declara 13 semanas (W41–W53) para um período que vai de 2026-10-05 a 2026-12-20 —
**11 semanas ISO** (W41–W51), com W52 como buffer e W53 inexistente em 2026.

**Consequência:** a meta B3 estava agendada para começar no dia seguinte ao
fecho deste plano, sobre um substrato que já não existe. Não se corrige por
adiamento — corrige-se por re-base.

---

## 2. O que o trimestre é agora

A fonte canónica do plano de engenharia é
`specs/production-readiness/ROADMAP.md` (2026-11-06). O que este documento faz é
a sua **projecção para o vault**: as metas do dono, o denominador, a cadência e o
critério de fecho. Não duplica o `TECH.md` e não redefine gates.

```
G1 · STORE      o Postgres real aceita o schema e o repositório relê
   ↓
G2 · CONTEÚDO   a prosa entra e o grounding chega
   ↓
G3 · HARNESS    o pi corre uma rotina de verdade          ┐ em paralelo
G4 · TELEGRAM   o dono escreve, editar revisa             ┘
   ↓
G5 · ENTREGA    um clone vira um serviço, sem mão
   ↓
MÉTRICA DE 14 DIAS (ADR-037 §8) — fora do Q4
```

O estado medido a 2026-11-06: **5 invariantes provadas, 3 parciais, 2 não
provadas** (`ROADMAP.md` §5). G1 é o único gate que desbloqueia a verificação de
todos os outros — e ainda não fechou, porque os 14 testes de `tests/store/` saltam
sem Docker.

---

## 3. As 6 metas do trimestre

Cada uma com um PASS falsificável. O fecho do trimestre calcula
`metas concluídas / 6 × 100`.

| # | Meta | PASS (falsificável) | Gate |
|---|---|---|---|
| **Q4.1** | **Provar o store** | os 14 testes de `tests/store/` passam no CI **e** `python -m src.transport.healthcheck` sai 0; o job **falha** se algum teste saltar | G1 / O1 |
| **Q4.2** | **Encher e ancorar** | `search_artifacts` devolve um artefacto cujo `body_hash` é o de um ficheiro conhecido do vault **e** `load_strategics(<raiz>)` devolve 9 documentos com índice não vazio | G2 / O2 |
| **Q4.3** | **O harness corre uma rotina** | por rotina, o artefacto do **tipo** certo existe no store com os campos que o tipo exige — a `desc` com `rationale`, o `okr` com `key_result` | G3 / O3 |
| **Q4.4** | **O dono escreve do telefone** | `/nota` cria `revision = 1`; **editar produz `revision = 2` e UM artefacto**; `/desc` com uma linha pergunta a segunda e não escreve | G4 / O3 |
| **Q4.5** | **Um clone vira um serviço** | `git clone` → `scripts/deploy-vps.sh main` → healthcheck verde **sem intervenção humana**, com dump antes do `up` | G5 / O4 |
| **Q4.6** | **A cadência existe** | a 2026-12-20, uma revisão por cada semana com commits > 0, e zero nas semanas a zero | C1 |

`Q4.6` é a única meta que não é de engenharia. É a que o Q3 falhou por completo, e
por isso é meta e não nota de rodapé: **o trimestre não fecha por os gates abrirem,
fecha por haver registo de os ter aberto.**

---

## 4. As ondas

O template do vault tem três pastas de onda; o plano de engenharia tem quatro
(O1–O4). O mapeamento é este, e a assimetria fica dita em vez de escondida:

| Pasta do vault | Onda de engenharia | Metas | PASS da onda |
|---|---|---|---|
| `02-onda-1/` | **O1 · Provar o store** | Q4.1 | 14 testes do store passam no CI |
| `02-onda-2/` | **O2 · Encher e ancorar** | Q4.2 | o store tem linhas do vault e o índice não está vazio |
| `02-onda-3/` | **O3 · O dono escreve** + **O4 · Entregar** | Q4.3, Q4.4, Q4.5 | editar no Telegram revisa em vez de duplicar **e** clone → serviço sem mão |

A onda 3 absorve duas ondas de engenharia porque O3 e O4 não se bloqueiam entre
si e caem ambos na janela de dezembro. Se O4 escorregar, escorrega com O3 — não
abre uma quarta pasta.

---

## 5. A janela que resta

Hoje é 2026-11-08 (domingo, fim da W45). O trimestre termina a 2026-12-20.

| Bloco | Semanas | Datas | O que fecha |
|---|---|---|---|
| Elapsed | W41–W45 | 10-05 → 11-08 | 5 de 11 semanas — **45 %** |
| Onda 1 | W46–W47 | 11-09 → 11-22 | Q4.1 |
| Onda 2 | W48–W49 | 11-23 → 12-06 | Q4.2 |
| Onda 3 | W50–W51 | 12-07 → 12-20 | Q4.3, Q4.4, Q4.5 |
| Fecho | W52 | 12-21 → 12-27 | Teste de Fogo do Q4, plano 2027-Q1 |

---

## 6. Cadência (Correção do Trajeto C1)

A produção do Q3 foi 704 commits em 5 semanas, com 7 semanas a zero. A rotina
segue o formato da produção, não o contrário:

| Gatilho | Registo | Onde |
|---|---|---|
| Semana com commits > 0 | uma `revisao`, no fecho da semana | `03-revisões-semanais/2026-Www.md` |
| Semana com 0 commits | uma linha na revisão seguinte, e nada mais | idem |
| Rajada (>100 commits numa semana) | a revisão da semana **é** o registo; não se desdobra em diários | idem |
| Fecho de onda | PASS da onda, com a evidência | `02-onda-N/` |

Não há rotina diária obrigatória. Havia, e produziu 3 registos em 60 dias úteis.

---

## 7. O que falta e não é engenharia

| Falta | Estado | Porque bloqueia |
|---|---|---|
| **O sonho do Q4** (`00-sonho/`) | `placeholder.md` — só existe | C3: o trimestre não devia ter aberto sem ele; a P2 do Teste de Fogo fica `UNKNOWN` |
| **Os projetos ativos** | índice derivado em `vault/projetos/00-INDICE-PROJETOS-ATIVOS.md`, com `UNKNOWN` | sem eles, nenhuma onda liga a trabalho real |
| **As negociações de trabalho** | **zero registos no repositório** | não têm casa; a nota só nasce quando o dono der os factos |
| **O BRD** (`specs/product-brief/`) | não existe | `ROADMAP.md` §1.1: não trava execução, trava a história |

---

## 8. Fora de escopo, decidido

Retirado pelo pivô de 2026-11-01 e pelo corte de 2026-11-05 — não reaparece neste
trimestre:

- TUI e `src/tuiboard/`, `interfaces/tui/`, `vibe-ops/vibeops-tui/`
- MCP stdio local (`src/ikigai/src/mcp_server/`, `sys_ikigai/gateway/stdio_adapter.py`)
- O harness langgraph/langchain anterior (`src/ikigai/src/agents|chat|plugins/`)
- O kernel PAV e a camada algorítmica (ADR-037 D1: vem depois dos dados e da métrica)
- `job_hunter` como código — segue spec-only, como o plano de 2026-08-28 já dizia

---

## 8. Actualização de 2026-11-23 — o sonho do Q4 e a estrutura que faltava

> **Apêndice datado; o §7 acima fica como estava.** A tabela do §7 diz, com
> veracidade à data, que o sonho do Q4 era um `placeholder.md`. Este apêndice
> diz o que aconteceu depois, e não reescreve o §7.

### 8.1 C3 cumprido

| Item | Estado |
|---|---|
| `02-q4-2026/00-sonho/` com um ficheiro com `norte_id`, frase no presente do indicativo e data-limite | ✅ `sonho-q4-2026-reposicionamento.md` — `norte_id: NK-20261123-q4-reposicionamento`, data-limite **2026-12-20** |
| O plano Q4 v2 cita-o | ✅ este §8 é a citação |

A frase: *"Até 2026-12-20, eu reconstruo o meu posicionamento como desenvolvedor
sênior de dados e automação em Salvador — com candidaturas submetidas que o meu
trabalho medido sustenta — e o meu trimestre vive num sistema que o regista sem
eu ter de o escrever à mão."*

**O que mudou na leitura do plano:** o sonho do trimestre é o **reposicionamento
profissional**, e as seis metas são o **instrumento** que o torna registável. A
P2 do Teste de Fogo — *que percentagem de tarefas diárias contribuiu
directamente para o sonho* — deixa de ser `UNKNOWN` por falta de denominador:
o denominador passa a ser o trabalho de carreira, e a folha que o regista é
`vault/projetos/2026-S47-msc-reposicionamento.md`.

**O `placeholder.md` fica como está.** A nota de adiamento de 2026-08-29 continua
verdadeira como registo: houve um tempo em que o trimestre não tinha norte.

### 8.2 A cadência do trimestre, cumprida

| PASS | Estado a 2026-11-23 | Onde |
|---|---|---|
| **C1** — uma revisão por semana com commits > 0, zero nas semanas a zero | ✅ **7 revisões para as 7 semanas com commits** (W40, W41, W42, W44, W45, W46, W47) e **zero** para a W43 | `02-q4-2026/03-revisões-semanais/` |
| **C2** — denominador fixo | ✅ já declarado (`denominador: 6`, 2026-11-08) | §3 deste ficheiro |
| **C3** — o trimestre tem sonho | ✅ ver §8.1 | `02-q4-2026/00-sonho/` |

### 8.3 A estrutura do trimestre, fechada

| Pasta | O que passou a ter |
|---|---|
| `00-sonho/` | 1 ficheiro (§8.1) |
| `01-plano-trimestral/` | este plano + o de 2026-08-28 (que fica como foi escrito) |
| `02-onda-1..3/` | 3 ficheiros de onda com o PASS e a evidência de cada uma |
| `03-revisões-semanais/` | 7 revisões (§8.2) |
| `04-relatórios-diários/` | 0 — e o README dirá porquê |

### 8.4 A janela que resta, corrigida

A tabela do §5 diz `Elapsed | W41–W45 | 10-05 → 11-08 | 5 de 11 semanas — 45 %`.
Medido a 2026-11-23: **W40 (2026-09-28 → 10-04) tem 30 commits** e pertence ao Q4
pelo enquadramento do próprio plano retrospectivo do Q3 (§2). Logo o conjunto
decorrido é **W40–W45, seis semanas**, e a percentagem do §5 é **6 de 11**.

---

*Ficheiro novo, 2026-11-08 — projecção para o vault de
`specs/production-readiness/ROADMAP.md` (2026-11-06), com o denominador fixado à
abertura.*
*Apêndice novo, 2026-11-23. Append-only.*
