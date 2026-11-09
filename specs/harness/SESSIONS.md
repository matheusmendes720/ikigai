# Sessions — the runtime, the routing, the question, and the panel

**Status:** specification (2026-11-09)
**Anchor:** [ADR-037](../../code-docs/adr/ADR-037-data-layer-canonical-turn.md) · [ADR-039](../../code-docs/adr/ADR-039-websocket-sync-transport.md) · [ADR-040](../../code-docs/adr/ADR-040-client-state-and-drafts.md) · [ADR-041](../../code-docs/adr/ADR-041-runtime-routing-and-human-in-the-loop.md)
**Companion:** [router.md](./router.md) · [CHAINED-ROUTINES.md](./CHAINED-ROUTINES.md) · [SKILL-SPECS.md](./SKILL-SPECS.md)

This document specifies the seam between a **client** (a Telegram chat, a TUI, a
panel) and the **runtime** that answers it: how a client is routed to a
runtime, how a conversation is held, how the agent asks the owner a question
and waits for the answer, and what the client sees while it waits.

It is the companion of `CHAINED-ROUTINES.md`: that document specifies the
chain *inside* a routine (router → session → routine → synthesis → HITL), and
this one specifies the seam — the routing, the blocking question and the
surfaces.

---

## 0. Verdict

| Piece | Where | What it is |
|---|---|---|
| the runtime registry | `deploy/harness/runtimes.mjs` | named profiles: provider, model, routines, memory |
| the routing table | the same file | client key → runtime id, fail-closed with a reason |
| the session | `deploy/harness/server.mjs` | one conversation, one `pi` process, one SQLite row |
| the agent's log | `deploy/harness/memory.mjs` | an append-only event log with a cursor |
| the question | `deploy/harness/owner.mjs` | a pending question, durable, with a deadline |
| the `ask` tool | `deploy/harness/owner-mcp.mjs` | the agent's door to the owner; the call BLOCKS |
| the channel | `src/bot/channel.py` | a question drawn as buttons, four ways |
| the panel | `src/bot/miniapp/` | the session in a page, authenticated by `initData` |

**Nothing here belongs in `src/` except the two client pieces.** ADR-037 D7:
the agent is external. The chain lives in `deploy/harness/`, beside
`server.mjs`, and reaches the store through the same six MCP tools the bot
uses. A file under `src/` that imports it is a drift.

---

## 1. The runtime

A **runtime** is a named profile of the agent:

```json
{
  "id": "owner",
  "label": "Owner",
  "provider": "harness",
  "model": "MiniMax-M2.7",
  "fallbackProvider": "deepseek",
  "fallbackModel": "deepseek-flash",
  "routines": ["daily-note", "weekly-review", "monthly-review", "quarterly-plan"],
  "memory": "owner"
}
```

| Field | Meaning | Default |
|---|---|---|
| `provider` | the provider the container knows | the container's own |
| `model` | the model on that provider | the container's own |
| `routines` | the routines this runtime may run; **omitted means all of them** | all |
| `memory` | the memory scope | the runtime's id |

The configuration is read from `HARNESS_RUNTIMES_FILE` (a JSON file — the
readable form) or `HARNESS_RUNTIMES` (the same JSON inline). With neither,
there is exactly one runtime, built from the container's own provider
settings: **the behaviour that existed before this file**.

### 1.1 The routing table

```json
{
  "default": "owner",
  "runtimes": { "owner": { "provider": "harness" } },
  "clients": { "tg:9138296750": "owner", "tg:999": "archive" }
}
```

The **client key** is the harness's own vocabulary: `tg:<chat_id>` today, and
whatever a TUI or a panel says tomorrow. It is matched exactly; a key that is
not in the table gets the default runtime, never a near miss.

### 1.2 Failing closed

| Configuration | What happens | Why |
|---|---|---|
| a runtime names a provider the container does not have | the runtime is **refused**, with the reason | a report quietly produced by the wrong model is worse than a refusal |
| a client is routed to a runtime that does not exist | the route is **refused**, with the reason | the same |
| a runtime id is not a slug (`a-z`, `0-9`, `_`, `-`) | the runtime is **refused** | the id becomes a session key and a file name |
| the default runtime does not exist | the default is kept, and the problem is reported | a typo in the default must not take the routing down |

`GET /v1/runtimes` reports the refusals. A routing table that refuses
something quietly is a routing table the operator cannot fix.

---

## 2. The session

A session is a **conversation**: one `pi` process, one context window, one
compaction history. Two chats are two conversations and cannot share one.

| Key | Lives in | Why |
|---|---|---|
| the session id | the harness | it is the agent's `--session-id`, and the agent's rules for ids are the harness's business |
| the runtime | the session row | it is the machine that holds the conversation |
| the questions | the harness's SQLite | the agent is suspended on them |
| the prose in progress | the store (`ikig.drafts`, ADR-040) | prose outlives the process |
| the cursor | the client | the feed's `since` |

The session id is the **sanitised** client key: `tg:9138296750` becomes
`tg-9138296750`. The client may send either spelling — the harness
sanitises on the way in, and the two are the same conversation.

**Re-routing changes the machine, not the conversation.** A client moved to
another runtime keeps its session id: the old `pi` is released and a new one
is spawned with the new runtime's model, and the conversation continues.

### 2.1 The routes

| Route | What it answers |
|---|---|
| `GET /v1/runtimes` | the registry, the default, and the refusals |
| `GET /v1/routing?client=<key>` | which runtime answers this client, and **whether that was a rule or the default** |
| `GET /v1/session?client=<key>` | the session id, the runtime, and the questions still open |
| `GET /v1/events?session=<key>&since=<n>` | the agent's log, forward, from a cursor |
| `POST /v1/routine` | run a routine; the body may carry `client` for the routing |
| `POST /v1/owner/ask` | register a question (the agent's tool calls it) |
| `GET /v1/owner/answer?question_id=<id>` | the state of a question: `pending`, `answered`, `expired` |
| `POST /v1/owner/answer` | the owner's answer |

### 2.2 The feed

`GET /v1/events` answers two questions with one page, the same way the
store's change feed does (ADR-039): *what is new* and *what did I already
have*. The response carries `events` (in order), `tip` (the highest
sequence) and `floor` (the lowest one still in the log).

An empty page is not one thing: it is "you are up to date" or "the log was
pruned under you". The client reads `floor` to tell them apart.

The event kinds the client renders:

| Kind | What it means |
|---|---|
| `routine.started` | a routine began, under a runtime |
| `routine.finished` | the report is ready |
| `routine.failed` | the run died, with the reason |
| `question.asked` | the agent is waiting for the owner |
| `question.answered` | the owner answered |
| `question.expired` | nobody answered in time |

---

## 3. The question

### 3.1 The tool

The agent's surface has exactly **one** tool of its own:

```json
{
  "name": "ask",
  "inputSchema": {
    "type": "object",
    "properties": {
      "question": { "type": "string" },
      "kind": { "type": "string", "enum": ["choice", "confirm", "text", "editor"] },
      "options": { "type": "array", "items": { "type": "string" } },
      "timeout_ms": { "type": "integer" }
    },
    "required": ["question"]
  }
}
```

The call **blocks**. The answer comes back as the tool's result. A question
that nobody answers comes back as an **error** that says so, and the agent is
told to continue with its own reading.

The tool is an MCP server of the **agent's** surface, registered in
`.pi/mcp.json` next to the store's six tools. It is not a seventh tool on
the api: the api's surface is exactly six, and asking the owner is not a
store operation.

### 3.2 The four kinds

| Kind | The owner | The channel draws |
|---|---|---|
| `choice` | picks one of `options` | one button per option |
| `confirm` | yes or no | two buttons |
| `text` | writes a line | one button that arms the chat; the next message is the answer |
| `editor` | writes several lines | the same, with a multi-line field |

### 3.3 The lifecycle

```
ask ──► registered (pending) ──► answered | expired
              │                        │
              └── the agent is suspended on it
```

| Rule | Why |
|---|---|
| the question is durable (SQLite) | a restart of the bot, the phone or the harness must not lose it |
| the deadline belongs to the question | the transport's timeout is longer than the deadline, so the question always expires first, with a clean answer |
| answering twice is refused | the first answer moved the agent on |
| an answer that was not offered is refused | the option's text is the runtime's |
| the option travels as an **index** | a channel's button payload is capped at 64 bytes, and it fails silently past it |

---

## 4. The channel

The channel renders a question and carries the answer back. It decides
nothing.

| The question | The button | What travels |
|---|---|---|
| `choice`, `confirm` | one per option | the question id and the option's **index** |
| `text`, `editor` | one that arms the chat | the question id; the answer arrives as a message |

The payload is versioned (`v1:<verb>:<argument>`): a button outlives the bot
that sent it, and a payload without a version is a payload the new process
has to guess the shape of.

The **client** is a projection (ADR-037 D8): the agent writes through the
api's six tools, and the channel writes nothing to the DOM.

---

## 5. The panel

A Telegram Web App is a page that opens **inside** the chat, and it arrives
authenticated: `initData` carries a signature the server checks.

### 5.1 The validation

```
secret_key = HMAC_SHA256(bot_token, "WebAppData")
check      = every received field, sorted, joined with "\n"   (hash and signature excluded)
expected   = HMAC_SHA256(check, secret_key)
```

The check accepts the reading **with** and **without** the `signature` field,
because Telegram's documentation describes both, and a check that rejects a
payload Telegram actually sent is a bot that cannot open its own panel. Both
readings require the token, so neither is a hole.

The **freshness window** is ours and it is not optional: without it the
signature is a bearer token with no expiry. A day is the default.

### 5.2 Who serves it

The **bot**. The validation key is derived from the bot token, and the bot is
the only component that holds it — a harness that held the token could speak
as the owner. The bot validates, asks the harness for the data, and serves
the page.

The public origin is a deployment decision: an HTTPS address with a
certificate the phone trusts. The current one is the tailnet name, whose
certificate Tailscale issues.

### 5.3 The routes

| Route | Body | Answer |
|---|---|---|
| `GET /` | — | the page |
| `POST /api/session` | `{"init_data": "…"}` | the session, the open questions, the log, the artefacts |
| `POST /api/answer` | `{"init_data": "…", "question_id": "…", "value": "…"}` or `{"option_index": 1}` | the answered question |

The panel **reads** through doors that already exist — the harness for the
agent's side, the api's MCP for the store's — and adds no capability of its
own. It writes nothing: a browser that opened a database would be a second
writer with a screen.

---

## 6. Gates

| # | Gate | PASS |
|---|---|---|
| G1 | the registry decides, and refuses with a reason | `node --test deploy/harness/test/` |
| G2 | the `ask` blocks and returns the answer | the MCP test: the call does not return, the question reaches the broker, the answer comes back |
| G3 | an unanswered question ends | the same test with the deadline passed: `isError`, and the agent is told why |
| G4 | the channel draws the four kinds | `tests/transport/test_bot_channel.py` |
| G5 | the panel knows who is asking | `tests/transport/test_bot_miniapp.py` |
| G6 | the routing is visible | `GET /v1/routing?client=…` answers with the runtime **and the reason** |
