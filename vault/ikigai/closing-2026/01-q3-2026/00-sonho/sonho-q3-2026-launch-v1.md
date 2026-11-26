---
tipo: folha-norte
sonho_id: sonho-q3-2026-launch-v1
norte_id: NK-20261123-q3-launch-v1-retro
criado: 2026-11-23
date: 2026-11-23
quarter: 2026-Q3
janela: 2026-07-06 → 2026-09-27
ultima_revisao: 2026-11-23
proxima_revisao: —
status: encerrada
proveniencia: reconstrucao-retrospectiva
---

# 🧭 Folha Norte — Q3-2026 — *launch v1* (declarada a posteriori)

> **Declaração de Norte (1 frase, presente do indicativo):**
> _"Até 2026-09-27, eu lanço a minha primeira versão operativa — um sistema de orchestration e registo que faz o trabalho do trimestre aparecer, com a CLI a correr de fora e a ponte ao `taskdog` exposta por inteiro."_

> **Este ficheiro é uma reconstrução, e dizê-lo é a primeira coisa.** O Q3
> abriu **sem sonho**: o `placeholder.md` desta pasta foi o que existiu, e o id
> `sonho-q3-2026-launch-v1` foi citado por três relatórios diários sem que
> nenhum conteúdo lhe correspondesse.
>
> **Logo: isto NÃO fecha a P2 do Teste de Fogo.** A P2 pergunta que percentagem
> de tarefas diárias contribuiu directamente para o sonho — e um norte declarado
> **depois** do ciclo não é o norte que o trimestre teve. A P2 fica `UNKNOWN`, e
> fica assim por desenho: um número inventado seria pior do que a ausência.
>
> **O que este ficheiro faz, então:** dá ao trimestre o artefacto que lhe falta
> para a estrutura estar completa, declara a norte que a evidência mostra ter
> servido, e deixa escrito — em letra — que é retrospectiva. O `placeholder.md`
> fica como está.

---

## 1. O que a evidência mostra que o trimestre serviu

| Linha | Evidência |
|---|---|
| Orchestration | M0–M80: daemon, cost dashboard, notificação multi-canal, cron de cadências — `feat(loop): M4…M80` |
| Ponte ao `taskdog` | M142–M148 — `feat(loop): M148 — full taskdog exposure via IKIGAI bridge` (`26e208da`, 2026-09-27) |
| CLI utilizável de fora | `feat(cli): M138 — life console-script globally available` · `feat(v2): M140 — life v2 vault-search` |
| Um LLM real no dispatch | `feat(llm): M87 - real LLM dispatch via ChatAnthropic with graceful fallback` |
| O método de planeamento nasce | `feat(meta-np): first Folha Norte + Folha Projeto + Discovery Log templates` — e a **primeira** folha escrita é `vault/projetos/2026-S39-calistenia-base.md`, a 2026-09-21 |
| Governança | 7 → 21 ADRs · `vault/run-continuation/2026-09-21-master-review-revisited.json` |

Isto é o "launch v1" do id: um sistema que corre, com registo próprio e com o
método de folha de projeto dentro do próprio vault.

---

## 2. O que o trimestre não serviu

| Item | Estado | Evidência |
|---|---|---|
| Registo do trabalho do dono | **inexistente** | 0 revisões em 12 semanas; 3 relatórios diários em ~60 dias úteis |
| Plano do trimestre | **inexistente** | reconstruído a 2026-11-08 a partir de `.claude/loop/roadmap.md` (`q3-2026-plano-retro.md`) |
| Ondas | **inexistente** | três `placeholder.md`; os fechos foram escritos a 2026-11-23 (`02-onda-1..3/onda-*-q3-2026.md`) |

---

## 3. Filtros de atenção (para quem ler este trimestre depois)

- ❌ **Não ler o Q3 como um trimestre executado.** Executou-se 704 commits em 5 semanas, e as 7 primeiras não tiveram nenhum. O rácio de 89,1 % mede auto-consistência (o denominador cresceu com o trabalho), não execução estratégica.
- ❌ **Não tratar o `placeholder.md` como o sonho do trimestre.** O sonho é o ficheiro ao lado, e ele diz que é retrospectivo.
- ✅ **A correcção do registo está em C1** (Correção do Trajeto, 2026-11-08): a unidade de registo passa a ser a rajada.

---

## 4. Projectos activos neste trimestre

- `vault/projetos/2026-S39-calistenia-base.md` — Folha Projecto `PK-2026-S39-calistenia-base`, `status: amarelo`. **Desactualizada**: a semana W39 já passou e a folha continua marcada como se fosse a semana actual.

---

*Ficheiro novo, 2026-11-23. Append-only. Retrospectivo por natureza — não serve
para a P2 do Teste de Fogo, que fica `UNKNOWN`.*
