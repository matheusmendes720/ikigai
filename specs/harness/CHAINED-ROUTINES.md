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

**AND THE NIGHT IS A UNIT — A BUSY SESSION DOES NOT LOSE IT.** Measured on the code (2026-11-11):
the cadence runs in the OWNER's session (`session_id=f"tg:{cadence.chat_id}"`), so a night when the
owner is in conversation with the bot is a night the harness REFUSES (409, `routine.refused`). The
bot used to swallow that refusal and go straight back to `next_run()` — which returns TOMORROW — so
the note of that night simply never existed, while the code's own comment claimed the night was
not lost. The night is now retried every 15 minutes (eight attempts, two hours), and every
attempt writes the note of the **night's** day: a retry that crossed midnight UTC would name
tomorrow, and tomorrow's own run would then be swallowed by the idempotency key — the store eats
a repeated key BEFORE it looks at the body — and tomorrow's note would vanish without a word.
Past the ceiling the night IS lost, and the owner is told so: a night that disappears without a
word is the failure this path exists to prevent. Whether the cadence should have a session of its
OWN is the owner's decision (§12); this is the fix that does not pre-empt it.

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

| # | Gate | PASS | Status |
|---|---|---|---|
| G1 | The deploy is green and the stack is current | `docker compose ps` shows six healthy services; `/start` lists store, agent and memory | **PASS** |
| G2 | One routine end to end | `/daily-note teste` → the agent answers, `/busca teste` finds the artifact, `/memoria` shows the session | **PASS** |
| G3 | A cadence fires itself | the daily note exists at 22:05 with no human message, and the run is in the harness memory | **RED** |
| G4 | The router routes | "fecha o dia de ontem" runs `daily-note` with `date=yesterday`; "asdkjh" answers with buttons, not a 500 | **PASS (by test)** |
| G5 | The store repeats itself | the same query, twice, returns the same uid set and the same order | **PASS** |
| G6 | HITL commits | **Guardar** writes once; the same button twice writes once (idempotency key); a stale revision is a 409 | **PASS** |
| G7 | Stop stops | the Stop button cancels the run within 2 s, and no artifact is written | **PASS** |
| G8 | Two clients converge | a write from the phone appears on the desktop through the ws, and neither reorders | **PASS** |
| G9 | The prose reaches the desktop | the note the cadence wrote is a file in the write-back tree, with the same bytes the store holds, and the ingestion that follows writes nothing | **UNKNOWN** — armed for 2026-11-12T01:00Z |

G1–G2 are the deployment; G3–G8 are this spec. Nothing below G2 is testable while G1 is red.

**THE TRACKER, AND WHAT ITS WORDS MEAN.** One status per gate, and three values only:

- **PASS** — the whole clause was measured and holds. The line below says where.
- **RED** — it was measured and it does **not** hold. A red gate is a defect with a date, not a
  to-do.
- **UNKNOWN** — no measurement was found, in this session or in the repository. It is written as
  UNKNOWN rather than guessed, because a gate nobody measured and a gate that passed look
  identical in a table that only records intent.

| Gate | Where the PASS comes from | What is left |
|---|---|---|
| **G1** | 2026-11-11, on the box: six `ikigai-*` containers `healthy` on image `sha-c935e180` (api, bot, db, harness, sync, ws) — the deployed image is the current `main` (PR #74) — and `/v1/health` answers `ok: true` with `live_sessions: 0`, `busy_sessions: 0`, seven routines and no problems | the `/start` half — the owner's chat |
| **G2** | 2026-11-10, all three halves: the routine's note (`Relatório Diário — 2026-11-09`, revision 4) is returned by `search_artifacts`, reads back by uid, and the harness memory holds `routine.started` + `routine.finished` for `tg-box-01` | — |
| **G3** | 2026-11-11, **the note landed once — on the build that carries the fixes**: the cadence fired on its own — `routine.started` at **2026-11-11T01:00:00.130Z** (= 22:00 in the configured −03:00), `client=tg:2115322359`, `message=""` — and wrote **`not:2026-11-11:74dfed05:d6ad7bd8023c5f59`**, "Relatório Diário — 2026-11-11", `quarter=Q4-2026`, `client_id=pi-tg-2115322359`, **9 items classified** (3 done · 0 partly · 5 not started · 1 dropped), each with its evidence, and the `EVIDENCES` edges landed with the note. The run finished in **86 s** (`routine.finished` at **2026-11-11T01:01:26.173Z**), with no human message and no question asked. **The night before, the same cadence fired and DIED**: `routine.started` at **2026-11-10T01:00:00.129Z**, `routine.failed` at **2026-11-10T01:30:00.135Z** — exactly **1 800 006 ms** later, "Timeout collecting events" — and it wrote **nothing** (the note for 2026-11-10 in the store was written at **17:52:47Z** by a *manual* run). That night ran on a build that has since been retired: the two fixes it was missing (#61, the store tools, merged **2026-11-10T13:32Z**; #65, the ceiling that kills the agent, merged **16:26Z**) landed **before** the night that passed | the gate is RED, and it is not the retired night. **THE REASON CHANGED ON 2026-11-11:** a night that a busy session refused WAS lost — the cadence runs in the owner's session (`session_id=f"tg:{cadence.chat_id}"` — `src/bot/main.py:1440`), so a night when the owner is in conversation is a night the entry is **refused** (409, `routine.refused`), and `next_run` returned the next occurrence, so **no note was written** (`src/bot/cadence.py:74-86`); the bot told the owner it was refused, and its own comment said *"the night is not lost"*, which was false. **That is fixed**: the night is now retried every 15 minutes (eight attempts, two hours), every attempt writes the note of the **night's** day, and past the ceiling the owner is told the night was lost (`_retry_cadence`, `src/bot/main.py`). **What is left** is the other half: the cadence still runs in the owner's session — whether it should have one of its own is the owner's decision (§12) — and the deployed image (`sha-c935e180`) has **not** run the cadence yet: the next firing is 2026-11-12T01:00Z, and it will be the first to write through the vault-write path |
| **G4** | 2026-11-10, **by test only**: 11 cases in `src/ikigai/tests/test_bot_router.py` — a sentence names a routine, the relative day is carried as a slot, accents and case do not change the reading, a sentence that names none is refused, two routines is an abstention, a button token round-trips and a forged one is refused | the live half — the owner typing "asdkjh" and getting buttons, not a 500 |
| **G5** | 2026-11-10, on the box: the same `search_artifacts` query twice → 10 uids, **the same list in the same order** | — |
| **G6** | 2026-11-10, on the box: `created` (rev 1) → the same `idempotency_key` again → **`unchanged`**, rev 1; a stale `expected_revision=999` → **`conflict`**, and the artifact kept revision 1 | the button itself, in the owner's chat |
| **G7** | 2026-11-10, on the box: the run settles in **55 ms** (gate: 2 000), the agent of the run is **born** and **gone** 222 ms after `routine.cancelled`, **1 974 artifacts before and after** | the button itself, in the owner's chat |
| **G8** | 2026-11-10, on the box: `seq` `[10589, 10590, 10591]` on **both** clients, strictly increasing, no duplicates; the gap closes at `[10592, 10593]` after a disconnect; **1 974 before and after** | a second physical device |
| **G9** | the arrow itself is measured (2026-11-11, ADR-043 §5.1, by `deploy/probes/vault-arrow.sh`): **23** files written, **23/23** with `sha256` == the store's `body_hash` and the store's `ueid` in the frontmatter, **1 976** live artifacts and **all** of them with a `vault_path` (the writer's backlog is zero), and the ingestion saying `created=0 updated=0 unchanged=1976` — **zero** revisions written by `vault-sync` on those lines | **the night**: the note of 2026-11-12T01:00Z has to go through the arrow on the current image — one file, the same bytes, **+1 revision from `vault-write`** and **zero from the ingestion** |

**THE LETTERS ARE NOT UNIQUE IN THIS REPOSITORY.** `specs/production-readiness/ROADMAP.md` has
its own `G1`–`G5` — the *deployment* gates (store, content, harness, Telegram, delivery) — and
they are not these. `ROADMAP`'s `G2` is "the prose enters and the grounding arrives", whose (b)
half **was RED**: measured 2026-11-10 on the deployed image, `load_strategics(/app)` returned
**0 documents** from **9 files**, because the loader keeps only files whose frontmatter carries
`tags: … strategic` and none of the nine had frontmatter. **That is fixed, and the gate is
green.** PR #52 (frontmatter on the nine files, the BOM and NUL bytes out, and a guard that
counts them) **landed 2026-11-10T12:42:43Z**; re-measured on the deployed image
(`sha-c935e180`, 2026-11-11) `load_strategics(/app)` returns **9 documents** and an index of
**95 169 chars** — not empty. The number reproduces in the repository's own corpus
(`load_strategics(<repo>)` → 9 documents, 95 169 chars) and it is the number PR #52 measured;
the ROADMAP carried it with the digits transposed (`95 167`), corrected in the same PR. A reader
who takes "G2 is green" from one document and "G2 is red" from the other is not confused —
they are reading two different gates that were given the same name.

**WHAT "NO ARTIFACT IS WRITTEN" MEANS.** The store is append-only, and the routine writes its
note at the END of its turn (the skill's step 5). So a stop before that write leaves the store
untouched; a stop after it keeps what was already written, because a note that exists is a note
the owner asked for, and deleting it would be the opposite of stopping. The gate's promise is
about the write that had not happened yet.

**WHAT G7 WAS MEASURED AGAINST.** On the box, 2026-11-09: a `daily-note` started, the stop
fired 3 s in, and the store held **1 973 artifacts before and 1 973 after** — the agent was
killed and nothing was written. The run's own answer is what the fix made true: it now comes
back as `cancelled` in the same milliseconds the stop took, instead of waiting for the run's
ceiling twenty minutes later. The **button** is still the owner's half: start a routine, press
**Stop**, and the answer must be "parada", not "falhou".

**WHAT "THE AGENT WAS KILLED" MEANS, MEASURED PROCESS BY PROCESS.** The old measurement said
"no `pi` left in the container's process table". That was true of the RUN's agent and not of the
table, which another probe was sharing — a table read at one instant cannot say WHICH agent it
is talking about. Re-measured on the box, 2026-11-10, on a freshly deployed container whose
baseline was **zero agents**: the agent of the run was BORN about a second into the run (a `pi`
appeared in the process table), the stop named that run, and the agent was GONE within **242 ms**
of the `routine.cancelled` event — the container went back to zero. The run settled in **96 ms**
(the gate is 2 000 ms), the stop that named ANOTHER run was refused without touching the live
one, and the store held **1 974 artifacts before and 1 974 after**. The claim that survives the
measurement is the narrow one: **the agent of THIS run is gone**, so the note it was writing
never arrives.

**WHAT G8 WAS MEASURED AGAINST.** On the box, 2026-11-10, with the deployed stack and the bot
stopped for the duration (the bot announces every change that is not its own to the owner's
Telegram, and a probe's writes would read as the owner's work). Two `WebSocketClient`s — the
published one, not a probe's own socket — subscribed to `ws://ws:8001/sync`, and the writes went
through the **same path the phone uses**: `McpClient` plus `_write_arguments` from
`src/bot/main.py`, the same envelope and the same contract.

| what the gate asks | what was measured |
|---|---|
| a write from the phone appears on the desktop through the ws | **yes** — 3 writes, 3 events, on both clients |
| neither reorders | `seq` `[10589, 10590, 10591]` on BOTH clients, strictly increasing, no duplicates |
| the two clients agree | the **same** uid list and the **same** `seq` list |
| the gap closes after a disconnect | desktop parked at 10591, 2 writes missed, reconnect → `[10592, 10593]`, in order, nothing repeated |
| the store is left as it was | **1 974 artifacts before and 1 974 after** |

The latency measured from the moment the phone DECIDES to write is **84–95 ms** on a warm path
(the first write of a burst pays ~1 200 ms, which is the pool and the MCP handshake warming up,
not the feed). And the event lands **42–56 ms BEFORE the write's own HTTP answer returns** — the
`NOTIFY` travels with the write, the answer has further to go. A client that waited for its own
answer before telling anyone would be slower than the store already is.

**THE TIP IS THE STORE'S `max(seq)`, AND THAT IS WHAT MAKES `lost` HONEST.** The `hello` frame
and the `resume` answer both report the tip, and on a healthy stack they agree with
`select max(seq) from ikig.artifact_events` — measured: `hello` 10511, `resume.tip` 10511,
`max(seq)` 10511. The log is PRUNED rather than gap-free (it kept 79 rows spanning `seq` 951 to
10 511), which is exactly why `resume` answers `floor` and `lost` beside the events: a `since`
below the floor is a client that missed something the store already forgot, and that is a
different answer from "nothing happened". A probe that asks `resume since=0` on this log gets
`lost: true` — correctly, and it must not be read as a defect.

**WHAT G8 DOES *NOT* CLAIM.** One Telegram `chat_id` is one conversation on every device; there
is no `device_id` in a message update (§7). So "the phone and the desktop converge" is measured
on two **websocket clients of the store**, which is the part the ws owns. The part that needs a
second physical device — the same chat writing from two phones — is the owner's half, like the
Stop button in G7.

**WHAT G9 WAS MEASURED AGAINST.** The box, 2026-11-11 at 10:12Z, image `sha-c935e180`, against
the **real** store (1 976 artifacts alive) and the real tree of the writer
(`/mnt/volume-fsn1-1/vault-escrita`, 23 files). The measurement is
`deploy/probes/vault-arrow.sh` — which **exits non-zero** when a fact is false — run against the
running stack, not against a fixture.

| what | measured |
|---|---|
| the file is what the store says | `sha256(file)` == `body_hash(store)`, **23/23**, 0 diverged, 0 missing |
| the file carries the identity | the frontmatter's `ueid:` is the store's uid, **23/23** |
| the store knows where the file is | **1 976 of 1 976** live artifacts have a `vault_path`; the writer's log says `scanned=0` |
| the cycle closes | the ingestion: `scanned=1977 created=0 updated=0 unchanged=1976 skipped=25`, four rounds in a row |
| the ingestion does not touch them | `ikig.artifact_revisions` on those 23 lines: **zero** revisions by `vault-sync` |
| the trees are separate | `write`: only the new tree, `rw`; `sync`: all three, `ro` |
| the git clone of the vault is untouched | `git -C /app/vault status --porcelain` → empty |
| the desktop delivery is wired | Syncthing folder `notas-escrita` (`sendreceive`, watcher on): `needFiles: 0`, `errors: 0` |

**WHAT G9 DOES *NOT* CLAIM.** That the arrow works is already measured (ADR-043 §5.1) — and it was
measured over 23 files written in **two** rounds, the second of them after a write that moved the
store's `updated_at` without moving the revision, which today's `_update` cannot do. The gate is
narrower: **a note written by the current image, going through the whole arrow** — one file, the
same bytes, **+1 revision from `vault-write`** and **zero from the ingestion**. That is the night
of 2026-11-12T01:00Z. And the file reaching the **desktop** is still the owner's half: the box is
in sync (`needFiles: 0`), but seeing the file on the `windows-pc` is a physical thing, like the
Stop button in G7 and the second device in G8.

**WHAT THE G3 RUN WAS MEASURED AGAINST — THREE CAUSES, NOT ONE.** The cadence run of 2026-11-10
(01:00:00Z, no human message) failed at 01:30:00Z. All three causes below were measured, and all
three are fixed; the gate stays **RED** until a cadence run lands a `nota`.

**WHAT THE G3 RUN OF 2026-11-10 WAS MEASURED AGAINST — THREE CAUSES, NOT ONE.** The cadence run of
2026-11-10 (01:00:00Z, no human message) failed at 01:30:00Z. All three causes below were
measured, and all three are fixed — and the run of 2026-11-11 landed a `nota` **on the build that
carries the fixes**. The gate is **RED** for a different reason, and the reason is still in the
code: the cadence shares the owner's session, so a busy session refuses the night, and the night
is not retried (the row above).

**Cause 1 — the agent had no store tools at all.** The run's session made **480 tool calls: 438
`bash`, 32 `read`, 9 `write`, 1 `edit`, and ZERO store tools**. Asked what it had, it answered
"Ferramentas de um servidor MCP chamado `ikigai`: **nenhuma**". It had been writing its own
JSON-RPC client in Node to reach the store. The cause was in `deploy/harness/server.mjs`:
`piArgs()` passed `--no-extensions`, and the comment beside it claimed the MCP client was CORE.
`pi`'s own documentation (`docs/settings.md`) lists `builtin:mcp` among the built-in extensions
and says `--no-extensions` disables them too; `docs/cli.md` names the combination that keeps
only MCP: **`pi -ne -e builtin:mcp`**. Fixed in PR #61 and **proved live**: a new session lists
`mcp__ikigai__search_artifacts|get_artifact|upsert_artifact|delete_artifact|list_relations|embed_text`
plus `mcp__owner__ask`.

**Cause 2 — the ceiling was a PROMISE and not a KILL.** The run answered `routine.failed` at
01:30:00Z and the agent **kept writing until 01:33:08Z** — three minutes of writes after the
owner was told the routine had failed. The SDK's `promptAndWait` passes the ceiling to
`collectEvents(timeout)`, and that timer only **rejects a promise**; it never touches the
process. The agent's turn is an EVENT, and a rejected promise does not kill the thing that was
going to emit it. This is the exact mirror of the G7 defect: there, a run that ended left a live
agent; here, the run that ENDED BY TIMEOUT left a live agent. Fixed: the harness owns the clock
(the SDK's timer is a backstop, given 5 s more so the harness always decides), and a run whose
clock ran out **releases its session** — the agent dies and the session is forgotten, so the next
routine of that chat spawns a fresh `pi`. The answer is `timedOut`, not `cancelled`: nobody
pressed Stop, and the clock is not the owner.

**Cause 3 — the skill had nothing to say about an empty set.** Measured on the box: the store
holds **0** `tarefa` artifacts alive (the only two ever written were probes, both deleted), and
**5** `fase` rows for Q4-2026 (B0–B4, each with its window and its "Done quando"), **5** `okr`,
**7** `kpi`, **1** `revisao`. The `daily-note` skill classified `tarefa` only, and said nothing
about a set that comes back empty — so the agent improvised: it wrote **two `desc`** and **no
note**. The note that WORKED (2026-11-09, revision 4, written through MCP) classified the
**phases and the plan's decision gate**, and said so in its own §1: with no artifact of the
kinds that represent work, "the planned tasks" are B0–B4 and the §4.1 gate. The skill now says
so: a phase is planned work and is classified like a task; an empty set is a **fact about the
day** that goes IN the note; and it is never a reason to write a different artifact, to invent
work, or to ask (a cadence fires at 22:00 with nobody watching — a question nobody answers holds
the run until its ceiling).

**THE PROOF OF G3 IS THE CADENCE, AND IT IS NOT CONTROLLED BY A PROBE.** The 22:00 run is the
first run with the six tools; a probe cannot stand in for it. The gate closes when the note
exists at 22:05 with no human message, and the run is in the harness memory.

**WHAT THE CADENCE RUN OF 2026-11-11 WAS MEASURED AGAINST.** It fired on its own, at
**01:00:00Z** (= 22:00 in −03:00), with `message=""` and no human in the room.

| when | what | where it can still be read |
|---|---|---|
| 2026-11-11T01:00:00.130Z | `routine.started`, `daily-note`, `client=tg:2115322359` | the ledger |
| 01:00:07Z | the agent's first tool call — and the first three were **refused by the schema** | that night's container — **gone** |
| 01:01:21Z | the write: `not:2026-11-11:74dfed05:d6ad7bd8023c5f59`, revision 1, `created` | that night's container — **gone** |
| 2026-11-11T01:01:26.173Z | `routine.finished`, **86 s** in | the ledger |

The two boundaries are read from the harness's ledger (`/app/memory/memory.sqlite`, a **volume**):
it outlived the container and still holds the pair of nights. The two times in the middle were
read from that night's container, and they **cannot be read again** — the container was recreated
on 2026-11-11 and its log went with it. The artifact itself is in the store:
`not:2026-11-11:74dfed05:d6ad7bd8023c5f59`, `created_at 2026-11-11 01:00:00Z` (a nota's
`created_at` is the day it carries — `src/services/sync.py:512-524`), at **revision 3** today:
the run wrote revision 1, and the vault-write path wrote the prose back twice since
(2026-11-11T05:05:03.968897Z).

The note is **"Relatório Diário — 2026-11-11"**, `quarter=Q4-2026`, `client_id=pi-tg-2115322359`,
and it classified **9 items** — 3 done (the AG3 gate decided, the note of 2026-11-10, and the
note itself), 0 partly done, 5 not started (the merge and the phases B0–B4), 1 dropped (Onda 2's
deferral) — each with the evidence that proves it, and the `EVIDENCES` edges landed with the
note. It also names a divergence it found: the KPI of daily reports still reads `actual: 1`
while three daily notes exist. The store went from **1 974 to 1 976** artefacts, and the second
one is the owner's own manual run of 17:52Z the day before (`not:2026-11-10:...`).

**THE RUN GOT TWO THINGS WRONG ON THE WAY, AND BOTH ARE NOW IN THE SKILL.**

- **The `kinds` argument was refused by the schema.** The run sent
  `{"query": {"kinds": {"item": "nota"}, "limit": "20"}}` — an object where a list belongs, and
  a string where a number belongs — and the schema said no. The agent said so in its own
  report (*"as chamadas com `kinds` foram rejeitadas pelo schema nesta passagem"*) and fell
  back to searching by text, which is why the note is good but was not built on the structured
  search. The manual run of the day before, on another provider, had sent
  `{"kinds": ["fase"], "quarter": "Q4-2026", "limit": 20}` and it answered. The skill now
  carries the exact call, and the exact shape: a LIST of kind names and a NUMBER.
- **The first uid was refused.** The manual run's first write carried
  `not:2026-11-10:daily:tg2115322359` — `daily` is not hex and `tg2115322359` is not sixteen
  hex characters — and the store refused it. The agent then copied the previous note's uid and
  it went in. The skill now states the shape: `not:<day>:<8 hex>:<16 hex>`.

**AND THE PRESCRIPTION WAS THEN CALLED, ON THE DEPLOYED API.** A skill that tells the agent to
call a shape nobody tried is a skill that fails at 22:00, in a run nobody watches. So the call
the skill now prescribes was called against the live API — with the MCP handshake, because the
agent does the handshake too:

| the call | what the API answered |
|---|---|
| `{"query": {"kinds": ["tarefa", "fase", "plano"], "quarter": "Q4-2026", "limit": 20}}` | **HTTP 200 · 7 rows** — 5 `fase` and 2 `plano`, the quarter's whole work in one page |
| `{"query": {"kinds": ["nota"], "quarter": "Q4-2026", "limit": 20}}` | **HTTP 200 · 3 rows** — the three daily notes, in a row |
| `{"query": {"kinds": {"item": "nota"}, "quarter": "Q4-2026", "limit": "20"}}` — what the run sent | **REFUSED**: `query.kinds — Input should be a valid tuple [type=tuple_type, input_value={'item': 'nota'}, input_type=dict]` |
| `{"query": {"kinds": ["plano"], "limit": 20}}` — without the quarter | **HTTP 200 · 20 rows**, the limit — it pages |

Two things came out of that table. The refusal names **`kinds` alone**: a number written as
text is coerced and accepted, so the object was the whole defect — and the skill says so now,
instead of blaming the quotes. And the prescription is a **drift test**
(`test_the_daily_note_skill_prescribes_calls_the_CONTRACT_accepts`): the JSON in the skill's
steps is parsed and validated against `SearchQuery`, the very model the API validates with, so a
skill that goes back to prescribing an object fails the suite instead of failing at 22:00.

**THE DAY OF THE NOTE, AND WHY IT IS NOT THE OWNER'S.** The note names **2026-11-11** — the
run's own UTC day — while the owner's report is titled with the local day, **2026-11-10**. The
two are one day apart BY CONSTRUCTION: the cycle fires at 22:00 in −03:00, which is 01:00Z of
the next day.

It cannot simply be made "the owner's day". The note's uid AND its idempotency key are both
derived from the day, and the store swallows a repeated key as `unchanged` **before it even
looks at the body** (`ikig.idempotency_keys`, `on conflict do nothing`). A rule that named the
local day would name 2026-11-11 on the night of the 10th — the very day the note of
2026-11-11 already carries — and that night's write would be a **silent no-op**: the note
vanishes and nobody says so. (And if the key were different, the create would be refused with
a 409 — *"the uid is taken"* — or the agent would revise yesterday's note to get around it.)

So the day the run hands the agent is the run's UTC day, which is the day the store already
carries (2026-11-09, 2026-11-10, 2026-11-11), and the rule lives in one function
(`run_day`) with a test that says it must advance once per run. **What is left to the owner is
the report's title**: whether the owner's message should name the run's day (2026-11-11, like
the note) or the day that just ended (2026-11-10, like the table of "today" it carries).

**WHAT THE CEILING WAS MEASURED AGAINST — THE AGENT DIES, PROCESS BY PROCESS.** The fix for
cause 2 is measured on the box, 2026-11-10, on the deployed image `sha-46d22cc0`, with a
`store-read` routine (read-only: it cannot pollute the store) and a ceiling of **25 000 ms**:

| moment | the agent (`pi`) | the agent's MCP child | the session file |
|---|---|---|---|
| baseline | 0 | 0 | — |
| t = 3,1 s | **1** (pid 1189) | 1 (pid 1201) | 32 470 B |
| t = 6,6 s | 1 | 1 | 36 547 B |
| t = 10,0 s | 1 | 1 | 58 399 B |
| t = 13,5 s → 20,3 s | 1 | 1 | 58 399 B (frozen) |
| **t = 25,3 s → http 502** | **0** | **0** | 58 399 B (frozen) |
| t = 30,3 s | 0 | 0 | 58 399 B (frozen) |

The answer was `{"ok":false,"error":"the routine failed: the routine exceeded its ceiling of
25000 ms"}` with **http 502**, the event was **`routine.timed_out`** (`ceiling_ms: 25000`), and the
pool's `live_sessions` went back to **0** — the entry was FORGOTTEN, so the next routine of that
chat spawns a fresh `pi`.

The second half of the claim is the session file: it **stopped growing at 58 399 B**, and its last
write is at 16:42:14Z — **before** the ceiling (16:42:31Z). The old defect answered at the
ceiling and kept writing for three minutes; here nothing is written after the clock runs out. The
agent's MCP server (`owner-mcp.mjs`, the `ask` tool) dies with it: no orphan is left holding the
port.

**HOW THE AGENT WAS COUNTED, AND WHY THE FIRST TWO COUNTS PROVED NOTHING.** The needle was wrong
twice, and both times the counter read the wrong thing. The first count looked for `--mode rpc`
in `/proc/<pid>/cmdline` and **counted the probe itself** — the probe's own source carried the
literal in its argv, so the counter read 1 before, 1 during and 1 after, and proved nothing. The
second count looked for `pi-coding-agent`, which is **never** in the cmdline: the agent rewrites
its `process.title`, so `/proc/<pid>/cmdline` reads exactly `pi`. The needle that works is the
agent's own title, and the probe skips its own pid besides. A counter that counts itself is worse
than no counter: it looks like a measurement.

**WHAT ELSE THE CADENCE HAD TO GET RIGHT, MEASURED BEFORE THE RUN.** Three things were measured
on the box on 2026-11-10, before the 22:00 run, because a run nobody watches cannot be corrected
once it is over:

- **The search the note rests on.** `search_artifacts` with `kinds=(tarefa,)` and the quarter
  returns **0** rows — the store holds no `tarefa` alive. The quarter's work is in the kinds
  that carry it: with `kinds=(tarefa, fase, plano)` and `quarter=Q4-2026` the search returns
  **7 rows** (5 `fase`, 2 `plano`), one page, under the limit of 20. A search WITHOUT the quarter
  returns every plan in the store (226) and pages. The skill now says so in step 1.
- **The day the note names.** The cadence runs with `message=""`, so the agent has nothing to
  name the day from except the clock — and the clock is UTC, which at 22:00 in −03:00 is already
  the next day. The note in the store (`date: 2026-11-09`, written at 01:31Z = 22:31 local the
  night before) names the **UTC** day, while the bot titles the owner's report with the **local**
  day: two artefacts about the same evening, naming two different days. The bot now says the day
  out loud (`date=run_day(...)`), so the agent does not guess it — and the rule, and why it
  cannot be the owner's day, are in "THE DAY OF THE NOTE" above.
- **The quarter's spelling.** `Q4-2026` — quarter-year. Measured on the box: the 5 `fase`, the 2
  `plano`, the 7 `kpi`, the 5 `okr` and the 1 `revisao` of the period all carry `Q4-2026`, and
  223 of the 226 `plano` carry **no** quarter at all.

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
