# Mini App — the owner's panel, inside the Telegram

**Status:** published contract. The decision behind it is
[`ADR-044`](../../code-docs/adr/ADR-044-mini-app-panel.md); this document is
the *shape* of the thing, so that a cold agent can build against it without
reading the ADR.

**What it is:** a Telegram Web App that the bot serves, which shows the
owner's session — what the agent is doing, what it is waiting on, what it
did, what the store holds — and answers a question from the same buttons the
chat has.

**What it is not:** a second client with its own door to the store. It reads
through the doors that already exist and writes through none of them.

---

## 1. Reading order for a cold agent

1. This document — the three routes and the shape of the answers.
2. `src/bot/miniapp/__init__.py` — the implementation, ~250 lines, and the
   comments in it say *why*.
3. `src/bot/miniapp/index.html` — the page. It ships inside the image; the
   panel is never a deployment that depends on a file somebody forgot to
   upload.
4. `ADR-044` — the decision, the evidence, and what is deliberately out of
   scope.

---

## 2. The contract

The Mini App is an HTTP surface **inside the bot's process**, on its own
port (`IKIGAI_MINIAPP_PORT`; `0` means the panel is not served at all, and
the bot is exactly the bot it was before). The public address is a **URL**,
not a port, because Telegram will only open an HTTPS address — and it lives
in the repository, in the table of the published surfaces (§8):
`deploy/surfaces.json`, mounted read-only at `/etc/ikigai/surfaces.json`.
`IKIGAI_MINIAPP_URL` is the **fallback**, for a checkout without the mount.

### `GET /` — the page

The whole panel, as one HTML document. **No credential required**: the page
is public, and what it *reads* is not. A cold client that opens it without
Telegram's payload gets the page and nothing else.

### `POST /api/session` — the view

```jsonc
// request
{ "init_data": "query_id=…&user=%7B…%7D&auth_date=…&hash=…" }

// 200
{
  "ok": true,
  "session": { "id": "tg-2115322359", "client": "tg:2115322359",
               "runtime": { "id": "owner", "label": "Owner", "model": "MiniMax-M2.7" } },
  "questions": [ /* the agent's pending questions */ ],
  "events":    [ /* the log of what the agent did */ ],
  "artifacts": [ { "uid": "…", "kind": "…", "title": "…" } ]
}

// 401
{ "ok": false, "error": "the initData carries no hash" }
```

`artifacts` is the only part that may legitimately be empty while the panel
works: the store being unreachable must not empty the panel, because the
agent's side is still worth showing.

### `POST /api/answer` — the answer

```jsonc
// request — one or the other
{ "init_data": "…", "question_id": "…", "option_index": 0 }
{ "init_data": "…", "question_id": "…", "value": "…" }

// 200
{ "ok": true, "question": { /* the question, now answered */ } }
```

The answer goes to the **agent**, through the harness — the same door the
chat's buttons use. The panel is a second way to press a button, not a second
way to change anything.

---

## 3. The credential: how Telegram's signature becomes an identity

Telegram opens a Mini App with the payload in the **fragment** of the URL
(`#tgWebAppData=…&tgWebAppVersion=…`) and the official SDK parses it into
`Telegram.WebApp.initData`. The page therefore:

1. reads `Telegram.WebApp.initData` **first** (the SDK is the parser);
2. falls back to parsing the fragment itself.

The server validates the payload with Telegram's own method: the secret key
is `HMAC_SHA256(bot_token, "WebAppData")`, the data-check string is every
received field sorted by name and joined with newlines, and the check is its
HMAC-SHA256. The `hash` field is excluded (it *is* the check) and so is
`signature`; **both readings are accepted** — with and without `signature` —
because a check that rejects a payload Telegram actually sent is a bot that
cannot open its own panel. Accepting both is not a hole: the `hash` can only
be produced with the bot's token, so every accepted payload was signed by
this bot either way.

A freshness window of **24 h** is enforced on top. Telegram's signature does
not expire on its own — a captured one would be valid forever.

The routing key is `tg:<user_id>`, where `user_id` is the id inside the
`user` field of the payload (Telegram sends it as a JSON string). It is the
**same key the chat uses**, because it is the same person. The client is
*routed*; it never chooses its runtime (ADR-041).

---

## 4. Rules that hold in every client

| # | Rule | Where it lives |
|---|---|---|
| 1 | The bot validates; the agent is asked for data | `src/bot/miniapp/__init__.py` |
| 2 | The page never talks to the store — only through the MCP and the harness | the same |
| 3 | An account that is not in the allowlist learns nothing (401, always) | the same |
| 4 | A stale payload is refused (401), even though the signature is valid | the same |
| 5 | The panel adds no capability the chat does not have | ADR-044 §4 |
| 6 | The panel never writes to the store | ADR-037 D5/D8 |
| 7 | The client is routed, never self-serving | ADR-041, `deploy/runtimes.json` |
| 8 | The page ships inside the image | `src/bot/miniapp/index.html` |
| 9 | The panel has a gate in CI: the `src-bot` job, on the image's Node 24 | `.github/workflows/ci.yml` |

---

## 5. Failures you will actually hit

| Failure | What the server says | What the owner sees |
|---|---|---|
| No payload, or no `hash` | 401 `the initData carries no hash` | the panel says it is not authenticated |
| A payload from another bot | 401 `the initData does not match this bot` | the same; the refusal is logged |
| A payload older than 24 h | 401 `the initData is older than the window this bot accepts` | the panel asks to be reopened |
| An account outside the allowlist | 401 `this account is not allowed here` | nothing of what exists is shown |
| The agent is down | 500 from `/api/session` | the panel shows the error, not an empty page |
| The store is down | `artifacts` empty, the rest shown | the session stays visible |
| The proxy in front of the bot is down | the page does not open | the button opens a network error — **and the chat keeps working** |
| The table of the published surfaces missing, or declaring a surface the code does not implement | no button is sent; `/painel` says the panel is not configured | the chat behaves exactly as before |

---

## 6. How the proof is read

**The server is the verdict; the screen is not.** The owner's display is
unstable — a window can be suspended, a client can be behind another one —
so a proof read off a screenshot proves nothing about the path.

The proof of this surface is:

- `POST /api/session` with a **200** and `session.id` = the owner's client;
- a User-Agent that is a **browser**, not `curl` — the calibration requests
  made by the harness itself are known and are excluded;
- and, for the proof that matters, a payload **Telegram delivered**, not one
  the harness signed itself. That last distinction is the whole point: a
  self-signed payload proves the code, not the path.

The observer is a `tcpdump` on the panel's port (both directions, headers
and body), because the bot has no access log of its own. It is calibrated
before it is trusted: one request without a credential (must be 401) and one
with a payload signed by the bot on the box (must be 200 with the session).

### 6.1 The measured result

The proof passed on 2026-11-10 at 13:53, from **Telegram Desktop** — a client
Telegram, delivering Telegram's own payload. The observer counted:

```
POST /api/session  2 -> 4
GET  /             16 -> 18
HTTP/1.1 200       16 -> 20
HTTP/1.1 401        2 -> 2      (the calibration 401s, unchanged)
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) … Chrome/157.0.0.0 … Edg/157.0.0.0
```

and the 200 body carried `"session":{"id":"tg-2115322359"`. The panel itself,
rendered inside Telegram's WebView, showed `SESSÃO tg-2115322359`,
`CLIENTE tg:2115322359`, runtime `owner`, and artifacts.

**How it was opened, and the limit of automation.** The inline button of a
message is **not** an automation element: Telegram exposes the message as a
`ListItem` and the button is nothing at all. A bot-menu button set to
`web_app` **is** an element (`HistoryView::BotMenuButton`), so it can be
invoked — which is how the proof was driven without a human touch. This is a
property of the client, not of the panel: on a phone it is one tap.

On this machine, injected **keyboard** works (`keybd_event`, `SendKeys`) while
injected **mouse** does not (`mouse_event`, `SendInput` with
`MOUSEEVENTF_ABSOLUTE`, and `PostMessage` of mouse messages are all ignored by
a Qt window) — measured against a control window, not assumed.

---

## 7. What is not published

- **A terminal client for the same panel.** Another product; the runtime
  table already has a read-only runtime waiting for it.
- **A way to write to the store from the panel.** Never.

---

## 8. The route, and where it lives

**The route is a file in the repository.** `deploy/surfaces.json` is the table
of the published surfaces — where each one is, how it is reached, and whether
it is published:

```json
{
  "surfaces": {
    "miniapp": {
      "host": "vps-hetzner.tail78a4a0.ts.net",
      "https_port": 8443,
      "path": "/",
      "target": "http://127.0.0.1:8003",
      "mode": "funnel",
      "auth": "telegram-initdata",
      "state": "pending"
    }
  }
}
```

It is mounted **read-only** in the bot (`./surfaces.json:/etc/ikigai/surfaces.json:ro`),
and `src/bot/surfaces.py` is the only thing that reads it. The environment is
the **fallback**, not the truth: an address that lives in the box's `.env` is
a second truth, and a second truth is edited by hand and never reviewed.

**The consumer fails closed.** A table that is missing, malformed, or that
declares a surface whose credential model, state, mode, host or port the code
does not implement, produces **no address at all**: the bot then behaves
exactly as it did before the panel existed — the chat keeps working, and the
panel button is simply not sent.

**`published` is not `decided`.** The state is a word in the table, and only
the owner writes it. `pending` means *declared, reachable inside the tailnet*;
`published` means *on the internet*. The **address is the same in both** — the
funnel does not move the panel, it removes the tailnet-only restriction from
it — so the button in the Telegram keeps working across the flip.

**The 443 is not publishable.** On this host, 443 carries the MCP api, the
agent's harness and three routes of another project. The panel has a host of
its own (8443), and a surface published from the shared one publishes all of
them.

**How the route is applied.** `deploy/apply-surfaces.sh`, run by the deploy
after the services are up. It is deliberately narrow: it touches **only** the
`host:port` and the path the table declares, it always passes `--https` **and**
`--set-path`, and it **never** runs `tailscale funnel reset` — measured on this
box, a funnel without `--https` takes the 443 host and replaces that host's
`/`, and a reset wipes the whole serve config, taking the other deployment's
routes with it. The script photographs the config before and after, compares
every other surface's handler, and restores what moved.

**The gate.** Two doors, measuring different things:

- the **contract** — `.github/workflows/ci.yml`, job *The published surface
  (gate próprio)* — runs `tests/test_published_surface.py`: the table against
  the deployment, the consumer against what it does not implement, and the
  applier against the shapes that were measured to be dangerous;
- the **effect** — `.github/workflows/deploy.yml`, job *The published surface
  (live, outside the tailnet)* — asks, from a runner that is **not** in the
  tailnet, whether the published surface answers `200` and whether its data
  door answers `401`. A probe from inside the tailnet would answer even with
  the funnel off, and would prove nothing about publication.

The effect gate only asks when the table says `published`. A surface that is
declared and not published is a decision that has not been taken yet — not a
failure.

**The decision behind it** is
[`ADR-045`](../../code-docs/adr/ADR-045-public-route-and-its-gate.md).
