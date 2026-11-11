---
id: ADR-045
title: "A rota pública do Mini App vive no repositório, e a superfície publicada tem gate próprio"
date: 2026-11-10
status: accepted
---

## 1. Veredito

**Entra:** duas decisões que fecham o que ADR-044 deixou aberto, e uma
consequência que elas passam a suportar.

1. **A rota é um ficheiro versionado.** `deploy/surfaces.json` é a tabela das
   superfícies publicadas: vai no repositório, no mesmo commit que o deploy, e
   é montada **read-only** no bot em `/etc/ikigai/surfaces.json`. O estado
   vive na tabela — `pending` ou `published` — e **publicado ≠ decidido**:
   o estado é uma palavra do dono, não um facto que o código deduza.
2. **A superfície publicada tem gate próprio.** Duas portas, e cada uma mede
   uma coisa diferente:
   - o **contrato** no CI — *The published surface (gate próprio)* — que
     pergunta se a tabela, o mount e o aplicador continuam de acordo;
   - o **efeito** no deploy — *The published surface (live, outside the
     tailnet)* — que pergunta, a partir de um runner **fora** da tailnet, se
     a superfície publicada responde `200` e se a sua porta de dados responde
     `401`.
3. **O aplicador é estreito, por medição.** `deploy/apply-surfaces.sh` toca
   **apenas** o `host:port` e o path que a tabela declara, passa **sempre**
   `--https` **e** `--set-path`, **nunca** faz `funnel reset`, e fotografa a
   configuração antes e depois para restaurar o que não é seu se algo a
   mexer.

**A tabela está com `state: published`.** A rota foi publicada (medido, §5.6) e o
estado no repositório diz o que é: **publicado ≠ decidido** continua a valer — o
estado é uma palavra do dono, não um facto que o código deduza — mas a palavra
já foi dita. Um repositório que declarasse `pending` com o Funnel ligado seria
um repositório a mentir sobre o que está no ar, e a mentira acabaria num
deploy que volta a desligar o que o dono ligou.

**Não entra, e a razão fica escrita:**

| Pedido | Veredicto | Porquê |
|---|---|---|
| Publicar no **443** | **Não** | nesse host vivem o api MCP, o harness do agente e três rotas de outra sessão (Athena, Hefesto, telegram). Uma superfície publicada de lá publica todas. |
| A rota no `.env` da caixa, em JSON inline | **Não** | ADR-042 D2, um nível acima: uma tabela dentro de uma string de ambiente é uma tabela que ninguém revê. |
| Um CDN à frente da superfície | **Não** | o Funnel já é a porta pública, com o certificado que o Telegram exige (HTTPS). Um CDN traz um problema novo — a chave do `initData` tem de chegar ao backend, e um proxy que reescreve o pedido muda o que o backend vê. |
| O `funnel reset` como "limpeza" | **Não, nunca** | medido: apaga o config **todo** — o 443, o 8443 e o 8444 de outra deployment. |
| O Funnel concedido pelo pipeline | **Não** | é uma capacidade da tailnet, decidida no admin da Tailscale. O pipeline publica o que a tabela diz; não concede o que a tailnet permite. |
| O Funnel ligado à mão, sem o repositório | **Não** | foi o que custou o incidente de §5.1. O que se aplica na caixa tem de ser o que a tabela diz — e a tabela está no repositório. |

---

## 2. A pilha

| Peça | Onde | Porque |
|---|---|---|
| `deploy/surfaces.json` | `deploy/` | a tabela: versionada, no commit que o deploy traz, com o estado à vista |
| `src/bot/surfaces.py` | `src/bot/` | o **único** leitor da tabela; fail-closed, e a tabela é a verdade, o ambiente é o fallback |
| o mount e o `IKIGAI_SURFACES_FILE` | `deploy/compose.yml` | o bot tem de saber **onde** a tabela está, e tem de a ter montada **read-only** |
| `deploy/apply-surfaces.sh` | `deploy/` | quem põe a rota na caixa; estreito, verificado, e sem `funnel reset` |
| `src/ikigai/tests/test_published_surface.py` | `src/ikigai/tests/` | os guards: a tabela contra o deployment, o consumidor contra o que ele não implementa, o aplicador contra as formas medidas |
| o job *The published surface (gate próprio)* | `.github/workflows/ci.yml` | o **contrato**: a superfície deixa de ser a única porta publicada sem gate |
| o job *The published surface (live, outside the tailnet)* | `.github/workflows/deploy.yml` | o **efeito**: a rota pública, medida de fora da tailnet |
| §8 na spec | `specs/miniapp/TECH.md` | a spec publicada passa a dizer **onde** a rota vive e como ela é conferida |

---

## 3. Justificativa

ADR-044 **provou** o caminho: o Telegram entregou o `initData` genuíno, o
`POST /api/session` devolveu `200` com `session.id = tg-2115322359`, e o painel
renderizou no WebView do Telegram. O painel existe e funciona.

O que ADR-044 deixou aberto era o **onde** e o **quando**. Três buracos, e
nenhum deles era o produto:

- **A rota não vivia em lado nenhum que se possa rever.** O bot tinha
  `IKIGAI_MINIAPP_URL` no `.env` da caixa: o endereço do painel era uma
  variável de ambiente escrita à mão, sem revisão, sem histórico, sem
  diferença entre o que o repositório diz e o que a caixa serve. Um `.env` é
  um ficheiro que ninguém lê num pull request — e a rota é a decisão mais
  reversível e mais consequente de um produto com uma porta pública.
- **A superfície publicada era a única sem gate.** A matriz do CI tem seis
  pacotes Python e o entry `src-bot` fecha a página; o `node --test` do
  harness tem job próprio desde ADR-042. A **superfície** — a tabela, o
  mount, o aplicador — não tinha gate nenhum: podia partir o roteamento, ou
  publicar a rota errada, e o pipeline não dizia nada.
- **A rota era aplicada à mão, e a mão mediu o custo.** Publicar o Funnel à
  mão, nesta caixa, tirou o api MCP do ar (medido, §5). A reparação levou
  uma fotografia das rotas e três comandos. Uma rota aplicada à mão é uma
  rota que ninguém consegue raciocinar: ninguém sabe, depois, o que mudou.

E há uma assimetria que obriga a decidir já: o **443** desta caixa é um
host partilhado com outra sessão. Publicar de lá não publica o painel —
publica o api, o harness e três rotas que não são nossas. A rota pública do
painel **tem** de ser a sua: o **8443**, o host que só carrega o painel.

---

## 4. A ponte que já existe

- O bot **já** tinha o botão do painel e a sua mensagem de "não configurado";
  o que mudou foi de onde vem o endereço.
- O compose **já** montava uma tabela read-only por baixo do agente
  (`./runtimes.json:/etc/ikigai/runtimes.json:ro`, ADR-042 D2) — o mesmo
  molde, a mesma razão, um serviço acima.
- O deploy **já** trazia a imagem, compunha o stack e esperava pelo health —
  o gancho do aplicador entra depois do `compose up --wait`, que é a ordem
  certa: a rota aponta para um serviço.
- O `tailscale serve` **já** levava a rota do painel na caixa (8443 → 8003),
  dentro da tailnet, desde ADR-044.
- A caixa **já** tinha `jq 1.8.1` e `python3 3.14.4` — o aplicador não
  precisa de nada novo instalado.

Nada foi reescrito. Esta ADR **liga** o que já estava feito, e **tira do
mão** o que era aplicado à mão.

---

## 5. O que está quebrado, com evidência

### 5.1 O incidente: o Funnel sem `--https` tomou o 443

Medido na caixa, ao tentar publicar o painel:

```
$ sudo tailscale funnel --bg 10000
Without --https, the funnel assumes the **443** host and REPLACES that host's `/`.

antes:  vps-hetzner.tail78a4a0.ts.net:443 -> {"/":{"Proxy":"http://127.0.0.1:8000"}, …}
depois: vps-hetzner.tail78a4a0.ts.net:443 -> {"/":{"Proxy":"http://127.0.0.1:10000"}, …}

→ o api MCP deixou de responder pela rota (502)
→ `AllowFunnel` ficou ligado no 443
```

### 5.2 O incidente: o `funnel reset` apagou tudo

```
$ sudo tailscale funnel reset
→ o config TODO foi apagado: o 443, o 8443 e o 8444 de outra deployment
```

A reparação teve de ser feita a partir de uma **fotografia** das rotas, taken
antes, e reaplicada rota a rota:

```bash
sudo tailscale serve --bg --https=443 http://127.0.0.1:8000   # restaura o '/' e tira o flag do funnel
sudo tailscale serve --bg --https=8443 http://127.0.0.1:8003
sudo tailscale serve --bg --https=8444 http://127.0.0.1:3000
```

Estado final, verificado **byte a byte** contra a fotografia:

```
vps-hetzner.tail78a4a0.ts.net:443  ->  {"/":{"Proxy":"http://127.0.0.1:8000"},"/athena":{"Proxy":"http://127.0.0.1:27210"},"/harness":{"Proxy":"http://127.0.0.1:8002"},"/hefesto":{"Proxy":"http://127.0.0.1:27213"},"/telegram":{"Proxy":"http://127.0.0.1:27212"}}
vps-hetzner.tail78a4a0.ts.net:8443  ->  {"/":{"Proxy":"http://127.0.0.1:8003"}}
vps-hetzner.tail78a4a0.ts.net:8444  ->  {"/":{"Proxy":"http://127.0.0.1:3000"}}
```

`AllowFunnel` ausente. As superfícies respondem: painel `200`/`401`, api
`404`, harness `200`, 8444 `302`.

### 5.3 A semântica medida do `tailscale` (1.104.5)

| Comando | O que faz |
|---|---|
| `tailscale funnel --bg --https=<porta> --set-path=<path> <alvo>` | publica **esse** host e **esse** path |
| `tailscale serve --bg --https=<porta> --set-path=<path> <alvo>` | aplica a rota **e tira o flag do Funnel** desse host |
| `tailscale funnel --bg <porta>` (sem `--https`) | **PROIBIDO**: toma o 443 e substitui o `/` desse host |
| `tailscale funnel reset` | **PROIBIDO**: apaga o config todo |

`serve get-config` / `set-config` **não** aceitam a configuração web (erro:
*"must specify either --service=svc:<name> or --all"*) — a reparação só é
possível pela CLI `serve`/`funnel`.

### 5.4 O estado do Funnel: como se lê, e como se lê mal

A primeira leitura foi **errada**, e a errada é instructive.

```
SelfNode.CapMap["https://tailscale.com/cap/funnel-ports?ports=443,8443,10000"]  →  null
SelfNode.CapMap["funnel"]                                                        →  null
```

Esse `null` foi lido como «o Funnel não está concedido» — e é a leitura que o
ADR-044 também registou. **Não é disso que o `null` quer dizer.** Depois de
forçar um refresh do netmap (`tailscale debug force-netmap-update`, um no-op
que volta a pedir o mapa ao control plane) e depois de **publicar** a
superfície, o `null` **continua igual**. Um `null` no `CapMap` é a ausência de
uma *restrição* de portas — o link ao lado é o formulário de activação — e não
uma negação.

**A leitura que prova é o próprio CLI, e o mundo:**

```
$ tailscale funnel status
# Funnel on:
#     - https://vps-hetzner.tail78a4a0.ts.net:8443
```

E, quanto ao JSON, `AllowFunnel` é um **mapa** `host:port → true`, no topo —
não um booleano. Antes da publicação era `null` (nenhum host); agora é:

```
AllowFunnel = { "vps-hetzner.tail78a4a0.ts.net:8443": true }
```

O 443 **não** lá está, e é assim que tem de estar: nesse host vivem o api MCP,
o harness e três rotas de outra sessão.

**Corolário:** o sinal que prova a publicação é o **mundo a responder** — o
`GET /` a `200` num endereço público que não é da tailnet. Nenhum campo do
`serve status` substitui isso.

### 5.5 O que a superfície está a fazer hoje

Medido depois do PR #64 (`40cf3eb7`), 6 contentores `healthy` na imagem do
merge: `GET /` → `200`; `POST /api/session` sem credencial → `401`; a rota do
painel na tailnet (`https://vps-hetzner.tail78a4a0.ts.net:8443/`) → `200`.
Ou seja: a porta de dados está **fechada** e a página **responde** — o que
faltava era a rota pública.

### 5.6 A publicação, medida

O comando de publicação **foi executado** — pelo **aplicador do
reposititório**, com uma cópia da tabela em `state: published`, e não à mão:

```
IKIGAI_SURFACES_TABLE=/tmp/surfaces-published.json bash /tmp/apply-surfaces.sh
```

```
Available on the internet:

https://vps-hetzner.tail78a4a0.ts.net:8443/
|-- proxy http://127.0.0.1:8003

Funnel started and running in the background.

=== what changed in the box's routes ===
  the handlers are identical (only the publication flag can have moved)

=== the other surfaces are untouched? ===
  OK: the other surfaces' handlers are exactly as they were

codigo de saida: 0
```

O diff das rotas, **antes e depois**, é **vazio** — as sete linhas (o 443 com
os cinco paths, o 8443 e o 8444) são as mesmas. O 443 continua *tailnet only*.

E a prova de fora da tailnet, forçando os **A públicos** do hostname (o caminho
que o runner do GitHub faz, e que não passa pela tailnet):

```
vps-hetzner.tail78a4a0.ts.net → A 185.40.234.55 / .75 / .198
                                AAAA 2a00:dd80:20::55 / ::873 / ::a8e

[185.40.234.55]   GET / → 200    POST /api/session → 401
[185.40.234.75]   GET / → 200    POST /api/session → 401
[185.40.234.198]  GET / → 200    POST /api/session → 401
[2a00:dd80:20::55]   GET / → 200    POST /api/session → 401
```

A página **responde** e a porta de dados está **fechada**, do lado de fora.

**E o certificado é de confiança pública.** Medido na caixa, com o store de CAs
do sistema (sem nenhuma CA do Tailscale instalada):

```
subject = CN=vps-hetzner.tail78a4a0.ts.net
issuer  = C=US, O=Let's Encrypt, CN=YE1
notBefore = Nov  9 03:16:25 2026 GMT    notAfter = Feb  7 03:24:24 2027 GMT
SAN     = DNS:vps-hetzner.tail78a4a0.ts.net

Verify return code: 0 (ok)
Protocol: TLSv1.3    Cipher: TLS_AES_128_GCM_SHA256
```

Isto não é um detalhe: o painel abre-se dentro do **WebView do Telegram**, e
um WebView recusa um certificado que não chains até uma CA pública. Um painel
publicado com um certificado auto-assinado abriria no `curl` da caixa e **não**
abriria no telemóvel do dono.

### 5.7 O primeiro gate de efeito falhou — e a falha não era do que ele mede

O primeiro deploy com `state: published` deixou o gate **vermelho**, com o
runner a sair com o **código 35** do `curl` (erro de ligação TLS). Duas
coisas estavam erradas ao mesmo tempo:

- **O gate não sabia o que tinha encontrado.** Com `curl -s -o /dev/null -w
  '%{http_code}'`, o código HTTP vai para o stdout e o erro do TLS para o
  stderr — e o gate lia o stdout. Um `200` que não chegou e uma superfície que
  não está publicada davam o **mesmo** código de saída, e a mensagem dizia
  «a superfície não está publicada». Mandava o dono procurar um problema que
  não existia.
- **A falha era transitória.** A borda do Funnel é um **ingress público
  partilhado**: o runner recebeu um endereço que não respondeu naquele
  momento. Na corrida seguinte, com o mesmo código, o mesmo runner resolveu os
  seis endereços públicos e respondeu à primeira:

```
resolving vps-hetzner.tail78a4a0.ts.net from the runner (outside the tailnet):
  185.40.234.198   185.40.234.55   185.40.234.75
  2a00:dd80:20::55  2a00:dd80:20::873  2a00:dd80:20::a8e
attempt 1:
  GET / -> http='200' curl_exit=0
  POST /api/session -> http='401' curl_exit=0
the surface answers 200 and its data door answers 401: published, and closed
```

Por isso o gate passou a **tentar três vezes**, com espera a crescer, e a
**distinguir as duas falhas**: o `curl exit` é reportado à parte do código
HTTP, e a mensagem de erro diz «a superfície pode estar publicada, mas o
runner não a alcança» quando o problema é de transporte.

O gate responde sobre a **superfície**, não sobre a sorte de uma borda.

---

## 6. Inventário, com a razão de cada peça

| Peça | Razão |
|---|---|
| `deploy/surfaces.json` | a tabela das superfícies, versionada. `host`, `https_port`, `path`, `target`, `mode`, `auth` e **`state`** — a palavra que decide se a rota é publicada. |
| `src/bot/surfaces.py` | o leitor único. `load_surfaces()`, `surface()` (recusa `auth`, `state`, `mode`, `host` e `port` desconhecidos) e `surface_url()`. Falha fechada: uma tabela ausente ou ilegível produz **nenhuma** Morada, e o bot fica exactamente como estava antes de o painel existir. |
| `surface_url()` devolve o **mesmo** endereço nos dois estados | o Funnel não move o painel — remove-lhe a restrição "só tailnet". Um endereço que mudasse com o estado obrigaria o dono a reabrir o painel à mão depois do flip. |
| o mount `./surfaces.json:/etc/ikigai/surfaces.json:ro` | relativo ao **directório do compose** (`deploy/`), como `./runtimes.json` em ADR-042. Read-only porque a tabela é do repositório e a caixa não escreve nela. |
| `IKIGAI_SURFACES_FILE: ${IKIGAI_SURFACES_FILE:-/etc/ikigai/surfaces.json}` | o default é o caminho do mount, e a variável continua a poder apontar para outro sítio — o que muda é o **default**, não a capacidade. |
| `_miniapp_url()` no bot | a **tabela** é a verdade; o `IKIGAI_MINIAPP_URL` é o **fallback**, para um checkout sem o mount. Uma caixa com o endereço no `.env` tem duas verdades, e a segunda é a que ninguém revê. |
| `deploy/apply-surfaces.sh` | quem aplica. Lê a tabela com `jq`, fotografa antes/depois, e por cada superfície faz `funnel` (published) ou `serve` (pending) — **sempre** com `--https` e `--set-path`. Um `state` desconhecido é **recusado**, não publicado. Todo o `sudo` é `-n`: o deploy corre num ssh sem terminal, e um comando à espera de uma password é um comando que pendura o deploy. |
| a guarda "nenhum handler de outra superfície mudou" | o 443 desta caixa é partilhado. A comparação antes/depois é o que apanha um comando que mexeu onde não devia, e a restauração a partir da fotografia é o que desfaz. |
| `tests/test_published_surface.py` (35 guards) | o contrato, perguntado ao **consumidor** (o loader do bot) e não a uma segunda implementação das regras. Cobre: a tabela e o deployment de acordo; o consumidor a recusar o que não implementa; o 443 **nunca** declarado; o alvo a apontar para a porta que o compose serve; o aplicador **sem** `funnel reset`, **com** `--https` e `--set-path` **sempre**, **sem** porta nem host escritos à mão; o CI a ter job próprio; o gate de efeito a correr fora da tailnet e a perguntar **só** quando o estado é `published`. |
| o job de contrato no `ci.yml` | a superfície deixa de ser a única porta publicada sem gate. O job corre `pytest tests/test_published_surface.py` — os guards vivem na suite canónica, no ambiente que corre o resto. |
| o job de efeito no `deploy.yml` | o **único** sítio sem corrida com o deploy e com um runner **fora** da tailnet. Uma sondagem de dentro da tailnet responderia mesmo com o Funnel desligado, e não provaria nada sobre publicação. |

---

## 7. Dia zero

```bash
# a tabela entra no repositório, e o compose passa a montá-la
git add deploy/surfaces.json deploy/apply-surfaces.sh deploy/compose.yml
git add src/bot/surfaces.py src/ikigai/tests/test_published_surface.py
git add .github/workflows/ci.yml .github/workflows/deploy.yml

# os guards, local
cd src/ikigai && poetry run pytest tests/test_published_surface.py -q     # 35 verdes
poetry run ruff check src/ && poetry run ruff format --check src/
poetry run mypy -p src.ikigai.src
```

O **flip** para `published` é uma palavra na tabela:

```diff
-      "state": "pending"
+      "state": "published"
```

E **é o deploy que publica** — não uma mão no `tailscale`:

```bash
# na caixa, o que o deploy corre (e o que mediu a publicação, §5.6):
bash apply-surfaces.sh          #  →  tailscale funnel --bg --https=8443 --set-path=/ http://127.0.0.1:8003
```

---

## 8. Evolução

| Ordem | O quê | Porquê agora |
|---|---|---|
| 1 | **o botão do menu do bot** | ADR-044 §5.4: o botão de menu (`setChatMenuButton` com `web_app`) é o que a UIA expõe e o que abre o Mini App. Tê-lo de pé em produção é uma linha — e é o que torna o painel alcançável a partir de um telemóvel, agora que a rota é pública. |
| 2 | **uma segunda superfície** | a tabela já é uma tabela: acrescentar `athena` ou `hefesto` é uma entrada, com a sua porta de dados e o seu estado. O aplicador e os guards não mudam. |
| 3 | **a tabela por ambiente** | hoje a tabela é uma coisa do repositório. Quando houver um segundo deployment, o `IKIGAI_SURFACES_FILE` aponta para outro sítio — já é possível sem mudar código. |
| 4 | **o client's address no `.env`** | hoje o `.env` tem o `IKIGAI_MINIAPP_URL` como fallback. Quando o fallback deixar de ser preciso, sai — para não haver duas verdades a sobreviverem lado a lado. |
| 5 | **a superfície, sem o dono por perto** | o Funnel é um_proxy público_: qualquer um na internet pode bater à porta. A porta de dados está fechada pela assinatura do Telegram, mas a *página* é pública — e isso é uma decisão de produto que ainda não foi escrita. |

---

## 9. Passos com PASS falsificável

| # | Passo | PASS | Como se falsifica |
|---|---|---|---|
| 1 | A tabela é a verdade | `tests/test_published_surface.py` verde | mudar o `target` da tabela para uma porta que o compose não serve e ver o teste falhar |
| 2 | O consumidor falha fechado | o mesmo teste: `auth`, `state`, `mode`, `host` e `port` desconhecidos dão **nenhuma** Morada | pôr `"auth": "none"` na tabela e ver o URL ficar vazio |
| 3 | O 443 nunca é declarado | o mesmo teste: nenhuma superfície declara o 443 | pôr `"https_port": 443` e ver o teste falhar |
| 4 | O aplicador não faz `funnel reset` | o mesmo teste: a proibição está no código do aplicador | pôr `funnel reset` no script e ver o teste falhar |
| 5 | O aplicador nomeia host e path | o mesmo teste: todos os comandos têm `--https=` e `--set-path=` | tirar o `--https` de um comando e ver o teste falhar |
| 6 | A superfície tem job próprio | o job *The published surface (gate próprio)* corre em cada PR | abrir um PR que quebre um guard e ver o job vermelho |
| 7 | O deploy aplica a rota | o `deploy.yml` chama `apply-surfaces.sh` **depois** do `compose up --wait` | mover a chamada para antes e ver o teste falhar |
| 8 | A rota pública existe | `GET /` → `200` **de fora** da tailnet | com o Funnel desligado, ver a sondagem falhar (ou nem sair) |
| 9 | A porta de dados está fechada | `POST /api/session` sem credencial → `401` | publicar uma superfície com a porta aberta e ver o gate falhar |
| 10 | O dono é quem decide | o gate de efeito só pergunta quando a tabela diz `published` | com `state: pending`, o gate não pergunta — e isso **não** é uma falha |
| 11 | As outras superfícies ficam intactas | o diff das rotas antes/depois do aplicador é **vazio** (medido: sete linhas antes, as mesmas sete depois) | declarar uma superfície no 443 e ver o diff da rota de outra sessão |
| 12 | O Funnel fica só onde foi declarado | `AllowFunnel` (um **mapa** `host:port → true`) só tem o 8443 | publicar o 443 e ver o `AllowFunnel` ganhar o 443 |

---

## 10. Fora de escopo

| Coisa | Porque fica de fora | O que a reabre |
|---|---|---|
| **Conceder o Funnel na tailnet** | é uma capacidade da tailnet, decidida no admin da Tailscale. O pipeline não concede o que a tailnet permite — nem deve. | o dono, no admin. |
| **Publicar o 443** | nesse host vivem o api MCP, o harness e três rotas de outra sessão. Publicar de lá publica todas. | um deploy em que o 443 passe a ser só nosso — o que não está previsto. |
| **Um CDN à frente** | o Funnel já dá HTTPS e o `initData` tem de chegar ao backend sem ser reescrito. | a latência ou o custo justificarem. |
| **Um proxy próprio** | o `tailscale serve` já é o proxy, com o certificado do MagicDNS. | a latência ou o custo o justificarem. |
| **O `initData` mais durável que 24 h** | é do Telegram (ADR-044 §3.4). | o Telegram mudar o prazo — não nós. |
| **Um segundo cliente (web, TUI)** | ADR-037 D2: a mesma tabela, outra projecção. Não entra aqui porque o cliente novo nasce do outro lado da rota. | a decisão de construir o cliente. |
| **Gerar o `initData` fora do Telegram** | a assinatura é do Telegram; um `initData` fabricado é uma falsificação, não uma sessão. | nunca. |

---

## 11. Decisões com default

| # | Decisão | Default | O que a muda |
|---|---|---|---|
| D1 | Onde a rota vive | `deploy/surfaces.json`, versionada | um segundo deployment, que precisa da sua |
| D2 | O caminho da tabela no contentor | `/etc/ikigai/surfaces.json` | `IKIGAI_SURFACES_FILE` |
| D3 | O estado de uma superfície | `pending` — **publicado ≠ decidido**; hoje o `miniapp` está em `published` | a tabela (`"state"`), e só o dono |
| D4 | O URL do painel | o mesmo nos dois estados: `https://host:8443/` | nada: o Funnel não move o painel |
| D5 | Se a tabela é recusada | o consumidor recusa e **não dá Morada nenhuma**; o chat continua, o botão não é enviado | nada: o fail-closed é o invariante |
| D6 | Se o ambiente ainda conta | sim, como **fallback** — a tabela primeiro | o dono, quando o fallback deixar de ser preciso |
| D7 | O que o aplicador pode tocar | só o `host:port` e o path declarados | nada: é o que a medição obriga |
| D8 | Se o gate pergunta quando o estado é `pending` | não — uma superfície declarada e não publicada é uma decisão em falta, não uma falha | o estado na tabela |
| D9 | Onde vive o gate do efeito | no `deploy.yml`, depois do deploy, num runner fora da tailnet | nada: é o único sítio sem corrida |

---

## 12. Camadas de falha

Cada uma falha sozinha, e nenhuma leva as outras:

| Camada | Se falhar | O que se vê |
|---|---|---|
| a tabela | não existe, ou não é JSON | o consumidor não dá Morada nenhuma; o bot não envia o botão do painel; o chat continua |
| uma superfície | declara um `auth`, `state`, `mode`, `host` ou `port` que o código não implementa | recusada, sem Morada — a superfície não aparece |
| o mount | o compose aponta para um ficheiro em falta | o docker cria um **directório**; o bot lê uma tabela vazia e parece saudável |
| o botão do painel | o endereço não vem de lado nenhum | a mensagem «O painel não está configurado neste bot» — e o chat nunca para |
| o aplicador | a tabela não está lá, ou o `jq` não existe | o deploy **falha** (código 1), em vez de publicar sem saber o que publica |
| o aplicador | o `tailscale` recusa o comando | o deploy falha, e a rota fica como estava |
| o aplicador | um comando mexeu num handler de outra superfície | a guarda apanha a diferença e **restaura** a partir da fotografia; o deploy falha na mesma |
| o Funnel | a tailnet não tem a capacidade, ou o CLI recusa | o `funnel` falha; o deploy fica **vermelho** e a rota continua como estava — dentro da tailnet, que é o estado correcto enquanto o dono não a publica |
| o Funnel | o comando corre, mas a página não responde de fora | o gate de efeito apanha: `GET /` não é `200` num endereço público — o deploy fica **vermelho** |
| o gate do contrato | o job do CI não corre | a superfície fica sem porta — e é a razão de o job existir |
| o gate do efeito | a superfície publicada não responde de fora | o deploy fica **vermelho**: a rota está declarada e não está no ar |
| o gate do efeito | a porta de dados responde `200` | o deploy fica **vermelho**: uma superfície publicada com a porta aberta é pior do que nenhuma |
| o gate do efeito | o runner não consegue abrir a socket | o gate **distingue** as duas coisas: o `curl exit` é reportado à parte do código HTTP, e a mensagem diz «a superfície pode estar publicada, mas o runner não a alcança» — em vez de dizer «não está publicada», que seria mentira |

---

## 13. Referências

- [ADR-044](./ADR-044-mini-app-panel.md) — o painel, a identidade do Telegram e a prova medida do caminho (§5.1, §5.2, §5.4)
- [ADR-042](./ADR-042-routing-table-in-the-repository.md) — D2: a tabela no contentor, montada read-only; e o precedente do gate próprio
- [ADR-041](./ADR-041-runtime-routing-and-human-in-the-loop.md) — o runtime routing e o HITL
- [ADR-037](./ADR-037-data-layer-canonical-turn.md) — D2 (uma DOM, N projecções), D8 (o Telegram é uma projecção)
- `deploy/surfaces.json` — a tabela das superfícies publicadas
- `src/bot/surfaces.py` — o leitor fail-closed
- `deploy/apply-surfaces.sh` — o aplicador, e as formas que estão proibidas
- `src/ikigai/tests/test_published_surface.py` — os 35 guards da superfície
- `.github/workflows/ci.yml` — o job *The published surface (gate próprio)*
- `.github/workflows/deploy.yml` — o job *The published surface (live, outside the tailnet)*
- `specs/miniapp/TECH.md` — §8 (a rota, e onde ela vive)
- `src/ikigai/tests/test_deployment_surface.py` — o padrão dos guards de deployment
