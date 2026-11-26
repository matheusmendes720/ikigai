# AGENTS.md — `src/bot/`

**Score 12 (11 Python modules + the Mini App page, ~4 800 LOC) — distinct domain: the Telegram projection of the DOM.** It is a client, never a second writer.

## OVERVIEW
The Telegram client, its Mini App, and the small modules that project the
DOM to an owner who lives in a chat. It reaches the system through three
doors — MCP (the DOM), the websocket (the store's changes), and harness HTTP
(the external agent, ADR-037 D7) — and it never opens a database.

## WHERE TO LOOK
| Item | Where |
|---|---|
| The bot itself | `main.py` — `Bot` (~50 methods), `McpClient`, `ROUTINES`, the routine lifecycle, the cadence loop (2022 lines; the only file that touches every other module) |
| Intent routing | `router.py` — `route()`, `callback_data()`, `parse_callback()`; the routine table is the caller's |
| The daily routine | `cadence.py` — `Cadence`, `cadence_from_env()`, `run_day()` |
| Streaming previews | `draft.py` — `Draft`, `Drafts`, `REFRESH_S` |
| Agent questions as buttons | `channel.py` — `Question`, `question_keyboard()`, `answer_buttons()` |
| Rendering | `rich.py` — `markdown_table()`, `report_markdown()`, `rich_payload()` |
| The websocket client | `ws_client.py` — `WebSocketClient` (call, draft, events, resumable feed) |
| The agent client | `harness_client.py` — `HarnessClient`, `HarnessError` |
| The Mini App | `miniapp/__init__.py` — `create_app()`, `validate_init_data()`; `miniapp/index.html` — the page (vanilla JS, no build step) |
| The surface registry | `surfaces.py` — the only reader of `deploy/surfaces.json` |

## CONVENTIONS
- **Three doors, two interchangeable transports.** `McpClient.call(tool, arguments)` and `WebSocketClient.call(tool, arguments)` are the same shape; `main()` picks the websocket when `IKIGAI_WS_URL` is set. The agent door is optional — the api's surface stays exactly six tools.
- **Fail closed, everywhere.** Empty `IKIGAI_BOT_ALLOWED_CHAT_IDS` → `SystemExit` at boot; a missing or malformed `surfaces.json` → no address, not a crash; an unknown callback payload → "I do not know that button", never an exception in the poll loop.
- **Owner-facing strings are PT-BR; code, docstrings and comments are EN.** The tool docstrings on the api side are PT-BR for the same reason: the calling model reads them.
- **Each module opens with a docstring that states the decision, the why, and the failure it prevents.** That is the house style of this package; a comment explains the rationale, never the what.
- **Constants are named for the limit they encode** — `MAX_MARKDOWN = 32000`, `MAX_COLUMNS = 20`, `REFRESH_S = 20` < `DRAFT_PREVIEW_S = 30`.
- **`expected_revision` is always `None` here**, and every write carries an idempotency key (`{uid}:{body_hash}`); the uid derives from the operation, not from the clock.
- **The cadence is computed from the wall clock** (`Cadence.next_run`, strictly after now) — never a persisted timer, so a restart cannot double-fire. A cadence env var that is set but malformed raises; "off" is spelled `off|none|no|never`.
- **`route()` abstains.** Zero or more than one routine matching returns `None` — abstention, not a coin flip.
- **The websocket feed is ordered.** Sequences at or below the last delivered one are dropped, and live events are buffered while a replay is in flight.

## ANTI-PATTERNS
- **Never open a database from `src/bot/`.** A DB fallback is a second writer (ADR-037 D5); the drift test asserts zero `psycopg|asyncpg|DSN|cursor(` here.
- **Never add a seventh tool to the api's surface** — that is a contract change (ADR-011), not a convenience. The agent is reached from the client, never from the api.
- **Never import the store client (`src/data`) from `src/bot/`.** The bot speaks MCP, the websocket, or harness HTTP — nothing else.
- **Never put option text in a `callback_data` payload.** Telegram caps it at 64 bytes; the option's *index* travels and the runtime holds the text.
- **Never capture the Mini App credential at load.** `var INIT_DATA` and `var START_PARAM` are banned by the page test: the credential is read at the moment of the request, and the SDK is loaded non-async/non-defer, before the page's own script.
- **Never publish a surface whose `auth`, `state`, `mode`, `host` or `port` is unknown, or whose auth is not `telegram-initdata`** (ADR-044). Refusal means *no address*, not a crash.
- **Never let the poll loop die** — a stranger's callback, a closed socket or a malformed frame is answered, not raised. Never cancel a run that already finished (`draft.finished`), and never let a late stop land on the next routine of the same chat (`client_run_id` names the run).

## COMMANDS
```bash
python -m src.bot.main                # the bot; the compose runs it as the `bot` role
ruff check . && ruff format --check .  # in src/bot; CI pins ruff==0.17.3
node --test "test/*.test.mjs"         # the Mini App page guards
cd src/ikigai && poetry run pytest -m "not e2e" -q   # the suite that covers this package
```

## NOTES
- Env contract: `IKIGAI_BOT_TOKEN`, `IKIGAI_BOT_ALLOWED_CHAT_IDS` (required), `IKIGAI_MCP_URL`, `IKIGAI_WS_URL`/`IKIGAI_WS_TOKEN`, `IKIGAI_CLIENT_ID`, `IKIGAI_HARNESS_URL`/`IKIGAI_HARNESS_TIMEOUT_S`, `IKIGAI_MINIAPP_URL`/`IKIGAI_MINIAPP_PORT` (0 = panel off), `IKIGAI_CADENCE_{AT,UTC_OFFSET,TZ,ROUTINE,CHAT_ID}` (unset = no cadence), `IKIGAI_SURFACES_FILE`.
