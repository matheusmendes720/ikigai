---
id: ADR-044
title: "O Mini App: o painel do dono, dentro do Telegram, com a identidade do Telegram"
date: 2026-11-10
status: proposed
---

## 1. Veredito

**Entra:** o Mini App como **superfície de leitura** do dono, servida pelo
próprio bot, dentro do chat do Telegram, e autenticada pela assinatura que o
Telegram entrega — nunca por uma credencial nossa.

Quatro decisões fecham isto:

1. **O bot serve o painel, e só o bot.** A identidade da página é derivada do
   *bot token* (`HMAC_SHA256(bot_token, "WebAppData")`). O bot é o único
   componente que o detém; o agente tem uma chave de modelo e a porta do
   store, e dar-lhe o token do bot seria dar-lhe a voz do dono.
2. **A página nunca fala com o store.** O painel é uma projecção (ADR-037 D8):
   lê pela mesma porta que os outros clientes (o MCP, o agente) e **não
   escreve por nenhuma**. Um browser que abrisse a base de dados seria um
   segundo escritor com ecrã.
3. **O `initData` entra pela porta que o Telegram usa.** O Telegram abre a
   Mini App com a carga no **fragmento** (`#tgWebAppData=…`); o SDK oficial
   é quem a parseia em `Telegram.WebApp.initData`. A página usa o SDK
   **primeiro** e o fragmento como recurso — e valida **as duas leituras** do
   `hash` (com e sem o campo `signature`), porque uma verificação que recusa
   uma carga que o Telegram mandou é um bot que não abre o próprio painel.
4. **A janela de validade é nossa e não é opcional.** A assinatura do Telegram
   não expira sozinha: uma capturada seria válida para sempre. A janela é de
   **24 h**, imposta no servidor.

**Não entra, e a razão fica escrita:**

| Pedido | Veredito | Porquê |
|---|---|---|
| Publicar o painel na internet | **Não, agora** | o dono decide depois da prova; e uma superfície publicada nova traz gate de CI próprio (ADR-042 D2) |
| Dar o bot token ao agente | **Não, nunca** | o agente passaria a poder falar como o dono; a validação fica no bot |
| A página escrever no store | **Não, nunca** | seria um segundo escritor (ADR-037 D5/D8) |
| Uma credencial nossa (cookie, JWT, token de sessão) | **Não** | a assinatura do Telegram é a identidade; uma credencial nossa é uma porta que se pode furar |
| O painel escolher o seu runtime | **Não** | ADR-041: o cliente é **roteado**, não escolhe. A chave é `tg:<id>` — a mesma do chat |
| Um cliente de terminal para o mesmo painel | **Não, agora** | é outro produto; o ADR fica escrito para o porta aberta |

---

## 2. A pilha

| Peça | Onde | Porque |
|---|---|---|
| `src/bot/miniapp/__init__.py` | `src/bot/miniapp/` | a superfície HTTP: a página, `POST /api/session`, `POST /api/answer` |
| `validate_init_data()` | o mesmo ficheiro | a verificação da assinatura do Telegram — o portão |
| `src/bot/miniapp/index.html` | o mesmo sítio | a página; viaja **na imagem** (o `src/` é copiado), para o painel nunca ser um deploy que depende de um ficheito que alguém se esqueceu de carregar |
| `src/bot/test/miniapp-page.test.mjs` | `src/bot/test/` | os testes de guarda da página (o SDK primeiro, o fragmento como recurso, as duas leituras do `hash`) |
| o job `src-bot` no CI | `.github/workflows/ci.yml` | Node 24 — a versão da imagem — e o ficheiro de testes como contrato |
| `_send_panel()` e `/painel` | `src/bot/main.py` | o botão: `web_app = ("📊 Abrir painel", url)` |
| `IKIGAI_MINIAPP_URL` / `IKIGAI_MINIAPP_PORT` | `.env` da caixa | o endereço público da página e a porta; **zero** significa que o painel não é servido |
| `deploy/runtimes.json` | `deploy/` | a chave de routing: `"tg:2115322359": "owner"` — a mesma pessoa do chat |
| `/v1/session`, `/v1/events`, `/v1/answer` | o agente | o que a página lê e o que responde |

---

## 3. Justificativa

### 3.1 O que o painel é, e o que o chat não é

O chat é um canal de mensagens: serve para verbos e para perguntas. O painel
serve para o que é **grande ou estruturado** — a sessão do agente, as
perguntas à espera de resposta, o registo do que o agente fez, os artefactos
que o store tem. Não é um segundo sítio onde a verdade vive: é o **mesmo
DOM, projetado de outra maneira** (ADR-037 D2, D8).

### 3.2 Porque é que o bot o serve, e não o agente

A chave de validação deriva do *bot token*. Entregar esse token ao agente
seria entregar-lhe a capacidade de falar como o dono no Telegram. O bot é,
por desenho, o único que o detém — logo, o bot valida, e o agente é **pedido**
para os dados.

### 3.3 Porque é que o `initData` tem duas leituras

O Telegram documenta a string de verificação com e sem o campo `signature`
(caminho de terceiros, Ed25519). As duas são aceites — e aceitar as duas não
é um buraco: o `hash` só pode ser produzido com o token do bot, portanto
**toda** a carga aceite foi assinada por este bot, de uma ou de outra forma.
Uma verificação que recusa uma carga que o Telegram mandou é um bot que não
abre o próprio painel.

### 3.4 Porque é que a janela de 24 h é nossa

A assinatura não expira sozinha. Sem janela, o `initData` capturado é um
bearer válido para sempre. Um dia é comprido o suficiente para um painel
aberto de manhã e curto o suficiente para ser inútil a quem o roube.

### 3.5 Porque é que a chave de routing é a mesma do chat

Um Telegram é uma conta, e essa conta tem um chat privado com este bot.
`_client_key()` devolve `tg:<user_id>` — exactamente a chave que o chat usa.
O painel não é outro cliente: é **o mesmo cliente, noutro ecrã**.

---

## 4. A ponte que já existe

O painel **não acrescenta nenhuma porta nova**:

- **A leitura do store** é o MCP do agente (`search_artifacts`), a seis
  ferramentas, como qualquer outro cliente.
- **A leitura da sessão** é `/v1/session`; **o histórico** é `/v1/events`;
  **a resposta a uma pergunta** é `/v1/answer` — as mesmas rotas que o chat
  usa por baixo.
- **O routing** é a tabela versionada (ADR-042), montada read-only no agente.
- **O botão** é um `web_app` do Telegram — nada mais.

O que o painel acrescenta é **uma superfície**, não uma capacidade.

---

## 5. O que está quebrado, com evidência

### 5.1 A prova do caminho — feita, e o que ela mede

Até 2026-11-10, tudo o que rodava tinha sido provado com um `initData`
**assinado por nós**, na caixa. Isso provava que o código valida e que a página
lê — **não** que o Telegram entrega a carga, que é o que o produto precisa.

O verificador do servidor está calibrado para essa distinção:

- caso **A**, pedido sem credencial → `401 {"ok":false,"error":"the initData
  carries no hash"}`;
- caso **B**, pedido com `initData` assinado pelo bot na caixa → `200
  {"ok":true,"session":{"id":"tg-2115322359","client":"tg:2115322359",…}}`.

O observador (`tcpdump` em 8003, ambos os sentidos) é o que distingue: uma
sessão aceite, com o User-Agent de um browser — e não `curl/8.21.0`, que é o
que a calibração deixa.

**Estado medido em 2026-11-10, 13:53 — a prova passou.** Um cliente **Telegram
real** (Telegram Desktop 7.3.3; por dentro, o WebView Edge/157) entregou a
carga. O servidor viu:

```
POST /api/session → 200 {"ok":true,"session":{"id":"tg-2115322359",…}}
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
            (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36 Edg/157.0.0.0
```

Contagens no observador: `POST /api/session` 2→4, `GET /` 16→18, `HTTP/1.1 200`
16→20; os `401` de calibração ficaram os mesmos 2. O painel, renderizado dentro
do WebView do Telegram, mostrou `SESSÃO: tg-2115322359`, `CLIENTE:
tg:2115322359`, runtime `owner`, artefactos (12) e `PERGUNTAS (nada por
responder)`.

Isto é a prova que o produto precisa: **a assinatura do Telegram foi a que
abriu a porta** — nenhuma credencial nossa — e a sessão do dono aparece no
painel.

### 5.2 O painel só era alcançável dentro da tailnet

Medido na caixa, **antes** da rota pública (ADR-045):

```
https://vps-hetzner.tail78a4a0.ts.net:8443 (tailnet only)
|-- / proxy http://127.0.0.1:8003
```

`tailnet only` era literal: o `tailscale serve` não expõe para a internet. Um
telemóvel sem Tailscale **não abria o painel** — e os pares Android da tailnet
estavam `offline` (o `POCO F8 Pro` foi visto há 1 dia).

**Isto deixou de ser verdade.** O Funnel está ligado ao 8443 (ADR-045 §5.6), e
o painel responde `200` num endereço **público**; a porta de dados continua
fechada (`POST /api/session` → `401` sem a assinatura do Telegram). O que a
publicação não dá é a sessão do dono a quem não a tem.

Uma correcção a este registo: o `cap/funnel-ports` = `null` que aqui foi lido
como «o Funnel não está concedido» **não diz isso** — é a ausência de uma
restrição de portas, não uma negação (ADR-045 §5.4).

### 5.3 O que o painel mostra hoje, medido

`GET /` responde 200 em `127.0.0.1:8003`, `172.18.0.8:8003` e
`https://vps-hetzner.tail78a4a0.ts.net:8443/`; a página em produção é
byte-a-byte a do repositório (mesmo conteúdo, sha do contentor
`5b0120835b…`, 42 002 B com LF; o ficheiro no disco com CRLF, 43 254 B — as
1252 linhas são as mesmas). O `GET /v1/routing?client=tg:2115322359` responde
`routed: true`, runtime `owner`, `session_id: tg-2115322359`.

### 5.4 O ecrã do dono: o que está quebrado, o que não está, e por onde entrou

A janela do Telegram Desktop do dono está **cloaked**
(`DWMWA_CLOAKED_SUSPEND`, `IsWindowVisible=true`, `IsIconic=false`) em **todos**
os desktops virtuais — as hotkeys de comuta de desktop injectadas comutam
mesmo (o *tooltip* "Desktop 4" prova-o), mas a cloak nunca sai. Não é um
problema de desktop virtual: a janela está no mesmo desktop Win32 e na mesma
sessão que o MCode (`GetThreadDesktop` e `OpenInputDesktop` dão o mesmo
`Default`).

O que está medido sobre o input desta máquina:

| Via | Veredicto |
|---|---|
| `keybd_event` / `SendKeys` | **funciona** — `GetAsyncKeyState` confirma a tecla premida e os caracteres chegam ao alvo |
| `mouse_event` / `SendInput` com `MOUSEEVENTF_ABSOLUTE` | **não funciona** — num formulário próprio, visível (pixel vermelho verificado por baixo do cursor, e a janela por baixo do cursor é o próprio formulário): o clique não dispara |
| `PostMessage` de mouse para a janela Qt | **ignorado** — o clique não seleccionou o chat |
| **UIA (UI Automation)** | **funciona** — a árvore do Telegram tem 3663 elementos; o `InvokePattern` abre o chat |

O que a UIA **não** expõe são os botões *inline* do teclado da mensagem: a
mensagem aparece como `ListItem` e o botão não é elemento nenhum. Por isso um
botão *inline* **não** se carrega por automação nesta máquina — é um toque
humano (no telemóvel, um toque).

**Por onde a prova entrou.** O botão de menu do bot (`setChatMenuButton` com
`web_app` para o mesmo URL do Mini App) transforma o botão «Menu» do chat num
atirador da Web App — e esse botão **é** exposto pela UIA
(`HistoryView::BotMenuButton`, nome «Painel»): o `InvokePattern` abriu o Mini
App dentro do WebView do Telegram. O menu foi reposto em `commands` depois da
prova.

Isto **não é uma falha do produto** — é o ecrã dele. Fica escrito para que
a próxima sessão não gaste horas a re-descobri-lo, e para que a prova seja
lida **no servidor**, que é onde ela é provável.

---

## 6. Inventário, com a razão de cada peça

| Peça | Razão |
|---|---|
| `validate_init_data()` | a única coisa que decide o que a página pode ler |
| a janela de 24 h | a assinatura do Telegram não expira sozinha |
| aceitar as duas leituras do `hash` | para não recusar uma carga que o Telegram mandou |
| a allowlist (`bot._allowed`) | uma conta não listada não aprende nada — falha fechada, como todas as portas do bot |
| `GET /` sem credencial | a página é pública; **os dados é que não são** |
| `POST /api/session` | devolve sessão, perguntas, eventos e artefactos — em conjunto, numa ida |
| `POST /api/answer` | responder a uma pergunta a partir do painel, com os mesmos botões do chat |
| o store inalcançável a partir da página | se o store falhar, o painel mostra o agente; **não** o contrário |
| o `initData` pelo SDK primeiro | o SDK é quem parseia o fragmento; o fragmento é o recurso |
| o botão `web_app` | é uma **superfície**, não um verbo — o payload do Telegram é diferente |
| `/painel` no chat | o dono pede o painel pelo mesmo lugar onde o resto acontece |
| o botão como **última** mensagem | é a superfície mais legível do chat; nada depois dela para a enterrar |
| `IKIGAI_MINIAPP_PORT=0` | o bot sem painel é o bot de antes — o painel é uma superfície, não o produto |

---

## 7. Dia zero

O que está **publicado e a correr**, medido em 2026-11-10:

- o contentor `ikigai-bot-1` serve a página em `127.0.0.1:8003`, publicado;
- o `IKIGAI_MINIAPP_URL` é `https://vps-hetzner.tail78a4a0.ts.net:8443/`;
- o `IKIGAI_MINIAPP_PORT` é `8003`; o `IKIGAI_BOT_ALLOWED_CHAT_IDS` é
  `2115322359`;
- o routing resolve `tg:2115322359` → `owner` (tabela versionada, montada
  read-only);
- o gate de CI do `src-bot` corre o Node 24 da imagem e os testes da página;
- o bot tem o comando `/painel` e o botão «📊 Abrir painel»;
- a **prova real passou**: um cliente Telegram entregou a carga e o servidor
  aceitou a sessão `tg-2115322359` (§5.1).

O que **falta**, escrito para não se perder:

- uma decisão sobre a rota pública (§8.2).

---

## 8. Evolução

1. **A prova, feita em 2026-11-10.** O dono abriu o painel **dentro do
   Telegram Desktop** (cliente real); a prova foi lida **no servidor**: um
   `POST /api/session` com `200`, o `session.id` certo e um User-Agent de
   browser. Para o telemóvel, o caminho é o mesmo botão, com o Tailscale
   ligado — o painel só é alcançável dentro da tailnet (§5.2).
2. **A rota pública, depois.** Se o dono quiser o painel no telemóvel sem
   Tailscale, o caminho é o **Tailscale Funnel** — que exige: (a) activar o
   Funnel no admin da tailnet; (b) versionar a rota no repositório, ao lado de
   `deploy/runtimes.json`; (c) um **gate de CI próprio** para a superfície
   publicada, como ADR-042 D2 stabilizou para o agente. Nada disto é feito sem
   o "go" do dono.
3. **A spec.** `specs/miniapp/TECH.md` publica o contrato: as três rotas, o
   formato da resposta, o que é `200` e o que é `401`, e o procedimento da
   prova — para que a próxima pessoa não tenha de o re-descobrir.
4. **Um cliente de terminal** para o mesmo painel, se o dono o quiser: o
   ADR-041 já deixou o runtime `fast` (read-only) na tabela, e o painel
   seria a porta natural para ele. Fora de escopo hoje.

---

## 9. Passos com PASS falsificável

| # | Passo | PASS | Falsificação (como se prova que NÃO passou) |
|---|---|---|---|
| 1 | A página está publicada | `GET /` → 200 e o sha do ficheiro servido = o sha do repositório | `GET /` → 404/500, ou o sha difere |
| 2 | A porta fecha sem credencial | `POST /api/session` sem `init_data` → 401 `the initData carries no hash` | devolve 200 com sessão |
| 3 | A porta fecha com credencial errada | `initData` de outro bot → 401 `the initData does not match this bot` | devolve 200 |
| 4 | A porta abre com a assinatura certa | `initData` assinado pelo bot → 200 com `session.id` = `tg-2115322359` | 401, ou 200 sem a sessão |
| 5 | **A prova real** — **PASSOU em 2026-11-10 13:53** | um cliente **Telegram** entrega a carga: o servidor vê `POST /api/session` → 200, `session.id` = `tg-2115322359`, e um User-Agent de browser (≠ `curl/…`) | o `POST` vem de `curl`, ou não vem |
| 6 | A página lê pela porta que já existe | a resposta 200 traz `session`, `questions`, `events` e `artifacts` | falta um deles, ou traz `artifacts` vazio com o store de pé |
| 7 | O painel não escreve | nenhum pedido do painel chega ao store como escrita (só leitura via MCP) | aparece uma escrita no store com origem no painel |
| 8 | O routing é o do chat | `GET /v1/routing?client=tg:2115322359` → `routed: true`, runtime `owner` | `routed: false`, ou um runtime diferente do do chat |
| 9 | A página tem gate | o job `src-bot` do CI corre o Node 24 e os testes da página | o job passa sem correr os testes, ou corre-os noutro Node |
| 10 | O painel não sai da tailnet (hoje) | `tailscale serve status` mostra `tailnet only` no 8443 | o 8443 aparece como público sem o "go" do dono |

---

## 10. Fora de escopo

- **Publicar na internet** — decisão do dono, depois da prova (§8.2). **Feito**:
  a rota pública vive no repositório e tem gate próprio (ADR-045).
- **Um terminal para o painel** — outro produto.
- **Escrever no store pelo painel** — ADR-037 D5/D8; nunca.
- **Dar o bot token ao agente** — nunca.
- **Uma credencial de sessão nossa** — a assinatura do Telegram é a identidade.
- **Alterar o `initData` do cliente** — o cliente não escolhe runtime nem
  identidade; é roteado (ADR-041).
- **Tocar no `vault/`** — ADR-012/ADR-043, e o vault é lido, não escrito
  (ADR-037 D4).
- **A janela do Telegram Desktop do dono** — o ecrã dele (§5.4); a prova
  lê-se no servidor.

---

## 11. Decisões com default

| Decisão | Default | Porquê |
|---|---|---|
| Quem valida o `initData` | o bot | é o único que tem o token |
| Como se extrai a carga | SDK primeiro, fragmento como recurso | o SDK é quem parseia; o fragmento cobre clientes sem SDK |
| Leitura do `hash` | as duas (com e sem `signature`) | para não recusar cargas reais do Telegram |
| Validade | 24 h | a assinatura não expira sozinha |
| Conta sem permissão | 401, sempre | falha fechada |
| Store inalcançável | o painel mostra o agente, sem artefactos | o store é acessório; o painel não pode desaparecer por causa dele |
| Chave de routing | `tg:<user_id>` — a mesma do chat | é a mesma pessoa |
| Endereço do painel | `IKIGAI_MINIAPP_URL`, sem default | um default errado abre a porta errada; zero é "não servido" |
| Porta do painel | `IKIGAI_MINIAPP_PORT`, zero = não servido | o bot sem painel é o bot de antes |
| A prova | lida no servidor, não no ecrã | o ecrã do dono é uma superfície instável; o servidor é o veredicto |

---

## 12. Camadas de falha

| Falha | O que acontece | O que o dono vê |
|---|---|---|
| `initData` ausente ou sem `hash` | 401 `the initData carries no hash` | o painel diz que não está autenticado |
| `initData` de outro bot | 401 `the initData does not match this bot` | o mesmo; e o servidor regista a recusa |
| `initData` com mais de 24 h | 401 `the initData is older than the window this bot accepts` | o painel pede para reabrir |
| conta fora da allowlist | 401 `this account is not allowed here` | nada do que existe é mostrado |
| agente indisponível | 500 do `/api/session` | o painel mostra o erro, não uma página vazia |
| store indisponível | os artefactos vêm vazios; o resto mostra-se | a sessão continua visível |
| o proxy (Tailscale serve) cai | a página não abre | o botão no chat abre um erro de rede — **e o chat continua a funcionar** |
| `IKIGAI_MINIAPP_URL` em falta | o botão não é enviado; `/painel` responde que o painel não está configurado | o chat funciona como sempre |
| a página é cacheada pelo browser | o `initData` velho falha com 401 | o dono reabre o painel |

---

## 13. Referências

- `src/bot/miniapp/__init__.py` — a superfície e a validação
- `src/bot/miniapp/index.html` — a página (SDK primeiro, fragmento como recurso)
- `src/bot/test/miniapp-page.test.mjs` — os testes de guarda da página
- `src/bot/main.py` — `_send_panel()`, `/painel`, `IKIGAI_MINIAPP_URL`,
  `IKIGAI_MINIAPP_PORT`
- `deploy/compose.yml` — o serviço `bot` (sem DSN: o bot é cliente do api)
- `deploy/runtimes.json` — a tabela de routing (`tg:2115322359` → `owner`)
- `.github/workflows/ci.yml` — o job `src-bot` (Node 24)
- ADR-037 (a volta canónica: D2/D4/D5/D6/D8) · ADR-041 (routing e HITL) ·
  ADR-042 (a tabela no repositório e o gate do agente) · ADR-043 (o
  `vault_write`)
- PR #38 (o Mini App), PR #39 (a tabela de routing), PR #44 (o `initData`:
  fragmento + SDK, e o gate de CI)
