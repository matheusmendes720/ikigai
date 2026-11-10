# Chained routines — the router, the state, and the human in the loop

**Status:** specification (2026-11-09)
**Anchor:** [ADR-037](../../code-docs/adr/ADR-037-data-layer-canonical-turn.md) · [ADR-039](../../code-docs/adr/ADR-039-websocket-sync-transport.md) · [ADR-040](../../code-docs/adr/ADR-040-client-state-and-drafts.md)
**Companion:** [router.md](./router.md) · [SYSTEM-PROMPTS.md](./SYSTEM-PROMPTS.md) · [SKILL-SPECS.md](./SKILL-SPECS.md)
**Reference:** [Telegram Bot Features](https://core.telegram.org/bots/features) · [Telegram Mini Apps](https://core.telegram.org/bots/webapps)

This document specifies the **chain**: the path from one message in a chat to a routine that
runs, produces a report, and asks the owner before it commits anything. It is the layer the
harness has today only in outline.

---

## 0. Verdict

The harness answers a routine **by name**. This spec adds the four things between the owner's
sentence and that name, plus the one thing after it — the confirmation.

| Piece | Today | This spec |
|---|---|---|
| A message becomes an intent | ✗ — no `/` means "append to draft" | Stage 0, a router with a deterministic table first |
| A routine is a stateful session | ◐ — one `pi` process per `tg:<chat_id>` | Stage 1, a session key that survives topics and restarts |
| A routine is grounded in `strategics/` | ◐ — the skills say to read it; nothing selects *what* | Stage 2, two-phase retrieval over the index |
| A routine produces a report | ✗ — plain text via `sendMessage` | Stage 3, `sendRichMessage` |
| The owner decides before it is written | ◐ — `/guardar`, typed | Stage 4, `callback_query` buttons and a Stop button |
| Two devices see one store | ◐ — the store yes, the chat no | §7 — and the limits are not where they look |

**Nothing here belongs in `src/`.** ADR-037 D7: the agent is external. The chain lives in
`deploy/harness/`, beside `server.mjs`, and reaches the store through the same six MCP tools
the bot uses. A file under `src/` that imports it is a drift.

---

## 1. The shape

```
owner ──message──▶ bot ──▶ POST /v1/route ──▶ [0] router        (intent, slots)
                                          ──▶ [1] session       (state the run resumes from)
                                          ──▶ [2] routine       (skill + strategics grounding)
                                                │
                                                │ MCP (six tools, the only writer)
                                                ▼
                                          [3] synthesis      (rich message)
                                                │
owner ──button───▶ bot ──▶ POST /v1/decide ──▶ [4] HITL        (commit / edit / discard)
                                                │
                                                ▼
                                          the store ──▶ ws ──▶ every client
```

Two rules the chain inherits and must not break:

1. **The router never writes.** It names a routine and fills slots. The routine writes, through
   the service layer, with a revision and an idempotency key (ADR-037 D5).
2. **A stage is a typed boundary.** Each arrow carries a JSON object that is validated before
   the next stage sees it. A chain of free text is a chain with no failure mode — and therefore
   no test.

---

## 2. Stage 0 — the router

### 2.1 Deterministic first, model second

The harness **fails closed**: `/v1/routine` refuses an id that is not in the published projection
(`loadRoutines()` in `deploy/harness/server.mjs`). A router that guesses is a router that
returns a 400 to the owner's face.

Order of resolution:

1. **A slash command.** `/daily-note` is not routed; it is dispatched. The table in
   `src/bot/main.py` (`ROUTINES`) already owns those names, and the bot already calls the
   harness directly. Routing them again would be a second spelling of the same fact.
2. **A deterministic pattern.** A small table of Portuguese and English phrasings, matched on
   normalized text, with no model. This is where most sentences land.
3. **The model**, only when (1) and (2) both abstain. It answers with the id and nothing else.

### 2.2 The intent table

| Intent | Routine id | Slots the routine needs |
|---|---|---|
| "fecha o dia", "registra o dia", "daily" | `daily-note` | `date` (default: today) |
| "revisão da semana", "weekly" | `weekly-review` | `week` (default: the current ISO week) |
| "fecha o mês", "monthly" | `monthly-review` | `month` |
| "planeia o trimestre", "quarterly" | `quarterly-plan` | `quarter`, and the `onda` split |
| "lê o arquivo X", "o que está guardado sobre X" | `store-read` | `query`, `kinds` |
| "grava isto", "regista a decisão" | `store-write` | `kind`, `title`, `body` |
| "sincroniza o vault" | `vault-sync` | none |

`store-read`, `store-write` and `vault-sync` are **roles**, not cadences (`router.md` §2). They
are routable, and they are not in the bot's `ROUTINES` table today — a gap this spec closes.

### 2.3 The output contract

```json
{ "routine": "weekly-review", "confidence": 0.86, "slots": { "week": "2026-W45" }, "why": "…" }
```

- `routine` **must** be one of the ids in `loadRoutines()`, or the response is a 400 naming
  the known ones (the harness already does this).
- `confidence < 0.6` → the chain does not run. It answers with the three closest routines as
  buttons. Guessing from a weak signal spends two minutes of model time to produce a report
  nobody asked for.
- `slots` is validated against the routine's own contract, not a shared blob.

---

## 3. Stage 1 — the session

A `pi` session is a conversation, a context window and a compaction history. It cannot be
shared (the harness pins one process per session id with `--session-id`).

### 3.1 The key

```
session = "tg:" + chat_id + (":" + thread_id if the message is in a topic else "")
```

`tg:<chat_id>` is what the harness builds today. The `thread_id` half is the change, and it is
the whole point of **topics in private chats** ([Bot API](https://core.telegram.org/bots/api#createforumtopic),
`createForumTopic` / `editForumTopic` / `deleteForumTopic`):

- one topic per routine in flight — the daily note, the weekly review, the quarter;
- a "thinking" topic is a conversation that does not pollute the main chat;
- a topic survives a bot restart, the same way a chat does.

This is a **native** client feature. It buys stateful, parallel, resumable conversations with no
custom UI — which is exactly what "interactive stateful sessions as routines" asks for.

### 3.2 What the session carries

| Key | Lives in | Why |
|---|---|---|
| `draft` | `ikig.drafts` (ADR-040) | prose in progress, survives a restart |
| `route` | harness memory (SQLite, `memory.mjs`) | a follow-up sentence joins the run it belongs to |
| `last_seq` | client | the websocket replay cursor (ADR-039) |
| `device` | client-supplied label | see §7 — the chat cannot supply it |

The rule: **prose lives in the store, route state lives in the harness, cursors live in the
client.** A session that keeps prose in the harness loses it on the next deploy.

---

## 4. Stage 2 — the routine

### 4.1 The skill is the routine

`specs/harness/skills/<id>/SKILL.md` is the source, copied into `.pi/skills/` by
`deploy/harness/entrypoint.sh`. A routine that is not in the projection does not run.

### 4.2 Grounding in `strategics/`

`strategics/` is mounted read-only into the harness (`deploy/compose.yml`, `../strategics`). It
is nine files, indexed by `strategics/00-ÍNDICE-PROGRESSIVO.md`.

The chain reads it in **two phases**, never one:

1. **Select** — read the index, choose the one or two files the routine names (`router.md` §3
   already maps routine → file). This is a table lookup, not a model call.
2. **Extract** — read only the chosen file, and only the sections the skill's contract asks for.

Dumping the tree into the prompt is the failure mode: it spends the context window on material
the routine will not cite, and it makes the report's claims untraceable. A report that names
`strategics/Modelagem Operacional.md` and quotes it is a report the owner can check.

### 4.3 The triggers

Three kinds, and they are not the same mechanism:

| Kind | Example | Where it lives |
|---|---|---|
| **Cadence** | every day at 22:00, `daily-note` | a scheduler, not yet built — see §11 G3 |
| **Intent** | "fecha o dia" → `daily-note` | Stage 0 |
| **Event** | the ingestion wrote 40 artifacts → suggest `vault-sync` report | the change feed (ADR-039) |

The cadence trigger is the one that does not exist in any form today. The bot can run a routine,
and nothing in the deployment ever asks it to.

---

## 5. Stage 3 — synthesis

### 5.1 Rich messages, not plain text

Telegram now ships `sendRichMessage` for exactly this content
([features](https://core.telegram.org/bots/features#rich-messages)): headings, tables with
alignment and spans, LaTeX inline and block, collapsible details, footnotes, media blocks with
captions, and **multiple embedded buttons in one message**.

A weekly review is a table and a decision. Sending it as 4 000 characters of `sendMessage` is
the client deciding that structure is not worth carrying. It is.

### 5.2 When a Mini App earns its keep

| Report | Surface | Why |
|---|---|---|
| Daily note, decision, OKR | rich message | read once, closed |
| Weekly / monthly review | rich message | one table, a few decisions |
| Quarterly plan | **Mini App** | the plan is a tree with reordering and toggles |

The test: if the report is a **document**, send a rich message. If the report is a **tool the
owner manipulates**, it is a Mini App (§10).

---

## 6. Stage 4 — HITL

### 6.1 The buttons

An inline keyboard under the agent's answer:

```
[ Guardar ]  [ Editar ]  [ Descartar ]
```

`callback_data` is a small, versioned token — `decide:v1:<action>:<uid>:<revision>` — never a
sentence, and never a uid alone (a stale revision must be a 409, ADR-037 D5).

Today the bot has **no** `callback_query` handling and sends **no** `reply_markup`: the whole
interaction is typed (`/guardar`). The buttons are the largest single UX gap.

### 6.2 Streaming, and the Stop button

In private chats, bots can show a **draft response while it is generated** and the user can
**stop it**, which arrives as an update the bot can act on
([features](https://core.telegram.org/bots/features#streaming-replies); `sendMessageDraft`,
`sendRichMessageDraft`, `MessageGenerationStopped`).

This replaces a design the bot has today: a poll loop that must not block, and a routine whose
answer arrives later as a second message. With drafts:

- the owner watches the report form, instead of a silent chat;
- **Stop** cancels the routine — the tag: "não para de gerar" is a real user need, and the
  client now has a native gesture for it.

**WHAT IS BUILT (G7, 2026-11-09).** The bot opens a **preview** when a routine starts
(`sendMessageDraft` with `can_stop`), refreshes it while the work runs — a preview lives about
thirty seconds, and a routine does not — and handles the `stopped_message_generation` update
that the button produces. The stop does TWO things: it cancels the bot's wait, and it asks the
harness to release the session, which kills the `pi` process holding the turn. The second one
is the one that matters: a bot that only stops waiting leaves an agent working, and an agent
that keeps working keeps writing. A run that was stopped answers **"cancelled", not "failed"** —
a cancelled routine did not fail, and the owner is told the truth.

**THE STOP NAMES THE RUN.** A chat is ONE session, so every routine the owner starts in it
shares the session key. A Stop from a preview that is already over would therefore land on the
NEXT routine of that chat and kill it — the owner pressed Stop on the daily-note and the
weekly-review died instead. So a run is NAMED: the preview's id travels to the harness as the
run's token, and a stop that names no live run changes nothing. The token lives as long as the
run, and dies with it.

**THE RUN IS TOLD, NOT INFERRED.** The agent's turn is an **event** (`agent_settled`), and a
killed agent never emits it. So a run cannot learn that it was stopped by waiting for its own
turn to fail — it has to be told, and the harness's stop signal is the telling. Measured on
the box before that was fixed: the agent was dead (no `pi` in the container's process table) and
the store was untouched (1 973 artifacts before and after), but the run answered **nothing for
twenty minutes**, until its own ceiling rejected the collection — and the harness's event log
said "started" and never said "cancelled". The run now races its turn against the stop signal,
so a stop ends the run in milliseconds.

**WHAT THE PREVIEW IS NOT.** It carries the **state** of the run, not the **tokens** of the
report: the harness does not publish the agent's text as it is generated, so there is nothing to
stream into it yet. The finished report is still sent as a message — a draft is a thirty-second
preview, and the message is what stays in the chat. Streaming the report itself needs the
harness to publish the deltas, which is a separate piece of work.

### 6.3 The state machine

```
idle ──intent──▶ routing ──confident──▶ running ──▶ awaiting_decision ──commit──▶ committed
                    │                      │                │
                    └─ambiguous─▶ asking   └─stop──▶ idle    └─discard──▶ idle
```

Every transition is a row the harness can replay. A run that dies mid-way resumes at
`running`; it never resumes at `committed` on a guess.

---

## 7. Multi-device — and the limit nobody mentions

**The chat cannot tell two devices apart.** A Telegram account is one `chat_id`; the same person
on a phone and on a desktop writes into the same conversation. There is no `device_id` in a
message update.

So "multi-device serving" splits in two, and only one half is a Telegram question:

| Half | Answer | Where |
|---|---|---|
| **The store** | one DOM, N clients, a write is revision-guarded | already true (ADR-037 D5) |
| **The conversation** | one chat, one session; two devices share it by construction | already true |
| **The cursor** | per client, not per device | ADR-039, `last_seq` |

What is genuinely missing is the **client label**: `IKIGAI_CLIENT_ID` is a deployment-wide
default (`owner`), so two clients write as one identity. A device label is a field the client
sends, and it belongs in the *store* (who wrote this), not in the chat.

---

## 8. Retrieval with hysteresis

### 8.1 What hysteresis means here

Two thresholds, and memory between calls:

```
score >= T_high        → the artifact is a hit
score <= T_low         → it is not
T_low < score < T_high → whatever the PREVIOUS call in this session decided
```

The point is not precision; it is **not flipping**. A weekly review that names the same three
artifacts every time it is asked the same question is a review the owner can trust. One that
alternates between four and five because the vector landed on a boundary is noise wearing a
table.

### 8.2 What blocks it today — measured

Hysteresis needs a **score**, and the search does not produce one:

- `src/data/repository.py:511` — `select {_ARTIFACT_COLUMNS} … order by embedding <=> %s::vector limit %s`.
  The distance orders the rows and is then **discarded**;
- `src/contracts/dom.py` — `SearchQuery` has `semantic: bool`, `limit`, and **no floor**;
  `SearchResult` carries artifacts and a cursor, and **no score**.

So this is a **contract change**, not a knob: `SearchResult` (or each hit) gains a `score`, and
`SearchQuery` gains `min_score`. Both are additive to a frozen model, which means a new field
with a default and a drift test — not a fork of the model.

### 8.3 The conflict to be explicit about

ADR-037 D1 defers the algorithms, and it names hysteresis: *"no PAV kernel, no hysteresis FSM,
no scoring in the published tree."*

That sentence is about the **PAV state machine** — a control-theory construction over goal
state. Retrieval hysteresis is a different, much smaller thing: two thresholds over a number
the database already computes. It is proposed here as the second, and only after §11 G5 proves
the store answers the same query twice. If the deferred FSM is meant, this section is not it and
should not be cited as it.

---

## 9. Telegram native features — what is available, and what we use

| Feature | What it buys | Status |
|---|---|---|
| Slash commands + `setMyCommands` scopes | the deterministic door, localized | ✅ present |
| `callback_query` + inline keyboards | HITL without typing | ✗ **missing** — the biggest gap |
| `sendRichMessage` / rich markdown | tables, LaTeX, collapsibles in a report | ✗ missing |
| `sendMessageDraft` + `MessageGenerationStopped` | progress, and a native **Stop** | ✗ missing |
| Topics in private chats | one conversation per routine, parallel and resumable | ✗ missing |
| `editMessageReplyMarkup` | a toggle that does not resend the message | ✗ missing |
| Deep links `?start=` / `?startapp=` | a routine launched from a link, 64 chars of payload | ✗ missing |
| Menu button → Mini App | a persistent door, no command needed | ✗ missing |
| Inline mode | send an artifact into another chat | ✗ not applicable yet |
| Ephemeral messages | private answers in a group | ✗ not applicable (1:1) |
| `WebApp.initData` validation | the Mini App is authenticated by HMAC-SHA-256 | ✗ missing |
| CloudStorage / DeviceStorage / SecureStorage | Mini App state without a backend round-trip | ✗ missing |
| Local Bot API | no 20 MB download / 50 MB upload ceiling | ◐ not needed yet |

---

## 10. Mini Apps — for the reports that are tools

### 10.1 When

The quarterly plan, and the synthesis that spans more than one artifact (the "interactive
reporting synthesis" in the request). A plan is a tree you reorder; a synthesis is a set of
findings you collapse and expand.

### 10.2 The contract

1. **Launch** from an inline button (`web_app`) or the menu button. Both arrive with
   `initData`.
2. **Validate** on the server: `initData` is a query string; the check is
   `HMAC_SHA256(data_check_string, secret_key)` where `secret_key = HMAC_SHA256(bot_token, "WebAppData")`,
   compared with `hash`. Third parties validate the Ed25519 `signature` with the published
   public key instead — no bot token needed
   ([webapps](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app)).
3. **Read** through the six MCP tools, like every other client. A Mini App that opens a database
   is a second writer with a browser.
4. **Write** through `upsert_artifact`, and only after `showConfirm`.
5. **Never trust the client's `auth_date`** without a freshness window.

### 10.3 Where it lives

Static assets served by the harness container (`deploy/harness/`), not by `src/`. The Mini App
is a **projection** (ADR-037 D8), and the DOM does not know it exists.

---

## 11. Gates — ordered, each falsifiable

| # | Gate | PASS |
|---|---|---|
| G1 | The deploy is green and the stack is current | `docker compose ps` shows six healthy services; `/start` lists store, agent and memory |
| G2 | One routine end to end | `/daily-note teste` → the agent answers, `/busca teste` finds the artifact, `/memoria` shows the session |
| G3 | A cadence fires itself | the daily note exists at 22:05 with no human message, and the run is in the harness memory |
| G4 | The router routes | "fecha o dia de ontem" runs `daily-note` with `date=yesterday`; "asdkjh" answers with buttons, not a 500 |
| G5 | The store repeats itself | the same query, twice, returns the same uid set and the same order |
| G6 | HITL commits | **Guardar** writes once; the same button twice writes once (idempotency key); a stale revision is a 409 |
| G7 | Stop stops | the Stop button cancels the run within 2 s, and no artifact is written |
| G8 | Two clients converge | a write from the phone appears on the desktop through the ws, and neither reorders |

G1–G2 are the deployment; G3–G8 are this spec. Nothing below G2 is testable while G1 is red.

**WHAT "NO ARTIFACT IS WRITTEN" MEANS.** The store is append-only, and the routine writes its
note at the END of its turn (the skill's step 5). So a stop before that write leaves the store
untouched; a stop after it keeps what was already written, because a note that exists is a note
the owner asked for, and deleting it would be the opposite of stopping. The gate's promise is
about the write that had not happened yet.

**WHAT G7 WAS MEASURED AGAINST.** On the box, 2026-11-09: a `daily-note` started, the stop
fired 3 s in, and the store held **1 973 artifacts before and 1 973 after** — the agent was
killed (no `pi` left in the container's process table) and nothing was written. The run's own
answer is what the fix made true: it now comes back as `cancelled` in the same milliseconds the
stop took, instead of waiting for the run's ceiling twenty minutes later. The **button** is
still the owner's half: start a routine, press **Stop**, and the answer must be "parada", not
"falhou".

---

## 12. Decisions that are not mine to take

1. **Hysteresis** — retrieval policy (this §8.2, after a contract change), or the deferred PAV
   FSM that ADR-037 D1 names? The two are not the same work.
2. **Where the chain lives** — `deploy/harness/` (in the repository, outside `src/`, shipped in
   the agent's image) or outside the repository entirely. ADR-037 D7 allows both; only the first
   is testable by CI.
3. **Natural language, or a stricter door** — the deterministic table resolves most sentences and
   refuses the rest. A model router resolves more and can invent a routine that does not exist.
   The harness fails closed, so the invention is a 400 rather than a wrong write — but it is
   still a refusal the owner did not ask for.
4. **One topic per routine** — it is the cleanest state model, and it changes the chat's shape.
   Some owners will hate it.
