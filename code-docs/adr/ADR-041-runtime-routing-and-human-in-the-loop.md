# ADR-041 — O runtime é o agente: o Telegram passa a ser o canal, e o agente pergunta

**Status:** Accepted
**Date:** 2026-11-09
**Deciders:** human (Matheus) + agent
**Scope:** o que um cliente Telegram deixa de ser (o dono da conversa) e passa a ser (o canal de um runtime agêntico), e como o agente consegue perguntar ao dono sem inventar um sétimo tool na api
**Anchor:** [ADR-037](./ADR-037-data-layer-canonical-turn.md) · [ADR-039](./ADR-039-websocket-sync-transport.md) · [ADR-040](./ADR-040-client-state-and-drafts.md)

---

## 1. Veredito

**Entra:** três decisões que juntas turning o bot num **canal de um runtime**:

1. **O roteamento por cliente.** O harness passa a ter um **registo de runtimes** — perfis com provider, modelo, rotinas permitidas e âmbito de memória — e uma **tabela de routing** que diz qual runtime serve qual cliente. O bot deixa de "usar o agente": ele **pergunta** ao harness qual runtime o serve.
2. **O HITL a bloquear.** O agente ganha **um tool próprio, `ask`**, que **suspende o turno** até o dono responder. A pergunta vive no runtime (SQLite), não no bot: um restart do bot não a perde, e o agente continua suspenso, com o contexto intacto.
3. **O Mini App servido pelo bot.** Um painel Web App que mostra a sessão, as perguntas à espera e o que o agente fez — autenticado pelo `initData` do Telegram, e servido pelo **bot**, porque o bot é o único que tem o token de que a identidade da página é feita.

**Não entra, e a razão fica escrita:**

| Pedido | Veredito | Porquê |
|---|---|---|
| um **sétimo tool na api** para perguntar ao dono | **recusado** | a api tem exactamente seis tools, guardadas por drift test (ADR-011, ADR-037 D6); e perguntar ao dono não é uma operação de store — a api é a porta do DOM, e o dono não é o DOM |
| o `ask` como **convenção de texto** ("termina o turno com PENDENCIA:") | **recusado** | uma convenção é uma promessa que o modelo pode cumprir, esquecer ou formular de outra maneira; um tool é uma **capacidade**, e a chamada é o que suspende o turno |
| a pergunta a viver **no bot** | **recusado** | o agente está suspenso à espera dela; se ela morresse com o processo do bot, o agente esperaria até ao deadline sem ninguém que pudesse responder |
| o **bot** a escolher o modelo | **recusado** | o cliente não nomeia um modelo: o cliente é **roteado** a um. Quem decide o que o agente é é o runtime, não a superfície |
| `sendRichMessage`, `sendMessageDraft`, **topics** de Telegram | **adiado** | são APIs do bot api que este deploy não usa; o `sendMessage` com `reply_markup` resolve o HITL, e o resto é evolução (§8) |

---

## 2. A pilha

```
Telegram ──update──► bot (canal)
                        │  valida initData, desenha botões
                        │  POST /v1/owner/answer
                        ▼
                    harness (runtime)
                     │  registo de runtimes + routing
                     │  sessão + perguntas (SQLite)
                     │  log do agente (feed com cursor)
                     ▼
                    pi (agente)  ──mcp__owner__ask──►  espera a resposta
                     │                                  ▲
                     └──mcp__ikigai (6 tools)──────────┘
                                │
                                ▼
                            store (DOM)
```

Three properties and one consequence:

- **O bot fala com o harness**, e o harness fala com o `pi`. O bot **nunca** fala com o `pi`, e o `pi` **nunca** fala com o Telegram.
- **A pergunta é estado do runtime**, e o log do agente é um **feed retomável** — a mesma forma do feed do store (ADR-039): o cliente diz o que tem e recebe o que não tem, por ordem.
- **O `pi` é externo** (ADR-037 D7). O `ask` vive **dentro da imagem do harness**, ao lado do `pi`, e é alcançado por MCP — a *superfície de tools do agente*, que não é a *superfície de tools da api*.

---

## 3. Justificativa

### 3.1 Porquê um registo de runtimes

Um deploy tem **um** agente: o provider e o modelo estavam no `models.json` da imagem, escritos a partir do ambiente. O momento em que aparece um **segundo cliente** — um segundo bot token, uma TUI, um chat de grupo — "o agente" deixa de ser uma coisa só. Um cliente pode querer o modelo forte e demorado, o outro o modelo barato e rápido, e um cliente que **não pode** tocar no store é um cliente com um conjunto de rotinas diferente.

O runtime é essa nomeação: um perfil com provider, modelo, rotinas permitidas e âmbito de memória. O cliente não diz "quero o modelo X": o cliente **é roteado** a um runtime, e o harness decide.

### 3.2 Porquê o `ask` bloqueia, e não notifica

A diferença entre *notificar* e *esperar* é a diferença entre um agente que sabe que o dono responderá mais tarde e um agente **suspenso** na pergunta, com o contexto intacto, que retoma exactamente no ponto em que parou.

O `pi` expõe `steer()` e `followUp()` — a resposta pode entrar **a meio** do turno. E o `pi` tem um primitivo HITL próprio, o `extension_ui` (`select`, `confirm`, `input`, `editor`), que bloqueia o agente até o cliente responder.

**Medido, no pacote `pi` 1.5.0:** o `RpcClient` **não expõe** a resposta do `extension_ui` — o `send` é `private` (`dist/modes/rpc/rpc-client.d.ts`). Por isso o `extension_ui` não é o caminho: o caminho é um **tool MCP do próprio agente**, que é onde a capacidade "perguntar" pertence.

### 3.3 Porquê o tool vive no harness, e não na api

Três razões, e as três são do repo:

1. **A api tem seis tools.** `test_drift_invariants.py` guarda `CANONICAL_TOOLS`. Um sétimo tool é uma **mudança de contrato** (ADR-011), não uma conveniência.
2. **A api é a porta do DOM.** Perguntar ao dono não lê nem escreve nada do DOM; é uma conversa. O `owner` é o **dono**, e o dono não é o DOM (ADR-037 D4).
3. **O agente escreve pela api, como qualquer cliente.** Continua a haver **um writer** por store (ADR-037 D5): o `ask` não escreve no DOM — pergunta.

### 3.4 Porquê o painel é servido pelo bot

A validação do `initData` é `HMAC_SHA256(bot_token, "WebAppData")`. O bot é o **único** componente que tem o token do Telegram. Dar o token ao harness para que ele sirva a página significaria dar ao harness a capacidade de **falar como o dono**. O bot valida; o harness fornece os dados.

---

## 4. A ponte que já existe

| O que já lá estava | O que esta ADR usa |
|---|---|
| o harness é um façade HTTP sobre o `pi`, com `pi` por sessão (`--session-id`) | a sessão **é** a conversa; o runtime é a máquina que a segura |
| `memory.mjs` já tinha um log append-only (`events`, com `seq`) | o log do agente passa a ser um **feed com cursor**, como o do store |
| o `.pi/mcp.json` é gerado pelo `entrypoint.sh` | ganha um **segundo servidor MCP**: o `owner` |
| o `pi` lê `.pi/mcp.json` do projecto e interpola `${VAR}` no `env` | o harness marca a sessão no ambiente do `pi` (`IKIGAI_SESSION_ID`) |
| o bot já fala `reply_markup` e `callback_query` (PR #33) | o mesmo mecanismo passa a desenhar as **perguntas** do agente |
| o `pi` já tem **fallback** de provider (`deepseek`), medido no contentor | o runtime nomeia o seu provider — e o fallback continua a ser do harness |
| o Traefik do host já serve `api/ws/harness` com TLS | o mesmo proxy serve o painel |

---

## 5. O que está quebrado, com evidência

| Quebra | Evidência | Consequência |
|---|---|---|
| o agente não tem como perguntar | o `RpcClient` não expõe o `extension_ui_response` (`private send;`) | a única forma de o agente pedir uma decisão era acabar o turno e esperar que a mensagem seguinte fosse a resposta |
| um cliente não escolhe o agente | o provider e o modelo estavam no `models.json` da imagem | um segundo cliente não pode ter outro modelo sem outra imagem |
| o log do agente não se relia | `memory.events()` era "os últimos N", por ordem **descendente** | um cliente que recomeçasse não sabe o que já viu |
| o painel não tem onde morar | o token do Telegram só existe no bot; o harness não o tem | servir a página no harness significava duplicar o token |
| a allowlist do bot vivo está por definir | `IKIGAI_BOT_ALLOWED_CHAT_IDS=TODO-SET-ME` no `deploy/.env` do servidor | o bot falha fechado (por desenho) — o ensaio tem de ser com gravador, sem tocar no bot real |

---

## 6. Inventário, com a razão de cada peça

| Peça | Onde | Porque |
|---|---|---|
| `runtimes.mjs` | `deploy/harness/` | o registo e o routing: fail-closed, com razão |
| `owner.mjs` | `deploy/harness/` | a sala de espera: a pergunta e a resposta |
| `owner-mcp.mjs` | `deploy/harness/` | o tool `ask`: bloqueia até o dono responder |
| `memory.mjs` (novas tabelas) | `deploy/harness/` | `questions` + feed com cursor |
| `server.mjs` (rotas novas) | `deploy/harness/` | `/v1/routing`, `/v1/session`, `/v1/events`, `/v1/owner/ask`, `/v1/owner/answer` |
| `channel.py` | `src/bot/` | as quatro formas de pergunta → botões |
| `harness_client.py` (novos métodos) | `src/bot/` | rota, sessão, feed, resposta |
| `miniapp/` | `src/bot/` | a página + a validação do `initData` |
| `@modelcontextprotocol/sdk` (pinado) | `deploy/harness/package.json` | o servidor MCP — o protocolo escrito à mão é o risco que não se paga |
| entrada `src-bot` na matriz do CI | `.github/workflows/ci.yml` | o `src/bot/` era código publicado **sem gate** |

**Decisões dentro das peças, e porquê:**

- **O `ask` corre por stdio, e não por HTTP.** O `pi` nasce os servidores MCP, portanto o servidor do `owner` é **filho do agente** — um por sessão, com a vida útil da sessão. O `session_id` viaja no ambiente (`IKIGAI_SESSION_ID`), e como **segunda testemunha** na linha de comandos do pai (`--session-id`). Duas testemunhas que **discordam** são uma recusa: uma pergunta feita na conversa errada é pior do que nenhuma pergunta.
- **A opção viaja como índice, nunca como texto.** O Telegram limita `callback_data` a 64 bytes e falha **em silêncio** quando se passa. O texto da opção é do runtime, e é o runtime que a resolve.
- **O `ask` expira, e a expiração é uma resposta.** Passado o deadline, o tool devolve um erro que diz ao agente para continuar com a sua melhor leitura — e para dizer que o dono não respondeu. Um turno que nunca acaba é pior do que uma resposta honesta.
- **O painel serve-se do bot, e o bot valida.** Ver §3.4.

---

## 7. Dia zero

Nenhuma migração. O harness ganha rotas e uma tabela; o `owner` ganha um servidor MCP e um ficheiro de runtime; o bot ganha um canal e um painel.

```bash
# o harness instala o SDK MCP pinado (o lock é o contrato)
cd deploy/harness && npm ci --omit=dev --ignore-scripts

# as rotas novas, no arranque
curl -s localhost:8002/v1/runtimes | jq
curl -s "localhost:8002/v1/routing?client=tg:9138296750" | jq
curl -s "localhost:8002/v1/events?session=tg:9138296750&since=0" | jq
```

O `.pi/mcp.json` do contentor passa a ter dois servidores: `ikigai` (os seis tools) e `owner` (o `ask`).

---

## 8. Evolução

| Ordem | O quê | Porquê agora |
|---|---|---|
| 1 | **vários tokens → vários runtimes** | a tabela de routing já existe; acrescentar um token é uma linha de JSON |
| 2 | **`sendRichMessage`** | o relatório do agente é uma tabela e uma decisão; `sendMessage` corta a 4000 caracteres |
| 3 | **`sendMessageDraft` + Stop** | o dono vê a resposta a formar-se, e tem um gesto nativo para a parar |
| 4 | **topics de Telegram** | uma conversa por rotina, em paralelo, retomável |
| 5 | **o painel com escrita** | hoje lê; quando escrever, só depois de `showConfirm`, e pela `upsert_artifact` |
| 6 | **`steer()`** | a resposta entra a meio do turno, sem esperar pelo fim |

---

## 9. Passos com PASS falsificável

| # | Passo | PASS |
|---|---|---|
| G1 | o registo de runtimes decide, e recusa o que está errado | `node --test deploy/harness/test/` → o routing recusa um provider desconhecido, um cliente sem runtime e um id que não é slug, **com a razão** |
| G2 | o `ask` bloqueia e devolve a resposta | o teste do MCP real: o `tools/call` não volta, a pergunta chega ao broker, o dono responde, a chamada volta **com a resposta** |
| G3 | uma pergunta sem resposta acaba, não fica pendurada | o mesmo teste, com o deadline a passar: o tool devolve `isError` e diz que o dono não respondeu |
| G4 | o bot desenha a pergunta e o botão entrega a resposta | `tests/transport/test_bot_channel.py`: as quatro formas, o payload ≤ 64 bytes, o round-trip |
| G5 | o painel sabe quem lhe pergunta | `tests/transport/test_bot_miniapp.py`: o `initData` válido passa; o forjado, o de outro bot e o velho são recusados |
| G6 | o routing é visível | `GET /v1/routing?client=…` devolve o runtime **e a razão** |

---

## 10. Fora de escopo

- **O `extension_ui` do `pi`** (`select`/`confirm`/`input` nativos): exige escrever na stdin do processo do agente, e o `RpcClient` não expõe essa escrita. Fica para quando o `pi` a expor.
- **`sendRichMessage`, `sendMessageDraft`, topics, menu button**: APIs do bot api que este deploy não usa (ADR-038 do Bot API, §8).
- **O `pi` a falar com o Telegram directamente**: o agente não fala com o dono; o runtime pergunta, e o **canal** desenha.
- **A página a escrever no store**: o painel é uma projecção. Escrever passa por `upsert_artifact` e por um `showConfirm` — e por uma ADR própria.
- **Sincronização bi-direccional do vault** (ADR-012) e a camada algorítmica (ADR-037 D1): recusados, e a razão está escrita em §1.

---

## 11. Decisões com default

| Decisão | Default | Onde se muda |
|---|---|---|
| o runtime de um cliente não roteado | `owner` (o perfil único, com o provider do contentor) | `HARNESS_RUNTIMES` / `HARNESS_RUNTIMES_FILE` |
| o deadline de uma pergunta | 15 minutos | `HARNESS_OWNER_TIMEOUT_MS` |
| o timeout do transporte MCP do `owner` | 960 s — **maior** que o deadline, para que a pergunta expire antes do transporte | `HARNESS_OWNER_MCP_TIMEOUT_S` |
| a porta do painel | **nenhuma** (o painel não arranca) | `IKIGAI_MINIAPP_PORT` |
| o URL do painel | **nenhum** (`/painel` diz que não está configurado) | `IKIGAI_MINIAPP_URL` |
| o intervalo do feed do agente | 2 s | `RUNTIME_POLL_S` (código) |
| a forma de uma pergunta | `text` | o `ask` aceita `choice`, `confirm`, `text`, `editor` |

---

## 12. Camadas de falha

Cada uma falha sozinha, e nenhuma leva as outras:

| Camada | Se falhar | O que o dono vê |
|---|---|---|
| o `owner` MCP não arranca | o agente não tem o `ask`; a rotina corre até ao fim | o relatório chega, sem perguntas |
| a pergunta não é entregue (o bot caiu) | a pergunta fica `pending` no runtime; o bot re-encontra-a no feed | o dono recebe a pergunta quando o bot volta |
| o deadline passa | a pergunta fica `expired`; o tool devolve erro | o agente continua com a sua leitura e diz que o dono não respondeu |
| a resposta chega twice | a segunda é recusada (`already answered`) | o bot diz que a pergunta já estava respondida |
| o runtime não tem a rotina | o harness recusa com 403 e diz as rotinas que tem | o bot diz que este runtime não corre essa rotina |
| o provider recusa | o fallback do harness (deepseek) assume, e o relatório diz que veio do secundário | o relatório vem com a nota do fallback |
| o painel não valida o `initData` | 401 | a página diz "ligação não autenticada" e para de pollar |
| o proxy não tem certificado | o painel não abre | o `/painel` continua a funcionar no chat |

---

## 13. Referências

- [ADR-037](./ADR-037-data-layer-canonical-turn.md) — D4 (store canónico), D5 (um writer), D6 (seis tools), D7 (o agente é externo)
- [ADR-039](./ADR-039-websocket-sync-transport.md) — o feed retomável, que o log do agente passou a ter
- [ADR-040](./ADR-040-client-state-and-drafts.md) — o draft é estado, e o estado vive no store; a pergunta do agente é estado, e vive no runtime
- [ADR-011](./ADR-011-ikigai-mcp-http-sse-transport.md) — a superfície de seis tools da api
- `specs/harness/router.md` — os papéis e as cadências
- `specs/harness/CHAINED-ROUTINES.md` — a cadeia (router → sessão → rotina → síntese → HITL), que esta ADR completa pelo lado do *bloqueio*
- `specs/harness/SESSIONS.md` — o protocolo publicado: routing, sessões, o tool `ask`, o canal, o painel
- `deploy/harness/` — `runtimes.mjs`, `owner.mjs`, `owner-mcp.mjs`, `server.mjs`, `memory.mjs`
- `src/bot/` — `channel.py`, `harness_client.py`, `miniapp/`
- `src/ikigai/tests/transport/test_bot_channel.py` · `src/ikigai/tests/transport/test_bot_miniapp.py` — G4 e G5
- `deploy/harness/test/` — G1, G2 e G3
- [Telegram Mini Apps](https://core.telegram.org/bots/webapps) — a validação do `initData`
- [Telegram Bot Features](https://core.telegram.org/bots/features) — `reply_markup`, `callback_query`, o Web App
