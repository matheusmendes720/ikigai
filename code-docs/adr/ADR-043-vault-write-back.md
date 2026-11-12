# ADR-043 — O `vault_write`: escrever a prosa de volta, sem segundo canónico

**Status:** Accepted
**Date:** 2026-11-10
**Medido:** 2026-11-11 — a seta foi percorrida ponta a ponta sobre o store real (§5.1, §9.1) · 2026-11-12 — a **noite**: uma nota nova do `pi` a percorrer a seta inteira (§5.2, §9.1)
**Deciders:** human (Matheus) + agent
**Scope:** quem escreve markdown no vault do VPS, em que árvore, com que regra de conflito e com que commit
**Anchor:** [ADR-037](./ADR-037-data-layer-canonical-turn.md) D4 · [ADR-039](./ADR-039-websocket-sync-transport.md) · [ADR-040](./ADR-040-client-state-and-drafts.md) §10 · ADR-012 (`vault_write` sole writer — **não publicada**, citada por ADR-037)

---

## 1. Veredito

**Entra:** um escritor de prosa — o `vault_write` — que **lê do store e escreve
markdown** numa **árvore nova no volume do VPS**, e que faz `commit` local sem
`push`. É o inverso exacto da ingestão.

**Não entra, e a razão fica escrita:**

| Coisa | Veredito | Porquê |
|---|---|---|
| escrever no `vault/` do clone git do VPS | **recusado** | o deploy faz `git reset --hard origin/main` a cada run: o que não for commited é apagado, e o que for commited diverge do `origin` sem mechanism de merge |
| `push` para o GitHub a partir do VPS | **recusado** | o VPS passa a ser writer do repositório; o `contents: read` do CI e o remote sem credencial mostram que hoje não é |
| escrever em artefactos **que já vieram de um ficheiro** | **recusado** | seria um segundo canónico: o markdown e o store a mandar um no outro sobre o mesmo artefacto |
| regenerar o markdown de tudo a partir do store | **recusado** | reescreve prosa que o dono editou à mão, sem conflito — é last-write-wins com o markdown a perder |
| "bi-direccional" como nome | **rejeitado** | a ingestão já é uma escrita no store; o que entra é a **direita inversa**, não as duas |

**A regra que substitui ADR-012:** *o store escreve a prosa; a prosa nunca
reescreve o store.* O `vault/` continua append-only, e o `vault_write` é o
único que escreve nele.

**A decisão que muda tudo:** o alvo é **uma árvore nova no volume**, não o
`vault/` do clone git. Três factos medidos no VPS a 2026-11-10:

1. `/opt/mathe/ikigai/vault` é o working tree de um clone git, e o deploy faz
   `git reset --hard origin/main` — o directório é **descartável por desenho**.
2. `/mnt/volume-fsn1-1/vault` é o directório do Syncthing (`folder id =
   "notas-estudo"`, `type="sendreceive"`), partilhado com o `windows-pc`. O
   Syncthing está `active`, com `fsWatcherEnabled="true"`.
3. A ingestão monta o **clone git** em `/app/vault:ro` e o **volume** em
   `/app/zonas:ro`. Duas árvores, dois regimes, um só leitor.

O `vault_write` escreve na **segunda** — a que o Syncthing traz para o desktop
— e o clone git fica como está: leitura, `ro`, descartável.

**E a seta está medida.** Em 2026-11-11, na imagem `sha-c935e180`, a seta foi
percorrida ponta a ponta sobre o store real: **23 ficheiros** escritos na árvore
do volume, **23/23** com `sha256(ficheiro) == body_hash(store)`, **23/23** com o
`ueid` da sua linha no frontmatter, e **1 976 artefactos vivos, todos com
`vault_path`** — o escritor não tem backlog. A ingestão que segue o write-back
diz `created=0 updated=0 unchanged=1976`: o ciclo fecha sem duplicar e sem
reescrever.

**E a noite está medida.** A 2026-11-12, na imagem `sha-f2fcf4f4`, a **noite**
correu sem ninguém: a cadência disparou às **01:00:00.134Z**, o único turno do
agente foi `/skill:daily-note` mais o contexto — **sem frase humana** — e a nota
que ela escreveu, `not:2026-11-12:74dfed05:d6ad7bd8023c5f59`, percorreu a seta
inteira: ficheiro com os **mesmos bytes** (`sha256` == `body_hash`), **+1 revisão
do `vault-write`**, **zero da ingestão**, e o Syncthing com `needFiles: 0` (§5.2,
§9.1).

---

## 2. A pilha

```text
                    ┌──────────────────────────────────┐
   agente (pi) ────▶│  store (Postgres + pgvector)    │  ← canónico
   Telegram     ────▶│  ikig.artifacts + vault_path     │
                    └──────────────┬───────────────────┘
                                   │
                    ┌──────────────▼───────────────────┐
                    │  VAULT_WRITE (NOVO)              │
                    │  lê store → escreve markdown     │
                    │  · só artefactos SEM vault_path  │
                    │  · commit local, sem push        │
                    └──────────────┬───────────────────┘
                                   │  escreve
                                   ▼
        /mnt/volume-fsn1-1/vault-escrita/   ← ÁRVORE NOVA (NOVA)
                   (Syncthing sendreceive)
                                   │
                                   ▼
                      windows-pc (desktop)
```

**O que NÃO está neste diagrama, e porquê:**

- **Nenhum `push`.** O `origin` continua a ser escrito pelo CI, a partir de
  commits que o dono revê. O `vault_write` não recebe credencial de escrita do
  GitHub, e o token que o deploy usa (`contents: read`, `packages: write`) não
  a tem.
- **Nenhuma escrita no clone git.** `git reset --hard` continua a ser seguro
  porque o directório continua descartável.
- **Nenhuma escrita de volta no store.** O `vault_write` escreve ficheiros, não
  artefactos. A ingestão continua a ser a única que escreve no store a partir
  de ficheiros.

---

## 3. Justificativa

### 3.1 O que o dono pediu, e o que era realmente a falta

O pedido foi "bi-directional read/write sync with vault". Medido, o que existe
hoje é:

| Direcção | Estado | Onde |
|---|---|---|
| vault → store | ✅ | `src/services/sync.py`, timer de 60s |
| store → clientes | ✅ | ADR-039, websocket + replay |
| clientes → store | ✅ | 6 tools MCP, `revision` + `idempotency_key` |
| **store → vault** | ❌ | não existe |

Falta **uma** seta. O que entra não é "bi-direccional" — a ingestão já escreve
no store. O que entra é a seta invertida, e ela tem de ser escrita com a
regra do conflito, porque é a seta que pode destruir trabalho.

### 3.2 Porque é que o alvo não pode ser o `vault/` do clone git

O deploy (`deploy.yml`, passo "Deploy over SSH") executa, por esta ordem:

```bash
git fetch --all --tags --prune
git checkout -q -B main origin/main
git reset --hard origin/main
```

`git reset --hard` **descarta** qualquer alteração no working tree. Duas
consequências, e as duas são fatais a um escritor de prosa:

1. **Sem `commit`:** o que o `vault_write` escrevesse desaparecia no deploy
   seguinte. Um ficheiro de nota que vive menos tempo que um deploy é um
   ficheiro que ninguém lê.
2. **Com `commit`:** o commit local fica no clone, e o próximo `reset --hard
   origin/main` **volta atrás dele**. O ficheiro desapareceria do mesmo modo —
   só um pouco mais tarde, e com a ilusão de que tinha sido gravado.

O `git reset --hard` não é um acidente do pipeline: é o que garante que o que
corre no servidor é exactamente o commit que o CI testou (ADR-037 D3). O
escritor de prosa **não pode** viver nesse directório sem quebrar a garantia
que faz o deploy valer alguma coisa.

### 3.3 Porque é que o `push` não entra

O remote do clone do VPS é `https://github.com/matheusmendes720/ikigai.git`,
**sem credential helper** — não há nada no servidor que lhe permita escrever. E
o workflow de deploy tem `permissions: contents: read`, `packages: write`: o
token do CI lê o código e publica imagens, e **não** escreve no repositório.

Dar ao VPS um token com `contents: write` seria dar ao servidor a chave da
casa. E o que o `vault_write` precisaria de push? Nada que o Syncthing não
faça melhor: o Syncthing **já** traz o volume para o desktop, com watcher de
ficheiro activo (`fsWatcherDelayS="10"`), sem token, sem branch, sem conflito
de merge.

### 3.4 A regra do conflito: quem ganha

O dono decidiu: **o store ganha em campo estruturado; o markdown que diverge
é um conflito explícito.**

Isto é ADR-037 D4 com nome próprio. D4 diz que o Postgres é canónico num
campo estruturado e que o markdown é a prosa de onde ele veio. A regra
escrita aqui é mais específica e é verificável:

> **O `vault_write` escreve um artefacto num ficheiro. Nunca reescreve um
> ficheiro que já existe.**

Ou seja: **o `vault_write` só escreve ficheiros novos**, para artefactos que
**não têm `vault_path`** — os que o agente criou no store e que nunca
existiram como ficheiro. Um artefacto que já tem `vault_path` tem um
ficheiro que já existe, e esse ficheiro é de quem o escreveu.

É por isso que o âmbito é *só os artefactos sem `vault_path`*: essa coluna,
criada na migração `0005_vault_path.sql`, **já é a resposta à pergunta
"isto já é um ficheiro?"**. A migração diz, nos seus próprios comentários:

> *A write-back needs to know which file to write, and the store is the only
> place that knows.*

O `vault_path` foi construído para isto. A peça já estava feita; o que
faltava era a decisão de a usar.

### 3.5 Porque é que isto não é um loop

O medo legítimo: escrita no vault → ingestão lê o ficheiro → store actualiza →
`vault_write` escreve de novo → ...

O ciclo **fecha** porque a identidade o fecha. A ingestão calcula a identidade
do artefacto a partir do `ueid` declarado no frontmatter quando existe
(`VaultSync._uid_for`), e o `vault_write` escreve **o `ueid` do store no
frontmatter** do ficheiro que cria. Logo:

1. o `vault_write` escreve `not:2026-11-10:abc123:def456` no frontmatter;
2. a ingestão lê o ficheiro, encontra o `ueid`, e usa **aquele** uid;
3. o artefacto que a ingestão escreve **é** o mesmo que o `vault_write`
   pretendia escrever — o mesmo uid, a mesma revisão;
4. o `body_hash` do ficheiro é o do corpo, e a ingestão vê que a escrita já
   está lá: `unchanged`.

A segunda passagem não muda nada. E o `vault_write` só escreve artefactos
**sem** `vault_path` — depois da primeira passagem o artefacto **tem**
`vault_path`, e o escritor deixa de lhe tocar. O ciclo não é infinito: é
**fechado em uma volta**, e o estado final é o mesmo nos dois lados.

O inverso também é verdade, e é o que torna a regra do conflito honesta: se o
dono editar à mão um ficheiro que o `vault_write` criou, a ingestão leva essa
edição para o store (é o comportamento normal de quem lê ficheiros), e o
`vault_write` **já não escreve nesse artefacto** — porque ele tem `vault_path`.
A mão do dono na Keyboard nunca é sobrescrita por uma máquina.

---

## 4. A ponte que já existe

Nada disto precisa de um novo primitivo. O que já lá está:

| Peça | Onde | Porque serve |
|---|---|---|
| `vault_path` | `src/contracts/dom.py:104`, migração `0005` | diz **que ficheiro** é este artefacto. `NULL` = nunca foi ficheiro = o `vault_write` pode escrevê-lo |
| `ueid` no frontmatter | `VaultSync._uid_for` (`sync.py:564`) | fecha o ciclo: o ficheiro escrito carrega a identidade do store |
| `body_hash` | `src/contracts/dom.py:90` | diz se o ficheiro e o store estão de acordo; é o que torna a reescrita idempotente |
| `client_id` | `WriteRequest` | distingue o escritor (`vault-write`) do dono e da ingestão (`vault-sync`) — quem escreveu é visível no store |
| `revision` | ADR-037 D5 | se o ficheiro é reescrito, a revisão sobe; o store nunca é sobrescrito em silêncio |
| O `client_id` do actor | `sync.py` `_client_id = "vault-sync"` | o `vault_write` nasce com `"vault-write"` — as duas escritas ficam distinguíveis no `ikig.artifacts` |
| A árvore do Syncthing | `folder id="notas-estudo"`, `sendreceive`, `windows-pc` | é a entrega: o ficheiro chega ao desktop sem token e sem branch |
| `git reset --hard` | `deploy.yml` | **deixa de ser um problema** quando o escritor não vive no clone git |

O que **não** existe e esta ADR não precisa: uma tool MCP nova, um canal novo,
um protocolo novo. O `vault_write` é um serviço como o `VaultSync` — e, como
o `VaultSync`, um comando de container.

---

## 5. O que está quebrado, com evidência

Medido no VPS a 2026-11-10 (`hetzner-vpn`, imagem `sha-d5e36106`):

| # | Facto | Como se mediu | Consequência |
|---|---|---|---|
| 1 | O `vault/` do VPS é o working tree de um clone git | `docker inspect ikigai-sync-1` → `Source=/opt/mathe/ikigai/vault` | o alvo do deploy e o alvo do ingestion são o **mesmo** directório |
| 2 | O deploy descarta esse directório | `deploy.yml`: `git reset --hard origin/main` | escrever lá é escrever num ficheiro que o próximo deploy apaga |
| 3 | O volume é Syncthing, não git | `config.xml`: `folder id="notas-estudo" type="sendreceive" path="/mnt/volume-fsn1-1/vault"`; `ls .git` → não existe | a árvore nova não é git — e não precisa de ser |
| 4 | O Syncthing está vivo e a observar | `systemctl is-active syncthing@mathe` → `active`; `fsWatcherEnabled="true"`, `fsWatcherDelayS="10"` | a entrega ao desktop é automática e por evento, não por polling |
| 5 | O VPS não tem credencial de escrita no GitHub | `git config --get credential.helper` → vazio; `.git/config` só tem `fetch` | `push` exigiria um token novo — e dava ao servidor `contents: write` |
| 6 | O CI também não escreve no repositório | `deploy.yml`: `permissions: contents: read, packages: write` | o padrão do repo é: **o CI publica imagens, não código** |
| 7 | As duas árvores estão montadas `ro` | `docker inspect`: `/app/vault (ro)`, `/app/zonas (ro)` | hoje **nenhum** container escreve markdown. O que entra muda isto, e só numa |
| 8 | O store tem 1 954 artefactos e distingue os seus autores | `group by client_id` → `vault-sync: 1953`, `pi-harness/tg-box-01: 1` | a autoria já é um dado do store. O `vault_write` é o terceiro autor, e aparece como tal |

O item 7 é o que torna esta ADR **uma troca de invariante**, não um
incremento: hoje a frase "o vault nunca é escrito por nada" é verdade em todo
o sistema (ADR-012, citado por `compose.yml:405`), e depois desta ADR deixa de
ser.

### 5.1 O que foi medido, e quando (2026-11-11)

Medido no VPS (`hetzner`, imagem `sha-c935e180`, contentores com dois minutos de
vida), pela **sonda versionada** `deploy/probes/vault-arrow.sh` — que mede os
factos abaixo e **sai com código diferente de zero** quando um deles é falso — e
por SQL directo ao store:

| # | Facto | Como se mediu | Resultado |
|---|---|---|---|
| 1 | O escritor escreve ficheiros | `find /mnt/volume-fsn1-1/vault-escrita -name '*.md'` | **23** ficheiros |
| 2 | O ficheiro **é** o que o store diz | `sha256sum` de cada ficheiro contra o `body_hash` da sua linha | **23/23 iguais**, 0 divergentes, 0 ausentes |
| 3 | O ficheiro carrega a identidade | `grep "ueid: <uid>"` em cada ficheiro | **23/23** com o `ueid` da sua linha |
| 4 | O store sabe onde o ficheiro está | `select count(*) … where deleted_at is null and vault_path is not null` | **1 976 de 1 976** — o backlog do escritor é **zero** (`scanned=0`) |
| 5 | O ciclo fecha sem duplicar | a linha da ingestão: `scanned=1977 created=0 updated=0 unchanged=1976 skipped=25`, quatro rondas seguidas | **created=0** e **updated=0** — a ingestão não escreve nada |
| 6 | A ingestão não mexe nas revisões | `ikig.artifact_revisions` das 23 linhas escritas | **zero** revisões de `vault-sync`; todas são do `vault-write` |
| 7 | A escrita do escritor é versionada | o mesmo `artifact_revisions` | **+1 revisão** por artefacto, via `expected_revision` — uma revisão que se mexe é um conflito, nunca uma sobrescrita (ADR-037 D5) |
| 8 | As árvores estão separadas | `docker inspect` das montagens | `write`: só `/app/vault-escrita`, **rw**; `sync`: `/app/vault`, `/app/vault-escrita` e `/app/zonas`, os três **ro** |
| 9 | A árvore escrita não é git | `ls .git` na raiz da árvore | não existe — e o registo de `commit` é *skipped*, por desenho (§12) |
| 10 | O `vault/` do clone git ficou intacto | `git -C /app/vault status --porcelain` | **vazio** — o `reset --hard` do deploy continua seguro |
| 11 | A entrega ao desktop está montada | Syncthing: pasta `notas-escrita`, `sendreceive`, `fsWatcherEnabled=true`; `rest/db/status` | `needFiles: 0`, `errors: 0`, `pullErrors: 0`, 23 ficheiros dos dois lados — **ver o ficheiro no desktop é do dono** |

**A nota da corrida de 2026-11-11** é o caso mais completo, porque é o
artefacto que o `pi` escreveu do zero: `not:2026-11-11:74dfed05:d6ad7bd8023c5f59`
→ `nota/relat-rio-di-rio-2026-11-11-q4-2026-d6ad7bd8.md`, `sha256` =
`body_hash` = `e1ebbcb4…`, `ueid:` no frontmatter, `rev=3`, e a ingestão a dizer
`unchanged`.

**Uma correcção ao que a ADR prometia.** O passo 5 do §9 dizia *"duas voltas ⇒ o
`body_hash` do ficheiro não muda"*. Medido: **o ficheiro é uma função do estado
do store** — e o estado do store inclui o `updated_at`. Quando o `updated_at` da
linha se mexe, os bytes mudam, e o escritor reescreve o ficheiro para volver a
bater. Numa janela de vinte minutos observada na caixa, **18 dos 23** ficheiros
foram reescritos por isso (mtime 05:05Z contra 04:45Z). O que é verdadeiro — e
é o que a ADR queria dizer — é: **duas voltas sobre o mesmo estado do store dão
os mesmos bytes.** E o escritor **é** um escritor: a sua escrita também é
versionada, e também sobe uma revisão (ADR-037 D5).

**O `UPDATE` sem revisão.** O log de eventos regista um `UPDATE` às
05:05:03.968897 nas linhas escritas, e a revisão **não** subiu. Com o código de
hoje isso é impossível — `_update` faz sempre `revision=revision+1`
(`src/data/repository.py:228`) — logo esse `UPDATE` pertence a um **build
transitório**, deployments de outra sessão nessa janela, e **não se repete** na
imagem actual (quatro rondas seguidas com `updated=0`).

**O que estava por medir:** a **noite** — uma nota nova, escrita pelo `pi` na
imagem actual, a percorrer a seta inteira. Foi medida a 2026-11-12 (§5.2).

### 5.2 A noite, medida (2026-11-12)

O que faltava à §5.1 era a **noite**: uma nota nova, escrita pelo `pi` na imagem
actual, a percorrer a seta inteira. Medido no VPS a 2026-11-12 (imagem
`sha-f2fcf4f4`), pela **sonda versionada** `deploy/probes/night-arrow.sh` — que
mede os factos abaixo e **sai com código diferente de zero** quando um deles é
falso — e por SQL directo ao store:

| # | Facto | Como se mediu | Resultado |
|---|---|---|---|
| 1 | A cadência disparou sozinha | o ledger do harness: `routine.started` | **2026-11-12T01:00:00.134Z**, `daily-note`, `date=2026-11-12`, sessão `tg-2115322359` |
| 2 | **Não havia mensagem humana** | o ficheiro de sessão do próprio agente: o único turno de utilizador da noite | `/skill:daily-note` mais o contexto (`date`, `now`) — **nada mais** |
| 3 | A corrida acabou | `routine.finished` | **01:02:25.808Z** — **145,7 s** — sem `routine.failed` nem `routine.timed_out`, e sem queda para o modelo de reserva (`fell_back: null`) |
| 4 | A nota aterrou | `select … from ikig.artifacts where kind='nota'` | `not:2026-11-12:74dfed05:d6ad7bd8023c5f59`, "Relatório Diário — 2026-11-12", `Q4-2026`, `2026-W46`, `client_id=pi-tg-2115322359`, **14 197 caracteres** |
| 5 | A nota classificou o dia | o corpo da nota | **11 itens** (4 feito · 0 parcial · 6 não iniciado · 1 descartado), completion **4/11** |
| 6 | A nota deixou a evidência | `ikig.artifact_relations` | **6 arestas `evidences`** (a nota de 11-11, a revisão W46, a decisão AG3, `fas:b3`, `fas:b2`, `kpi:relatorios-diarios`) |
| 7 | O ficheiro **é** o que o store diz | `sha256sum` do ficheiro contra o `body_hash` da linha | `nota/relat-rio-di-rio-2026-11-12-q4-2026-d6ad7bd8.md` (14 580 B): `dfc3954d…` == `body_hash` — **iguais** |
| 8 | A autoria é do escritor | `ikig.artifact_revisions` da nota | rev 1 por `pi-tg-2115322359` (01:02:19.028846Z), rev 2 por `vault-write` (01:02:19.987204Z), **zero** de `vault-sync` |
| 9 | O ciclo fecha | a linha da ingestão depois do write-back | `scanned=1979 created=0 updated=0 unchanged=1978 skipped=25`; o escritor: `scanned=1 written=1 skipped=1` (o *skip* é o `commit`, por desenho) |
| 10 | O store sabe onde está cada ficheiro | `select count(*) … where deleted_at is null and vault_path is not null` | **1 978 de 1 978** |
| 11 | A entrega ao desktop está montada | Syncthing `notas-escrita`, `rest/db/status` | `idle`, `needFiles: 0`, `errors: 0`, `pullErrors: 0`, **25 ficheiros dos dois lados** |

**A sonda foi falsificada antes de ser acreditada.** Uma sonda que só imprime
é um relatório. `deploy/probes/night-arrow.sh` foi estragada de propósito, de
três maneiras, e tinha de falhar todas as três: uma noite que nunca aconteceu
(`2026-11-08` → **6 falhas**, saída 1), um ficheiro com **um byte** mudado (a
verificação do `sha256` falha, saída 1), e uma **frase humana** injectada no
turno da noite, dentro do ficheiro de sessão do agente (a verificação de «sem
mensagem humana» falha, saída 1). A terceira encontrou um defeito real da
sonda: o `SESSION_DIR` é lido pelo JS **dentro** do contentor, e o `docker exec`
não herda o ambiente do host — a sonda lia o ficheiro de sessão verdadeiro
enquanto dizia ler o falso. Corrigido com `docker exec -e`.

**A outra linha da mesma noite foi pela mesma seta.** O store cresceu **dois**
artefactos, não um: a nota da noite, e a revisão semanal
`rev:2026-w46:5c1e9a33:cc03eb19e37836a4` (criada 2026-11-11T23:23:30Z, rev 1
por `pi-tg-2115322359` às 23:26:51Z, rev 2 por `vault-write` às 23:27:18Z,
`sha256` = `af16d254…` == `body_hash`). Mesma seta, mesmo autor, zero da
ingestão — a seta não é um caso especial da nota diária.

---

## 6. Inventário, com a razão de cada peça

| # | Peça | Ficheiro | Porque existe |
|---|---|---|---|
| 1 | `VaultWrite` | `src/services/vault_write.py` (novo) | o serviço que traduz store → markdown. Espelha `VaultSync`, que traduz markdown → store |
| 2 | O comando | `python -m src.services.vault_write` | o `vault-sync` skill diz "run the ingestion" e nomeava nada; a skill do `vault_write` dirá "run the write-back" e nomeará isto |
| 3 | `IKIGAI_VAULT_WRITE_ROOTS` | env | a árvore onde escreve. Sem ela, não escreve — como o `IKIGAI_VAULT_ROOTS` da ingestão |
| 4 | O contentor `write` | `deploy/compose.yml` (novo) | a sua própria cadência: escreve em render, e não em request |
| 5 | O mount `rw` | `deploy/compose.yml` | **só** a árvore nova. O `/app/vault` e o `/app/zonas` continuam `ro` |
| 6 | `client_id = "vault-write"` | `src/services/vault_write.py` | o store tem de dizer quem escreveu. Sem isto, o actor é indistinguível da ingestão |
| 7 | O `ueid` no frontmatter | `src/services/vault_write.py` | fecha o ciclo (§3.5). É a peça que impede o loop |
| 8 | O `body_hash` do artefacto | já existe | o que torna a reescrita idempotente: o mesmo corpo é o mesmo ficheiro |
| 9 | A guarda de conflito | `src/services/vault_write.py` | o ficheiro existe e o `body_hash` **não** bate ⇒ **conflito explícito**, não escrita |

**O que não entra:** nenhuma tool MCP nova (o `vault_write` é uma serviço
interno, não uma superfície pública — o agente não o invoca), nenhuma migração
(o `vault_path` já existe), nenhum endpoint, nenhum token novo.

---

## 7. Dia zero

O que fica verdade no primeiro commit desta ADR:

1. O `vault/` do clone git **continua `ro`** em todos os contentores, e
   continua descartável pelo `git reset --hard`.
2. O `/app/zonas` **continua `ro`** — a ingestão não muda de regime.
3. **Nenhum** contentor escreve markdown. A árvore nova ainda não existe.
4. O store tem `vault_path` em 1 954 artefactos ingeridos, e `NULL` nos que o
   agente criou — a distinção que o âmbito usa já é um facto medido.
5. O `vault_write` **não** existe. Ninguém o pode chamar.
6. ADR-012 continua por substituir: o `vault_write` como **único** writer do
   vault é a decisão que esta ADR substitui.

---

## 8. Evolução

| Quando | O que muda |
|---|---|
| **Agora** | o `vault_write` escreve ficheiros **novos** para artefactos sem `vault_path`, na árvore nova do volume |
| **Se o dono quiser editar** | o `vault_write` passa a poder reescrever os **seus** ficheiros (os que tem `vault_path`), com o conflito explícito: só reescreve se o `body_hash` do store bater com o do ficheiro |
| **Se o Syncthing deixar de ser a entrega** | o `vault_write` passa a fazer `commit` + `push` numa branch do GitHub — e nesse dia o VPS precisa de `contents: write`, que é uma decisão de segurança à parte |
| **Se o `vault/` do clone git deixar de ser descartável** | o deploy deixa de fazer `reset --hard` no `vault/` — e o `vault_write` pode escrever lá |

Cada uma destas é uma **emenda** a esta ADR, não um redimensionamento: o
invariante central — *o store escreve a prosa, a prosa não reescreve o store* —
não muda em nenhuma delas.

---

## 9. Passos com PASS falsificável

| # | Passo | PASS | Como se falsifica |
|---|---|---|---|
| 1 | A árvore nova é **separada** da do clone git | `docker inspect` mostra `Source=/mnt/volume-fsn1-1/...` e **não** `/opt/mathe/ikigai/vault` | apontar o `IKIGAI_VAULT_WRITE_ROOTS` ao clone git ⇒ o teste falha |
| 2 | O `vault/` e o `/app/zonas` continuam `ro` | `docker inspect` diz `ro` nos dois | pôr `rw` no `sync` ⇒ o teste falha |
| 3 | Só se escreve o que **não** tem `vault_path` | um artefacto com `vault_path` não ganha ficheiro | pôr `vault_path` no `body` de um artefacto novo ⇒ o teste falha |
| 4 | O ficheiro escrito carrega o `ueid` do store | o frontmatter tem `ueid:` e o valor é o uid do artefacto | escrever o slug em vez do uid ⇒ o teste falha |
| 5 | A reescrita é idempotente | duas voltas sobre o **mesmo estado do store** ⇒ o `body_hash` do ficheiro não muda | escrever o timestamp no corpo ⇒ o teste falha |
| 6 | O ciclo fecha | ingestion depois do write-back ⇒ `unchanged`, e o `revision` **não sobe por causa da ingestão** | retirar o `ueid` do frontmatter ⇒ a ingestão cria um **segundo** artefacto e o teste falha |
| 7 | Conflito é explícito | um `body_hash` divergente ⇒ o ficheiro **não** é reescrito, e há um registo | reescrever na mesma ⇒ o teste falha |
| 8 | A autoria é visível | o artefacto escrito tem `client_id = "vault-write"` | escrever com o `client_id` da ingestão ⇒ o teste falha |
| 9 | **Nenhum** `push` | o contentor não tem `contents: write` e não tem token de GitHub | pôr um token no `.env` ⇒ o teste falha |
| 10 | O `vault/` do clone git é **descartável** | `git reset --hard origin/main` **depois** do write-back não altera nada | o write-back escrever no clone git ⇒ o teste falha |

### 9.1 O que foi medido, passo a passo (2026-11-11)

| Passo | Como se mediu | Estado |
|---|---|---|
| 1 · a árvore nova é **separada** da do clone git | `docker inspect` das montagens | **provado** — `/mnt/volume-fsn1-1/vault-escrita` (rw) no `write`; o clone git é `/app/vault` (ro) |
| 2 · o `vault/` e o `/app/zonas` continuam `ro` | o mesmo `docker inspect` | **provado** — as três montagens do `sync` são `rw=false` |
| 3 · só se escreve o que **não** tem `vault_path` | `scanned=0` depois da primeira volta, com **1 976** linhas vivas **todas** com `vault_path` | **provado** — o escritor não tem backlog |
| 4 · o ficheiro escrito carrega o `ueid` | `grep` em 23 ficheiros | **provado** — 23/23 |
| 5 · a reescrita é idempotente | duas rondas sobre o mesmo estado do store | **provado, com a ressalva do §5.1** — o ficheiro é função do **estado do store**, `updated_at` incluído |
| 6 · o ciclo fecha | a ingestão depois do write-back | **provado** — `created=0 updated=0 unchanged=1976`, e **zero** revisões de `vault-sync` nas 23 linhas |
| 7 · o conflito é explícito | — | **não medido** — nenhum conflito ocorreu na caixa; o ramo existe e está coberto pelo teste unitário |
| 8 · a autoria é visível | o `client_id` das revisões | **provado** — as revisões do escritor são `vault-write`, as da ingestão `vault-sync`: distinguíveis |
| 9 · **nenhum** `push` | a árvore não é git; o contentor não tem credencial do GitHub | **provado** — o `commit` é *skipped* por desenho (§12) |
| 10 · o `vault/` do clone git é **descartável** | `git -C /app/vault status --porcelain` | **provado** — vazio: nada foi escrito no clone, e o `reset --hard` continua seguro |
| 11 · a **noite** percorre a seta inteira | `deploy/probes/night-arrow.sh 2026-11-12` | **provado** — a nota da noite, o ficheiro com os mesmos bytes, **+1 revisão do `vault-write`** e **zero da ingestão** (§5.2) |
| 12 · a sonda não é um relatório | a mesma sonda, estragada de propósito | **provado** — falhou nas três falsificações, uma delas depois de um defeito real da própria sonda (§5.2) |

---

## 10. Fora de escopo

| Coisa | Porque fica de fora | O que a reabre |
|---|---|---|
| **`push` para o GitHub a partir do VPS** | o VPS não tem credencial e não deve ter; o Syncthing entrega ao desktop sem token | o Syncthing deixar de ser a via de entrega |
| **Escrever no `vault/` do clone git** | o `git reset --hard` do deploy apaga-o | o deploy deixar de fazer `reset --hard` no `vault/` |
| **Reescrever ficheiros que já existem** | é onde a prosa do dono seria destruída | o §8 "se o dono quiser editar", com o conflito medido |
| **Escrever no store a partir do markdown** | a ingestão já faz isso; dois escritores do store é o que ADR-037 D5 proíbe | nunca, sem outra ADR |
| **O `vault_write` como tool MCP** | é um serviço interno, não uma superfície pública; o agente não o invoca | um cliente externo que precise de mandar exportar |
| **Round-trip completo (store → vault → store)** | o §3.5 mostra que o ciclo já fecha numa volta, por causa do `ueid`. Fazê-lo duas vezes é o bug, não a prova | nunca |
| **Índice/compressão "hysteresis"** | ADR-037 D1 adia a camada algorítmica | dados reais e uma ADR que a promova |

---

## 11. Decisões com default

| # | Decisão | Default | O que a muda |
|---|---|---|---|
| D1 | O alvo é uma **árvore nova no volume** (`/mnt/volume-fsn1-1/vault-escrita`), **não** o `vault/` do clone git | árvore nova no volume | o Syncthing deixar de ser a entrega, ou o deploy deixar de resetar |
| D2 | A **regra do conflito**: o store ganha em campo estruturado; markdown divergente é **conflito explícito** | conflito explícito, e o ficheiro não é reescrito | o dono decidir que o markdown é canónico — o que inverteria ADR-037 D4 |
| D3 | O **âmbito**: só artefactos **sem** `vault_path` — os que o agente criou e que nunca foram ficheiro | só sem `vault_path` | o dono querer que o escritor também mantenha os seus ficheiros (§8) |
| D4 | O `vault_write` faz `commit` local e **nenhum** `push` | commit local | o Syncthing deixar de entregar, e o token de escrita ser aceite |
| D5 | A **identidade** é o `ueid` do store, escrito no frontmatter | `ueid` no frontmatter | nada — sem ela o ciclo abre |
| D6 | A **autoria** é `client_id = "vault-write"`, distinto de `vault-sync` | `vault-write` | nada |
| D7 | O `vault_write` é um **serviço + comando**, não uma tool MCP | serviço | um cliente externo que precise de exportar |
| D8 | A **cadência** é própria (o `write` contentor, com o seu intervalo) | contentor próprio | o `sync` absorver a escrita — mas então os dois regimes (ro/rw) colidem no mesmo contentor |

---

## 12. Camadas de falha

Cada uma falha sozinha, e nenhuma leva as outras:

| Camada | Se falhar | O que se vê |
|---|---|---|
| o `uid` | o artefacto não tem identidade | nada é escrito, e o log diz qual |
| a árvore de destino | não existe, ou não é escrevível | o contentor escreve no log e **não** escreve ficheiro nenhum |
| o ficheiro existe e o `body_hash` diverge | **conflito** | o ficheiro fica como está, e a divergência é registada — nunca sobrescrita |
| o `commit` | o directório não é um repo git | o ficheiro **já** está no disco (o Syncthing leva-o na mesma); só o registo git se perde |
| o `push` | — | não existe nesta ADR. Se algum dia existir, a falha é do `push`, e o ficheiro já está no disco |
| o Syncthing | o desktop não recebe | o ficheiro está no volume; o dono vê-o quando a sincronização voltar |
| a ingestão | o `vault/` não é lido | o store fica como estava; o ficheiro novo espera |
| o store | não responde | o `vault_write` não escreve; o contentor fica unhealthy, e é a verdade |

**A ordem importa:** o ficheiro escreve-se **antes** do `commit`, e o `commit`
**antes** de qualquer entrega externa. Perder o `commit` custa um registo;
perder o ficheiro custa a prosa.

---

## 13. Referências

- [ADR-037](./ADR-037-data-layer-canonical-turn.md) — D4 (o store é canónico num campo estruturado), D5 (uma escrita, versionada, conflito = 409), D6 (seis tools)
- [ADR-039](./ADR-039-websocket-sync-transport.md) — o store a anunciar as suas mudanças; a vía que o `vault_write` vai ler
- [ADR-040](./ADR-040-client-state-and-drafts.md) §10 — o sync bi-direccional **recusado**, e a condição exacta que a reabre: *"Uma ADR que substitua ADR-012 explicitamente, com a direção, o conflito e o lock escritos."* Esta é essa ADR.
- `ADR-012` — `vault_write` como único writer do vault. **Não publicada**: fica no disco do dono e na história (ADR-037 §"publicação independente"). **Esta ADR substitui-a** no ponto único que a tornava binding: o `vault_write` deixa de ser o escritor de um `vault/` local e passa a ser o escritor de uma árvore no volume, com o conflito explícito e o `commit` local.
- `src/contracts/migrations/0005_vault_path.sql` — a migração que já continha a resposta: *"A write-back needs to know which file to write, and the store is the only place that knows."*
- `src/services/sync.py` — `VaultSync._uid_for` (o `ueid` declarado vence), `VaultSync._ingest_file` (o `body_hash` que decide se algo mudou)
- `src/contracts/dom.py:90,104` — `body_hash` e `vault_path`
- `specs/production-readiness/ROADMAP.md` — G2 (a prosa entra) e a track **T5 · `vault_write`** (ADR-012), que esta ADR cumpre
- `deploy/compose.yml:405` — *"The vault is never written by anything (ADR-012)"* — a frase que deixa de ser verdadeira, e porquê
- `deploy/probes/vault-arrow.sh` — a sonda versionada da medição de 2026-11-11: mede os factos do §5.1 e sai com código diferente de zero quando um deles é falso
- `deploy/probes/night-arrow.sh` — a sonda versionada da **noite**: mede os factos do §5.2 — a corrida disparou sozinha, sem mensagem humana, e a nota percorreu a seta inteira — e sai com código diferente de zero quando um deles é falso. Aceita o dia (`bash deploy/probes/night-arrow.sh 2026-11-12`) e, sem argumento, mede a última noite do ledger
- `specs/harness/CHAINED-ROUTINES.md` §11 — o tracker dos gates, onde o G3 (a cadência dispara-se) e o G9 (a prosa chega ao desktop) estão medidos por esta noite
- `src/ikigai/tests/store/test_vault_write_cycle.py` — o PASS 6 contra o Postgres real: a ingestão escreve zero e a revisão não sobe
- `src/ikigai/tests/services/test_vault_write_back.py` — a lógica do escritor com um store falso
