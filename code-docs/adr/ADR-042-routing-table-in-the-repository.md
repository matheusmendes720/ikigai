---
id: ADR-042
title: "A tabela de routing vive no repositório, e o harness tem gate no CI"
date: 2026-11-09
status: accepted
---

## 1. Veredito

**Entra:** duas decisões que fecham o que ADR-041 deixou aberto.

1. **A tabela de routing é um ficheiro versionado.** `deploy/runtimes.json` é
   a tabela do deployment: vai no repositório, no mesmo commit que o deploy,
   e é montada **read-only** no agente em `/etc/ikigai/runtimes.json`. O
   harness **re-lê-a quando o mtime muda** — editar a tabela não é reiniciar
   nada.
2. **O harness tem gate no CI.** O agente é código publicado (a imagem
   própria, ADR-037 D7) e era a única superfície publicada **sem porta**: os
   24 testes seus (`deploy/harness/test/`) corriam na mesa do dono e em mais
   lado nenhum. Entra um job próprio — *The agent's own gate* — com o Node da
   imagem (24) e o lock como contrato.

**Não entra, e a razão fica escrita:**

| Pedido | Veredito | Porquê |
|---|---|---|
| A tabela no `.env`, em JSON inline | **Não** | várias runtimes é uma tabela, e uma tabela numa string JSON dentro de um ficheiro de ambiente é uma tabela que ninguém revê. O próprio código do registry diz isto. |
| A tabela só na caixa, fora do repositório | **Não** | a tabela é o mapa do deployment dos **seus** clientes. Um mapa que viaja com o deploy é um mapa que não pode descrever um deploy diferente do que corre; um mapa que fica na caixa desaparece com a caixa. |
| Um segundo bot token | **Não** | isso é uma decisão de produto — que canal existe — e não de deployment. A tabela está pronta para o receber: uma linha. |
| O cliente escolher o seu runtime | **Não, nunca** | ADR-041: o cliente é **roteado**, não escolhe. A escolha é do dono, na tabela. |

---

## 2. A pilha

| Peça | Onde | Porque |
|---|---|---|
| `deploy/runtimes.json` | `deploy/` | a tabela: versionada, no commit que o deploy traz |
| o mount e o `HARNESS_RUNTIMES_FILE` | `deploy/compose.yml` | o agente tem de saber **onde** a tabela está |
| `deploy/harness/test/deployment.test.mjs` | `deploy/harness/test/` | a tabela é conferida pelo **próprio registry**, não por uma segunda implementação das regras |
| o job *The agent's own gate* | `.github/workflows/ci.yml` | o harness deixa de ser a única superfície publicada sem gate |
| §1.0 e o gate G7 | `specs/harness/SESSIONS.md` | a spec publicada diz onde a tabela vive e como ela é conferida |

---

## 3. Justificativa

ADR-041 construiu o registo de runtimes, a tabela e o routing. **Construiu,
e não Exercitou.** A feature estava publicada, com os seus testes verdes, e
a correr em modo latente: o deployment tinha **um** runtime e **nenhuma**
regra, portanto o routing respondia sempre `routed: false` com a razão
`no routing rule; the default runtime` — visível, correcto, e a não decidir
nada.

Havia dois bloqueios, e nenhum dos dois era código:

- **O deployment não tinha forma de carregar a tabela.** O compose passava
  `HARNESS_RUNTIMES_FILE` — um caminho **dentro** do contentor — e não havia
  mount nenhum; e o `HARNESS_RUNTIMES` inline, que o registry sabia ler,
  não era passado. Havia, portanto, **zero** caminhos para dar uma tabela a
  uma deployment.
- **O código que aplica a tabela não tinha gate.** A matriz do CI é Python
  (seis pacotes) e o job *Container* constrói as imagens; o `node --test` não
  corria em lado nenhum. Um ficheiro em `deploy/harness/` podia partir o
  routing, o broker ou o tool `ask` e o pipeline não dizia nada.

É o mesmo buraco que a entrada `src-bot` tapou no cliente do Telegram: uma
árvore publicada sem gate encontra os seus defeitos pela pessoa que os sofre,
não pelo pipeline.

---

## 4. A ponte que já existe

- `runtimes.mjs` **já** lia `HARNESS_RUNTIMES_FILE` e **já** re-lia o
  ficheiro quando o mtime mudava. A decisão "editar a tabela não é reiniciar"
  estava tomada e escrita.
- `routeClient` **já** decidia e **já** recusava com a razão.
- O registry **já** era fail-closed: um provider que o contentor não tem, um
  runtime que não existe, um id que não é slug — recusados, com o motivo
  reportado em `/v1/runtimes`.
- O harness **já** tinha a sua suite e o SDK MCP pinado.

Nada foi reescrito. Esta ADR **liga** o que já estava feito.

---

## 5. O que está quebrado, com evidência

Medido na caixa, depois do deploy de `120103ff` (ADR-041):

```
GET /v1/runtimes
  → {"default":"owner","runtimes":[{"id":"owner", …}],"problems":[]}
    UM runtime. "problems":[] porque ninguém declarou nenhum.

GET /v1/routing?client=tg:2115322359
  → "routed": false, "reason": "no routing rule; the default runtime"

deploy/compose.yml
  → HARNESS_RUNTIMES_FILE: ${HARNESS_RUNTIMES_FILE:-}     (sem mount)
  → HARNESS_RUNTIMES: ausente                              (o inline nunca chega)

.github/workflows/ci.yml
  → a matriz tem seis pacotes Python; `node --test` não aparece em lado nenhum
```

E o contrapositivo, medido com a **imagem deployada** (não a cópia dos
testes): o registry decide e recusa como deve —

```
tg:proof-2     routed=true   runtime=fast   model=deepseek-flash
tg:2115322359  routed=false  runtime=owner  "no routing rule; the default runtime"

recusados, com a razão:
  runtime "ghost": provider "openai" não configurado (o contentor conhece: harness, deepseek)
  client "tg:orphan": encaminhado para "does-not-exist", que não existe
  client "not a client key": a chave não é uma chave de cliente válida
```

O código estava certo. O que faltava era o **cabo**.

---

## 6. Inventário, com a razão de cada peça

| Peça | Razão |
|---|---|
| `deploy/runtimes.json` | a tabela do deployment, versionada. `"default": "owner"`; o runtime `owner` (o provider do contentor, modelo `MiniMax-M2.7`, todas as rotinas); o runtime `fast` (o fallback `deepseek`, `deepseek-flash`, **só** `store-read` e `store-write`, âmbito de memória próprio) — o perfil de um cliente que não corre cadências; e a regra `tg:2115322359 → owner`. |
| o mount `./runtimes.json:/etc/ikigai/runtimes.json:ro` | relativo ao **directório do compose** (`deploy/`), como `../vault` — `./runtimes.json` seria `deploy/runtimes.json`, que é o ficheiro que o repositório publica. O ficheiro é versionado, logo está sempre lá: um mount de um ficheiro **em falta** faz o docker criar um **directório**, e o agente leria uma tabela vazia parecendo saudável. |
| `HARNESS_RUNTIMES_FILE: ${HARNESS_RUNTIMES_FILE:-/etc/ikigai/runtimes.json}` | o default é o caminho do mount, e a variável continua a poder ser apontada para outro sítio — o que muda é o **default**, não a capacidade. |
| `deploy/harness/test/deployment.test.mjs` | quatro testes: a tabela é **aceite** pelo registry (zero problemas), o default existe, **algum** cliente é roteado, e o compose monta e nomeia a tabela. A coerência é conferida pelo registry, não por uma reimplementação das regras. |
| o job *The agent's own gate* | `node --test "test/*.test.mjs"`, com `npm ci --omit=dev --ignore-scripts` e o Node **24** — o da imagem (`node:24-bookworm-slim`). Uma suite que passa no runner e falha no contentor é um gate que mede o runner. |
| §1.0 na spec | a spec publicada passa a dizer **onde** a tabela vive, porque uma spec que descreve o mecanismo e omite onde ele vive deixa a próxima pessoa a procurar. |

---

## 7. Dia zero

```bash
# a tabela entra no repositório, e o compose passa a montá-la
git add deploy/runtimes.json deploy/compose.yml
git add deploy/harness/test/deployment.test.mjs .github/workflows/ci.yml

# a suite do agente, local
cd deploy/harness && npm ci --omit=dev --ignore-scripts
node --test "test/*.test.mjs"        # 28 verdes

# a tabela, lida pelo registry (o mesmo código que a imagem corre)
curl -s localhost:8002/v1/runtimes
curl -s "localhost:8002/v1/routing?client=tg:2115322359"
```

---

## 8. Evolução

| Ordem | O quê | Porquê agora |
|---|---|---|
| 1 | **o segundo token** | ADR-041 §8: a tabela já existe; acrescentar um canal é uma linha de JSON e um segundo bot token. |
| 2 | **um runtime que não vê o store** | o registo já estreita as rotinas; falta um perfil cujas rotinas não tocam o store — o `routines: []` de um cliente que só conversa. |
| 3 | **a tabela por ambiente** | hoje a tabela é uma coisa do repositório. Quando houver **dois** deployments (a caixa e o portátil do dono), a tabela do portátil vai querer ser uma variante — e aí o `HARNESS_RUNTIMES_FILE` aponta para outro sítio, que já é possível. |
| 4 | **`sendRichMessage`** | ADR-041 §8: o relatório do agente é uma tabela e uma decisão; `sendMessage` corta a 4000 caracteres. |

---

## 9. Passos com PASS falsificável

| # | Passo | PASS | Como se falsifica |
|---|---|---|---|
| 1 | A tabela é aceite | `deploy/harness/test/deployment.test.mjs` verde: `registry.problems` é vazio | pôr `"provider": "openai"` num runtime e ver o teste falhar com a razão |
| 2 | A tabela roteia alguém | o mesmo teste: pelo menos um cliente, e `routed: true` para ele | esvaziar `"clients"` e ver o teste falhar |
| 3 | O compose dá a tabela ao agente | o mesmo teste: o mount e a variável estão lá | tirar o mount e ver o teste falhar |
| 4 | O harness tem gate | o job *The agent's own gate* corre em cada PR | abrir um PR que quebre um teste do harness e ver o job vermelho |
| 5 | O routing decide **na caixa** | `GET /v1/routing?client=tg:2115322359` → `"routed": true` | deixar a tabela sem a regra e ver `routed: false` com a razão |
| 6 | A tabela é recusada **na caixa** | meter uma regra para um runtime inexistente e ver `/v1/runtimes` reportar a recusa | tirar a regra e ver `problems: []` |
| 7 | Editar a tabela não reinicia | mudar a tabela e ver `/v1/routing` responder com a nova regra, sem restart | reiniciar o contentor e ver que também funciona — o teste é que **não** foi preciso |

---

## 10. Fora de escopo

| Coisa | Porque fica de fora | O que a reabre |
|---|---|---|
| **Um segundo bot token** | é produto: um canal novo é uma decisão do dono sobre que conversa existe, não sobre como o deploy a serve. A tabela já a aceita (uma linha). | a decisão do dono, e um token novo. |
| **A tabela fora do repositório** | esta ADR é a decisão. | um segundo deployment, que precisa da **mesma** tabela com outra forma — e aí a variável já aponta para outro sítio. |
| **O harness passa a ser Python** | ADR-037 D7: o agente é externo e tem o seu runtime. O Node é dele. | nunca, se a pergunta for "porquê". |
| **Rotinas que o registry não conhece** | o registry estreita o que um runtime pode correr; ele não **inventa** rotinas. | uma rotina nova na projecção — a tabela estreita-se com ela. |
| **Escrever de volta no vault** | ADR-012, por ADR-040 §10. Não éincremento: é a troca de um invariante. | uma ADR que substitua ADR-012 explicitamente. |

---

## 11. Decisões com default

| # | Decisão | Default | O que a muda |
|---|---|---|---|
| D1 | Onde a tabela vive | `deploy/runtimes.json`, versionada | um segundo deployment, que precisa da sua |
| D2 | O caminho da tabela no contentor | `/etc/ikigai/runtimes.json` | `HARNESS_RUNTIMES_FILE` |
| D3 | O runtime de um cliente não roteado | `owner` | a tabela (`"default"`) |
| D4 | O runtime do dono | `owner` — o provider do contentor, todas as rotinas | a tabela |
| D5 | Se a tabela é recusada | o registry recusa **e** responde com o default, e reporta a razão | nada: o fail-closed é o invariante |
| D6 | Se a edição da tabela reinicia o contentor | não — o mtime chega ao registry | nada: o hot-reload está escrito |

---

## 12. Camadas de falha

Cada uma falha sozinha, e nenhuma leva as outras:

| Camada | Se falhar | O que se vê |
|---|---|---|
| o ficheiro da tabela | não existe | o registry fica sem configuração e usa o runtime único — o comportamento anterior |
| o JSON | não é JSON válido | o registry recusa e reporta; o cliente cai no default |
| um runtime | nomeia um provider que o contentor não tem | o runtime é recusado, com a razão, em `/v1/runtimes` |
| uma regra | aponta para um runtime que não existe | a regra é recusada, com a razão; o cliente cai no default |
| o mount | o compose aponta para um sítio que não existe | o agente sobe sem tabela e usa o runtime único |
| o gate do CI | o job do agente não corre | o harness fica sem porta — e é a razão de o job existir |

---

## 13. Referências

- [ADR-041](./ADR-041-runtime-routing-and-human-in-the-loop.md) — o registo, a tabela, o HITL e o painel; §8 (evolução), §11 (decisões com default)
- [ADR-037](./ADR-037-data-layer-canonical-turn.md) — D7: o agente é externo e tem a sua própria imagem
- `deploy/harness/runtimes.mjs` — o registo, o routing e o fail-closed
- `deploy/harness/test/deployment.test.mjs` — a tabela do deployment, conferida pelo registry
- `specs/harness/SESSIONS.md` — §1.0 (onde a tabela vive) e o gate G7
- `.github/workflows/ci.yml` — o job *The agent's own gate*
- `src/ikigai/tests/test_deployment_surface.py` — a superfície do deployment (a porta do bot, a do agente, o token do websocket)
