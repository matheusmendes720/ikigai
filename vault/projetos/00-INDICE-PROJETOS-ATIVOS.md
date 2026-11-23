---
type: indice
date: 2026-11-08
revisado: 2026-11-23
status: revisto
proveniencia: atividade-git-derivada
preenchimento: dono+evidencia
---

# Índice — projetos ativos, 2026-11-08

> **O que este ficheiro é.** Um levantamento derivado de evidência, não um
> inventário. As colunas de identificação vêm da atividade git medida a
> 2026-11-08; as colunas de **estado**, **sonho** e **próximo passo** estão
> `UNKNOWN` porque só o dono as sabe, e este ficheiro não as inventa.
>
> **Como completar:** uma linha `UNKNOWN` de cada vez, sem apagar as que já estão
> medidas. Quando um projeto ganhar trabalho semanal, promove-se a
> `vault/projetos/<YYYY>-S<WW>-<slug>.md` (formato Folha Projeto, META-NP).

---

## 1. O que a atividade mede

Repositórios com commits nos últimos 30 dias, ordenados por volume:

| Repositório | Último commit | Commits / 30 d | Branch | Papel derivado |
|---|---:|---:|---|---|
| `code_space/moblie_harness` | 2026-11-08 | **299** | `main` | mobile-harness — `athena`, `hefesto`, `telegram`, `bridge`, `knowledge`, `pmo` |
| `code_space/f8-pro-dotfiles` | 2026-10-29 | **154** | `main` | dotfiles / paleta `f8` |
| `code_space/life-oss/life` | 2026-11-08 | **94** | `feat/harness-container` | **este repositório** — o store, o transporte, o bot |
| `code_space/hackaton` | 2026-10-31 | **30** | `main` | `cheers-hackathon-sesi-saude-2026` — pitch SINAL |
| `code_space/hefesto` | 2026-10-26 | 2 | `main` | **sem remote** — ver §3 |
| `code_space/athena` | 2026-10-26 | 2 | `main` | **sem remote** — ver §3 |
| `code_space/job_hunter` | 2026-10-17 | 1 | `main` | **sem remote** — spec-only desde 2026-08-28 |

Parados há mais de 30 dias, ainda com repositório: `senai`, `avalia-tui`,
`voice-agent` (2026-09-29 a 2026-09-19), `HSK`, `flowsint`, `apps`,
`creative_ai`, `Learn-Vim`.

**Leitura:** dos repositórios acima, o que mais recebe trabalho **não é este**.
O `mobile-harness` fez 299 commits em 30 dias contra os 94 deste. O vault que
estamos a actualizar pertence ao menos activo dos dois — e é por isso que o
registo tem de nomear ambos, ou fica a mentir por omissão.

---

## 2. Os que o vault já conhece

| Projeto | Onde está no vault | Estado |
|---|---|---|
| Calistenia — ser campeão de street workout | `vault/00-norte/calistenia-campeao.md` (Folha Norte `NK-20260921`) | ativa; revisão marcada para 2027-03-21 |
| Calistenia — semana base | `vault/projetos/2026-S39-calistenia-base.md` (Folha Projeto `PK-2026-S39`) | `status: amarelo`; a semana W39 de 2026 já passou — **desactualizada** |
| ikigai / life — o produto canónico | este repositório; plano em `specs/production-readiness/` | ativo; plano Q4 v2 escrito hoje |

A Folha Projeto da calistenia é a única instância do formato META-NP que existe.
O pivô data-first exige ≥ 4 semanas de folhas para o promover — há 1. Enquanto
não houver as outras, o formato fica em rascunho e este índice não o promove.

---

## 3. Uma duplicação a resolver

`code_space/athena` e `code_space/hefesto` são repositórios **sem remote**,
parados a 2026-10-26, com dois commits cada (`product.md`, contratos e esqueleto).
O `code_space/moblie_harness` tem `athena/` e `hefesto/` como subdirectorias, com
trabalho a decorrer hoje (`feat(athena): a cura determinística das arestas + a
coluna edge_type`, 2026-11-08).

Ou seja: **os dois projectos existem duas vezes em disco**, e a versão viva é a
que está dentro do `mobile-harness`. As duas pastas soltas são o primeiro
esqueleto, e ficaram para trás. Não são um projecto activo — são uma cópia morta
com o mesmo nome. Nada aqui as apaga: fica registado para o dono decidir.

---

## 4. O buraco — o que este índice não tem

| Falta | Porque não está aqui |
|---|---|
| **Estado de cada projeto** (verde / amarelo / vermelho, e porquê) | só o dono sabe |
| **O sonho a que cada projeto serve** | o Q3 teve um `sonho-q3-2026-launch-v1` sem conteúdo; o Q4 ainda não tem sonho escrito |
| **Os projetos pessoais não-código** (corpo, estudo, trabalho) | não têm evidência em repositório nenhum |
| **As negociações de trabalho em curso** | **zero registos**. O `job_hunter` é a ferramenta, não a negociação; e está spec-only desde 2026-08-28 |

A última linha é a mais importante deste ficheiro. Não há uma única linha sobre
carreira em todo o `vault/`: nem proposta, nem entrevista, nem recrutador, nem
data. Um trimestre inteiro de trabalho pago pode estar a decorrer fora do sistema
que existe para o registar.

**A nota das negociações só nasce quando os factos forem ditos.** Não se cria um
placeholder a dizer "negociações em curso" — o vault já tem placeholders
suficientes, e um placeholder não é registo.

---

## 5. Revisão de 2026-11-23 — o buraco das negociações foi preenchido

> **O que muda neste índice.** A §4 diz que as negociações de trabalho têm
> **zero registos** e que «a nota só nasce quando o dono der os factos». Os factos
> foram dados: o trabalho de carreira do trimestre está em
> `C:\Users\mathe\code_space\work\msc`, e a folha que o regista é
> `vault/projetos/2026-S47-msc-reposicionamento.md`. A §4 fica como estava — é a
> fotografia de 2026-11-08, e este apêndice é a de 2026-11-23.

### 5.1 O facto que muda a leitura do índice

| Projecto | Onde está | Commits | Papel |
|---|---|---:|---|
| **Procura activa / reposicionamento** | `work/msc` — **não é um repositório de código** | **0** (por desenho) | **é o trabalho mais activo do trimestre, e o índice derivado de git não o via** |

A §1 mede repositórios com commits nos últimos 30 dias. O projecto mais activo
do Q4-2026 não aparece lá porque não tem `.git`: é um espaço de trabalho de
procura, com `.md` datados, snapshots do quadro de vagas e scripts de verificação.
**É a limitação do índice, não um buraco do trabalho** — e o mesmo se aplica ao
`mobile-harness` (299 commits em 30 dias, o repositório mais activo da lista),
cuja relação com o `athena`/`hefesto` continua por resolver (§3).

### 5.2 As linhas que os factos do dono preencheram

| Projecto | Estado | Sonho | Próximo passo |
|---|---|---|---|
| **Procura / reposicionamento** | 🔴 **vermelho** — 3 candidaturas em aberto, a primeira com prazo a **3 dias** (Neoenergia, 26/11); o bloqueio é o material bruto do CV (BYD), não o mercado | `NK-20261123-q4-reposicionamento` | mensagem à headhunter · submeter a Neoenergia · submeter a VWGS · preparar o desafio técnico da Caffeine Army |
| **ikigai / life — o produto canónico** | 🟡 **amarelo** — o sistema corre (3 noites medidas, métrica de 14 dias fechada); falta o job de CI com Docker (Q4.1) e o `scripts/` versionado (Q4.5) | `NK-20261123-q4-reposicionamento` (objectivo 2) | G1 · o PR #80 aberto (a cadência com sessão própria) |
| **Calistenia — ser campeão de street workout** | 🟡 **amarelo** — Folha Projecto `PK-2026-S39-calistenia-base` de 2026-09-21, **desactualizada**: a W39 já passou | `NK-20260921-calistenia-campeao` | reescrever a folha da semana actual |
| **Calistenia — semana base** | ⚪ **UNKNOWN** — sem registo desde 2026-09-27 | idem | o dono |
| **mobile-harness** | ⚪ **UNKNOWN** — 299 commits em 30 dias e o vault não sabe o que é | ⚪ | o dono |
| **f8-pro-dotfiles** · **hackaton** · **job_hunter** | ⚪ **UNKNOWN** | ⚪ | o dono |

### 5.3 As negociações de trabalho — o registo que não existia

| Facto | Valor | Onde |
|---|---|---|
| Vaga que originou o trabalho | encerrada — `12802194`, Analista Administrativo JR, Key User do Centro Logístico, Salvador | `work/msc/LEIA-ME.md` |
| Vagas em aberto | **3** — Neoenergia Coelba (fecha a postagem **26/11**), VW Group Services (candidaturas até **03/01/2027**), Caffeine Army DevOps I (sem prazo publicado) | `work/msc/16-o-que-fazer-agora-plano-23-11.md` §1 |
| Vagas de TI/dados no quadro da Wilson Sons | **0** de 43 posições lidas uma a uma a 23/11 | `work/msc/snapshots/2026-11-23-quadro-gupy.tsv` |
| Projectos com métrica nos CVs | **5**, escritas em STAR (encontrados em `job_hunter/base`) | `work/msc/16-…` §0 |
| Lacuna que resta nos 3 CVs | **1** — a BYD: mês de saída, stack, contribuições, escala | idem |
| Insumos do doc 14 §9 pendentes | **4** de 6 (material bruto feito em 23/11): piso salarial, nome/email da gestora, PJ permite nomear o cliente?, referência em 3 min, vídeo de 90 s | `work/msc/16-…` §5 |

### 5.4 O que a revisão não preenche

O estado (verde/amarelo/vermelho) do `mobile-harness`, do `f8-pro-dotfiles` e do
`hackaton` continua `UNKNOWN` — o índice mede commits, e commits não dizem o que
um projecto é. As duas cópias mortas de `athena`/`hefesto` (§3) continuam à
espera de decisão do dono. E a segunda instância do formato Folha Projeto
(`PK-2026-S47-msc-reposicionamento`) **não promove o formato** a fonte de verdade:
o critério do §2 são ≥ 4 semanas de folhas, e há 2.

---

*Ficheiro novo, 2026-11-08. Derivado por atividade git; completado pelo dono.
Não promove o formato META-NP a fonte de verdade.*
*Apêndice novo, 2026-11-23. Append-only.*
