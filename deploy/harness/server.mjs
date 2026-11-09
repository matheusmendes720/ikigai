/**
 * The harness: the `pi` agent, behind an HTTP door, with a SQLite memory.
 *
 * WHY THIS EXISTS: the Telegram bot is a CLIENT of the api (ADR-037 D6) and
 * the api speaks our MCP over HTTP (ADR-011). The agent, though, is not a
 * client of anything we publish — it is an external process (`pi`), and `pi`
 * speaks JSONL on its own stdin/stdout (RPC mode). Somebody has to own that
 * pipe and expose it on a socket. That somebody is this file, and it lives
 * in `deploy/` — OUTSIDE `src/` — because the agent is external (ADR-037 D7)
 * and nothing in the published service tree may import it.
 *
 * THE SHAPE:
 *
 *   Telegram ──▶ bot ──▶ api ──▶ harness (this) ──▶ pi (RPC, subprocess)
 *                                  ▲                    │
 *                                  └──── MCP ───────────┘
 *
 * The arrow that matters is the one going BACK: the harness reaches the
 * store through MCP, exactly like any other client. It never opens the
 * database. The harness writes the DOM through `store-write` and reads it
 * through `store-read`, and this file is not in that path.
 *
 * WHY ONE PROCESS PER SESSION: `pi` owns a session (a conversation, a
 * context window, a compaction history). Two Telegram chats are two
 * conversations and cannot share one context. So a session id maps to one
 * `pi` process, and the process is pinned to that session with
 * `--session-id`, which is what makes it survive a restart of this service.
 *
 * WHY THE ROUTINES ARE READ FROM THE DISK AND NOT WRITTEN HERE: the
 * whitelist of routines is the PUBLISHED projection
 * (`specs/harness/skills/<id>/SKILL.md`). The container copies that
 * projection into `.pi/skills/`, and this file reads the same directory to
 * know what exists. A routine that is not in the projection does not run —
 * the harness fails closed, the same way the bot fails closed without
 * `IKIGAI_BOT_ALLOWED_CHAT_IDS`.
 */

import { createServer } from "node:http";
import { existsSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { RpcClient } from "@earendil-works/pi-coding-agent";
import { Memory } from "./memory.mjs";
import { Owner } from "./owner.mjs";
import {
  DEFAULT_RUNTIME_ID,
  buildRegistry,
  describeRuntime,
  readRegistryConfig,
  routeClient,
} from "./runtimes.mjs";

// ── configuration ────────────────────────────────────────────────────────────
// Everything is an environment variable: this file ships in a container and a
// secret never lives in a file (the house rule, and ADR-037's contract C-5).

const PORT = Number(process.env.HARNESS_PORT || 8002);
const HOST = process.env.HARNESS_HOST || "0.0.0.0";
const PI_CLI = process.env.PI_CLI_PATH || "";
const PI_CWD = process.env.HARNESS_CWD || "/app";
const PI_SESSION_DIR = process.env.PI_SESSION_DIR || "/root/.pi/agent/sessions";
const PI_SKILLS_DIR = process.env.PI_SKILLS_DIR || "/app/.pi/skills";
const ROUTINES_DIR = process.env.HARNESS_ROUTINES_DIR || "/app/specs/harness/skills";
const MEMORY_DB = process.env.HARNESS_MEMORY_DB || "/app/memory/memory.sqlite";
const MAX_SESSIONS = Number(process.env.HARNESS_MAX_SESSIONS || 8);
const SESSION_TTL_MS = Number(process.env.HARNESS_SESSION_TTL_MS || 15 * 60 * 1000);
// The ceiling of ONE question to the owner. It is longer than a routine's
// poll window and shorter than the patience of a person who forgot they were
// being asked.
const OWNER_TIMEOUT_MS = Number(process.env.HARNESS_OWNER_TIMEOUT_MS || 15 * 60 * 1000);
// THE CEILING OF ONE ROUTINE — DERIVED from the question's ceiling.
//
// WHY DERIVED: a routine that asks the owner WAITS for the answer; the agent
// is SUSPENDED on the question (see `owner.mjs`). So the run has to be able
// to OUTLIVE the question, or the run dies while the owner is still reading.
// Measured on the box (2026-11-09): with the run's ceiling at 10 min and the
// question's at 15 min, NO routine that asked a question could ever finish —
// the run was killed by its own ceiling.
const RUN_TIMEOUT_MS = Number(process.env.HARNESS_TIMEOUT_MS || OWNER_TIMEOUT_MS + 5 * 60 * 1000);
// The margin between the run's ceiling and the SERVER's patience.
//
// WHAT THIS IS NOT: a fix for the 300 s that killed the monthly review on
// 2026-11-09. That 300 s came from the CALLER — the isolation (same handler,
// same 310 s delay, on the box's own Node 24) shows the response arriving at
// 310 s against a server with Node's default `requestTimeout`, and dying at
// 301 s against `fetch`, whose undici default `headersTimeout` is 300 s.
//
// WHAT THIS IS: the server declares its own patience, derived from the run it
// is allowed to take, so the order of the product's ceilings is stated in the
// product instead of inherited from a runtime's defaults.
const REQUEST_MARGIN_MS = Number(process.env.HARNESS_REQUEST_MARGIN_MS || 60 * 1000);
// The routing table: which agentic runtime serves which client. A file is
// the readable form; the environment variable is the one-shot form.
const RUNTIMES_FILE = String(process.env.HARNESS_RUNTIMES_FILE || "").trim();

// A model override, when the container should not use whatever the host had.
// The vocabulary is ONE: `HARNESS_PROVIDER_ID` and `HARNESS_MODEL_ID` are the
// names the entrypoint writes into the provider catalog, so the agent and the
// catalog cannot drift apart.
const PI_MODEL = process.env.HARNESS_MODEL_ID || "";
const PI_PROVIDER = process.env.HARNESS_PROVIDER_ID || "";

// ── the fallback ─────────────────────────────────────────────────────────────
// When the primary provider refuses, the routine is retried on a second one.
//
// WHY IT LIVES HERE AND NOT IN A VIRTUAL MODEL: `pi` supports model fallback
// through `virtual-models` — `route(request)` receives `request.failed` and may
// dispatch the retry to another model — but virtual models are registered by
// an EXTENSION, and this harness runs `--no-extensions` on purpose (RpcClient
// does not implement the `extension_ui` sub-protocol, so an extension that
// opens a dialog blocks the agent forever). So the retry is ours.
//
// WHAT A FAILURE LOOKS LIKE, measured on the box against a quota-exhausted
// provider: `promptAndWait` does NOT throw. It returns the event stream, and
// the assistant message carries `stopReason: "error"` with an `errorMessage`
// holding the provider's answer ("429 {… rate_limit_error …}"). The text is
// empty, so the routine used to report `ok: true` with nothing in it — a
// green answer for a request that never reached a model.
const FALLBACK_PROVIDER = process.env.HARNESS_FALLBACK_PROVIDER || "deepseek";
// The API ID, not the catalogue name. DeepSeek's own `/models` lists
// `deepseek-flash` and `deepseek-v4-pro`; asking for `deepseek-v4.1-flash` —
// the name pi's bundled catalogue uses for the same tier — returns
// 400 "The supported API model names are deepseek-flash, deepseek-v4-pro".
// Measured on the box, so the default here is the one the API accepts.
const FALLBACK_MODEL = process.env.HARNESS_FALLBACK_MODEL || "deepseek-flash";
// The codes that mean "the provider refused", not "the request was wrong".
// A 400 or a 401 is a configuration problem: retrying it elsewhere hides the
// mistake and costs a second round trip.
const FALLBACK_ON = String(process.env.HARNESS_FALLBACK_ON || "429,500,502,503,504,timeout")
  .split(",")
  .map((s) => s.trim().toLowerCase())
  .filter(Boolean);

const memory = new Memory(MEMORY_DB);

/**
 * The owner: the questions the agent asks, and the answers that unblock it.
 *
 * The broker is the WAITING ROOM (see `owner.mjs`). It lives here, in the
 * runtime, because the agent is suspended on the question: a question that
 * lived in the bot would die with the bot, and the agent would keep waiting
 * for an answer that nobody could give.
 */
const owner = new Owner({ memory, defaultTimeoutMs: OWNER_TIMEOUT_MS });

/**
 * The runtime registry.
 *
 * It is READ FROM THE ENVIRONMENT, and it is re-read when the file it comes
 * from changes: a routing table that needs a container restart to be edited
 * is a routing table that stops being edited. The mtime is the cheap test —
 * one stat per lookup, and a lookup happens once per client per routing call.
 */
let registry = null;
let registryStamp = "";

function currentRegistry() {
  const file = String(process.env.HARNESS_RUNTIMES_FILE || "").trim();
  let stamp = "";
  if (file) {
    try {
      stamp = `${file}:${statSync(file).mtimeMs}`;
    } catch {
      stamp = `${file}:missing`;
    }
  } else {
    stamp = `inline:${String(process.env.HARNESS_RUNTIMES || "").length}`;
  }
  if (registry && stamp === registryStamp) return registry;

  const { config, error } = readRegistryConfig(process.env);
  const built = buildRegistry({ env: process.env, config });
  if (error) built.problems.push(error);
  registry = built;
  registryStamp = stamp;
  return registry;
}

// ── the routines ─────────────────────────────────────────────────────────────

/**
 * The routines are the skills present in the projection. Reading them from the
 * disk is the point: the list is never written twice.
 */
function loadRoutines() {
  if (!existsSync(ROUTINES_DIR)) return new Map();
  const out = new Map();
  for (const entry of readdirSync(ROUTINES_DIR, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const skill = join(ROUTINES_DIR, entry.name, "SKILL.md");
    if (!existsSync(skill)) continue;
    out.set(entry.name, {
      id: entry.name,
      skill: skill,
      bytes: statSync(skill).size,
    });
  }
  return out;
}

let routines = loadRoutines();

// ── the pi processes ─────────────────────────────────────────────────────────

/** session id -> { client, routine, lastUsed, chain } */
const sessions = new Map();

/**
 * The flags that decide WHICH provider the agent talks to.
 *
 * ONE resolution, ONE helper, BOTH callers:
 *
 *     explicit → the routed runtime → the DEFAULT runtime of the table → the
 *     environment
 *
 * The routines and the readiness probe must agree on it. Measured on the box
 * (2026-11-09): with two providers in the catalogue, a probe that spawns the
 * agent WITHOUT `--provider`/`--model` gets pi's OWN default — the fallback —
 * and reports it as the model the container is on. The container was "healthy"
 * on the strength of the provider of reserve, while the routines were
 * configured for another one, and nothing said so.
 *
 * A probe that carries its own list of flags is exactly how they drifted the
 * first time. So: the probe asks for the DEFAULT RUNTIME — what a routine
 * gets when no client rule applies — and the routines pass the runtime the
 * routing table gave them.
 */
function providerArgs({ provider, model } = {}) {
  const registry = currentRegistry();
  const fallback = registry?.runtimes?.get(registry.default);
  const args = [];
  const chosenModel = model || fallback?.model || PI_MODEL;
  const chosenProvider = provider || fallback?.provider || PI_PROVIDER;
  if (chosenModel) args.push("--model", chosenModel);
  if (chosenProvider) args.push("--provider", chosenProvider);
  return args;
}

function piArgs(sessionId, { provider, model } = {}) {
  const args = [
    "--mode",
    "rpc",
    "--session-dir",
    PI_SESSION_DIR,
    "--session-id",
    sessionId,
    // Extensions are OFF on purpose. `RpcClient` does not implement the
    // `extension_ui` sub-protocol, so an extension that opens a dialog would
    // block the agent forever with nobody to answer it. The MCP client is
    // CORE (not an extension), so the harness keeps its way into the store.
    "--no-extensions",
    // The project configuration (`.pi/mcp.json`, `.pi/skills/`) is only read
    // after the project is trusted. Without this, the harness would start
    // with no store to talk to — and would fail with a message that says
    // nothing about the cause.
    "--approve",
  ];
  return [...args, ...providerArgs({ provider, model })];
}

/**
 * Did the turn reach a model at all?
 *
 * The agent reports a provider refusal as an ASSISTANT MESSAGE with
 * `stopReason: "error"` — not as a thrown error, and not as a failed exit.
 * Measured with a quota-exhausted key: `promptAndWait` resolved with 36 events,
 * the text was empty, and the only evidence was
 * `{"stopReason":"error","errorMessage":"429 {…}"}` on the message.
 *
 * Returns `null` when the last assistant message finished normally, so a
 * caller can tell "the model answered nothing" (a real, if unhelpful, answer)
 * from "the model never ran".
 */
function lastAssistantFailure(events) {
  let last = null;
  for (const event of events || []) {
    const message = event && event.message;
    if (message && message.role === "assistant") last = message;
  }
  if (!last) return null;
  const stop = String(last.stopReason || "");
  if (!stop || stop === "stop" || stop === "end_turn" || stop === "tool_use") return null;
  return {
    stopReason: stop,
    errorMessage: String(last.errorMessage || ""),
    provider: String(last.provider || ""),
    model: String(last.model || ""),
  };
}

/**
 * Is this refusal worth retrying on another provider?
 *
 * `codes` carries both HTTP codes ("429") and the word "timeout". Anything
 * else — a 400, a 401, a tool error — is NOT retried: a wrong request is
 * wrong everywhere, and a masked 401 sends the reader to the wrong place.
 */
function isFallbackTrigger(errorMessage, codes) {
  const text = String(errorMessage || "").toLowerCase();
  if (!text) return false;
  for (const code of codes) {
    if (code === "timeout") {
      if (text.includes("timeout") || text.includes("timed out")) return true;
      continue;
    }
    // A three-digit code has to appear as a token: searching for "429" inside
    // a request id would fire on a healthy response.
    if (new RegExp(`(^|[^0-9])${code}([^0-9]|$)`).test(text)) return true;
  }
  return false;
}

/**
 * The session id has to survive TWO vocabularies.
 *
 * `pi` refuses a session id that is not made of alphanumerics, `-`, `_` and
 * `.`, and that does not start and end with an alphanumeric — so a chat key
 * like `tg:9138296750` kills the agent on the first prompt (measured: exit 1,
 * "Session id must be non-empty, contain only alphanumeric characters, '-',
 * '_', and '.'"). The caller sends whatever it has (a Telegram chat id, a
 * thread id, a composite key), so the id is SANITISED here, once, and the
 * same value is used for the agent AND for the memory: one session, one key.
 */
function sanitiseSessionId(raw) {
  const trimmed = String(raw ?? "")
    .replace(/[^A-Za-z0-9._-]/g, "-")
    .replace(/^[^A-Za-z0-9]+/, "")
    .replace(/[^A-Za-z0-9]+$/, "");
  return trimmed || "session";
}

async function spawnPi(sessionId, opts) {
  const client = new RpcClient({
    cliPath: PI_CLI || undefined,
    cwd: PI_CWD,
    args: piArgs(sessionId, opts),
    // The session id travels to the agent's CHILDREN as well.
    //
    // The `ask` tool is an MCP server, and MCP servers are spawned by the
    // agent — so the server that asks the owner a question is a grandchild
    // of this process. It needs to know WHICH session is asking, or the
    // question goes to the wrong conversation. The environment is the
    // carrier: the agent inherits it (the SDK merges, it does not replace —
    // `env: { ...process.env, ...this.options.env }`), and the MCP server
    // reads it from its own.
    env: { ...(opts?.env || {}), IKIGAI_SESSION_ID: sessionId },
  });
  await client.start();
  return client;
}

/**
 * The session entry.
 *
 * `runtime` is part of it, and it is part of it because the runtime decides
 * the MODEL and the ROUTINES. A client re-routed to another runtime gets
 * another `pi` process — the old one is released, and the conversation
 * continues in the new profile with the same session id, because the session
 * id is the CONVERSATION and the runtime is the MACHINE that holds it.
 */
async function acquire(sessionId, runtime) {
  const live = sessions.get(sessionId);
  if (live) {
    // A session whose runtime changed is a different machine for the same
    // conversation: the old process is released and a new one is spawned.
    if (runtime && live.runtime !== runtime.id) {
      await release(sessionId);
    } else {
      live.lastUsed = Date.now();
      return live;
    }
  }
  if (sessions.size >= MAX_SESSIONS) {
    // The oldest idle session gives its slot. A session in use is never
    // evicted: killing a running agent loses the turn it is in the middle of.
    let oldest = null;
    for (const [id, s] of sessions) {
      if (s.turns > 0) continue;
      if (!oldest || s.lastUsed < oldest.lastUsed) oldest = { id, s };
    }
    if (!oldest) {
      throw Object.assign(new Error("harness is at capacity"), { status: 503 });
    }
    await release(oldest.id);
  }
  const client = await spawnPi(sessionId, {
    // The ROUTED runtime's provider, if the routing table gave one. The rest
    // of the chain — the default runtime, then the environment — is resolved
    // by `providerArgs()`, the same helper the readiness probe uses.
    provider: runtime?.provider,
    model: runtime?.model,
  });
  const entry = {
    client,
    routine: "",
    lastUsed: Date.now(),
    // THE TURNS IN FLIGHT, COUNTED — not a flag.
    //
    // WHY A COUNTER: a request that is REFUSED (the agent is busy with another
    // turn) must not clear the mark of the turn that is actually running. With
    // a flag, the refused request's `finally` cleared it, the reaper saw an
    // idle session, and it KILLED a live agent mid-write.
    //
    // Measured on the box (2026-11-09): the quarterly-plan's refusal cleared
    // the monthly-review's flag at 20:26:59Z, and the reaper killed the agent
    // at 20:41:59Z — the agent was writing at 20:41:53Z. The routine's work
    // was lost and nobody was told.
    turns: 0,
    chain: Promise.resolve(),
    runtime: runtime?.id || DEFAULT_RUNTIME_ID,
  };
  sessions.set(sessionId, entry);
  return entry;
}

async function release(sessionId) {
  const entry = sessions.get(sessionId);
  if (!entry) return;
  sessions.delete(sessionId);
  try {
    await entry.client.stop();
  } catch {
    /* the process is already gone; nothing to close */
  }
}

async function reapIdle() {
  const now = Date.now();
  for (const [id, s] of [...sessions]) {
    if (s.turns === 0 && now - s.lastUsed > SESSION_TTL_MS) await release(id);
  }
}

/**
 * Repeat the turn on the secondary provider, in the SAME session.
 *
 * The primary client is stopped first and only then the secondary is spawned:
 * two `pi` processes must never write the same session file. The session id is
 * kept, so the conversation continues where it was — `pi` names the physical
 * model on every assistant message, which is what makes a mid-conversation
 * provider switch legal (models.md: replaying across models works like a
 * manual switch).
 *
 * Returns `{ ok, text, events, error }` and never throws: the caller decides
 * what a failed fallback means.
 */
async function runOnFallback(sessionId, prompt, timeout, refusal) {
  await release(sessionId);
  let client = null;
  try {
    client = await spawnPi(sessionId, {
      provider: FALLBACK_PROVIDER,
      model: FALLBACK_MODEL,
    });
    const events = await client.promptAndWait(prompt, undefined, timeout);
    const text = (await client.getLastAssistantText()) || textFromEvents(events);
    const again = lastAssistantFailure(events);
    if (again) {
      return {
        ok: false,
        events,
        error: `${again.stopReason}: ${again.errorMessage}`,
        refusal,
      };
    }
    if (!text) {
      return { ok: false, events, error: "the fallback answered with no text", refusal };
    }
    return { ok: true, events, text, refusal };
  } catch (err) {
    return {
      ok: false,
      events: [],
      error: err && err.message ? err.message : String(err),
      refusal,
    };
  } finally {
    if (client) {
      try {
        await client.stop();
      } catch {
        /* the process is already gone */
      }
    }
  }
}

// ── the run ──────────────────────────────────────────────────────────────────

function buildPrompt(routine, payload) {
  // `/skill:<id>` is pi's FORCED invocation of a skill: without it, the model
  // decides whether the description matches, and a routine that must run now
  // can be "not quite applicable". The routine is a decision the owner made.
  const context = {
    session_id: payload.session_id,
    chat_id: payload.chat_id,
    date: payload.date,
    now: payload.now,
    ...(payload.context || {}),
  };
  const parts = [`/skill:${routine}`];
  if (payload.message) parts.push(String(payload.message));
  parts.push("Contexto da sessao (JSON):");
  parts.push(JSON.stringify(context, null, 2));
  return parts.join("\n\n");
}

function textFromEvents(events) {
  let out = "";
  for (const ev of events || []) {
    if (ev && ev.type === "message_update" && ev.assistantMessageEvent) {
      const inner = ev.assistantMessageEvent;
      if (inner.type === "text_delta" && inner.delta) out += inner.delta;
    }
  }
  return out;
}

async function runRoutine({ routine, session_id, chat_id, client, message, context, date, timeout_ms }) {
  if (!routines.has(routine)) {
    throw Object.assign(
      new Error(`unknown routine: ${routine}`),
      { status: 400, detail: `known routines: ${[...routines.keys()].join(", ")}` },
    );
  }

  // THE ROUTING: the client is not the agent. The client is routed to a
  // runtime — a profile with its own model, its own routines and its own
  // memory — and the runtime is what answers.
  const registry = currentRegistry();
  const clientKey = String(client || (chat_id ? `tg:${chat_id}` : session_id || ""));
  const routed = routeClient(registry, clientKey);
  const runtime = routed.runtime;

  // A runtime that may not run this routine says so, and says WHICH
  // routines it may run: a refusal that names the alternatives is a
  // sentence the owner can act on.
  if (Array.isArray(runtime.routines) && !runtime.routines.includes(routine)) {
    throw Object.assign(
      new Error(`the runtime "${runtime.id}" does not run ${routine}`),
      { status: 403, detail: `this runtime runs: ${runtime.routines.join(", ") || "nothing"}` },
    );
  }

  const sessionId = sanitiseSessionId(session_id || `anon-${chat_id || "0"}`);
  const started = Date.now();
  // The ceiling of THIS run. A caller may ask for LESS (the harness's own
  // ceiling is the most the socket can hold), never for more: a run that
  // outlives the socket is a run whose answer nobody receives — the work
  // lands in the store and the caller hears nothing.
  const timeout = Math.min(Number(timeout_ms) || RUN_TIMEOUT_MS, RUN_TIMEOUT_MS);

  const entry = await acquire(sessionId, runtime);
  // THE TURN IS COUNTED, not flagged: a request that is REFUSED must not
  // release the mark of the turn that is running (see the counter's note in
  // `acquire`).
  entry.turns += 1;
  entry.lastUsed = Date.now();
  try {
    const prompt = buildPrompt(routine, {
      session_id: sessionId,
      chat_id,
      message,
      context,
      date,
      now: new Date().toISOString(),
    });

    memory.beginSession(sessionId, { routine });
    memory.logEvent({
      kind: "routine.started",
      key: routine,
      session: sessionId,
      payload: { chat_id, date, runtime: runtime.id, client: clientKey },
    });

    let events = [];
    let text = "";
    let failure = null;
    let fellBack = null;
    try {
      events = await entry.client.promptAndWait(prompt, undefined, timeout);
      text = (await entry.client.getLastAssistantText()) || textFromEvents(events);
    } catch (err) {
      failure = err && err.message ? err.message : String(err);
    }

    // A provider refusal is NOT a thrown error: the turn ends with an assistant
    // message carrying `stopReason: "error"`. Without this check the routine
    // answered `ok: true` with an empty text — the green lie, in the one place
    // the owner reads the agent's work.
    let refusal = failure ? null : lastAssistantFailure(events);

    if (!failure && refusal && isFallbackTrigger(refusal.errorMessage, FALLBACK_ON)) {
      memory.logEvent({
        kind: "routine.fallback",
        key: routine,
        session: sessionId,
        payload: {
          from: `${refusal.provider}/${refusal.model}`,
          to: `${FALLBACK_PROVIDER}/${FALLBACK_MODEL}`,
          reason: refusal.errorMessage.slice(0, 300),
        },
      });
      const second = await runOnFallback(sessionId, prompt, timeout, refusal);
      if (second.ok) {
        events = second.events;
        text = second.text;
        fellBack = {
          provider: FALLBACK_PROVIDER,
          model: FALLBACK_MODEL,
          primary_error: refusal.errorMessage.slice(0, 300),
        };
        refusal = null;
      } else {
        failure =
          `the primary provider refused (${refusal.errorMessage.slice(0, 200)}) ` +
          `and the fallback ${FALLBACK_PROVIDER}/${FALLBACK_MODEL} failed: ${second.error}`;
      }
    } else if (!failure && refusal) {
      // Not a trigger: a 400 or a 401 is a wrong request or a wrong key, and
      // repeating it elsewhere would hide the cause and cost a second call.
      failure = `the provider refused: ${refusal.stopReason}: ${refusal.errorMessage.slice(0, 300)}`;
    }

    if (failure) {
      memory.logEvent({
        kind: "routine.failed",
        key: routine,
        session: sessionId,
        payload: { error: failure },
      });
      throw Object.assign(new Error(`the routine failed: ${failure}`), { status: 502 });
    }

    // The memory: what the agent said, and what it was asked. The DOM stays
    // canonical — if the routine wrote artifacts, it wrote them through MCP.
    const wrote = memory.remember({
      kind: "routine",
      key: routine,
      content: text,
      status: "ok",
      source: `telegram:${chat_id ?? "?"}`,
      session: sessionId,
      confidence: 1.0,
    });
    memory.logEvent({
      kind: "routine.finished",
      key: routine,
      session: sessionId,
      payload: { chat_id, bytes: text.length, entry_id: wrote.id, fell_back: fellBack },
    });

    return {
      ok: true,
      routine,
      session_id: sessionId,
      // Which runtime answered — so the client can say "the archive model
      // answered" and not present it as the primary's work.
      runtime: runtime.id,
      client: clientKey,
      text,
      bytes: text.length,
      events: (events || []).length,
      // Present only when the answer came from the secondary provider, so the
      // bot can say so instead of presenting it as the primary's work.
      fell_back: fellBack,
      memory_entry_id: wrote.id,
      duration_ms: Date.now() - started,
    };
  } finally {
    entry.turns = Math.max(0, entry.turns - 1);
    entry.lastUsed = Date.now();
  }
}

// ── the api ──────────────────────────────────────────────────────────────────

function json(res, status, body) {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    "content-type": "application/json; charset=utf-8",
    "content-length": Buffer.byteLength(payload),
  });
  res.end(payload);
}

async function readBody(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  if (!chunks.length) return {};
  const raw = Buffer.concat(chunks).toString("utf8");
  try {
    return JSON.parse(raw);
  } catch {
    throw Object.assign(new Error("body is not JSON"), { status: 400 });
  }
}

/**
 * The shallow probe: this process is alive and the memory answers.
 */
function health() {
  let memoryOk = false;
  let memoryDetail = null;
  try {
    memory.db.prepare("SELECT COUNT(*) AS n FROM sessions").get();
    memoryOk = true;
  } catch (err) {
    memoryDetail = err.message;
  }
  const registry = currentRegistry();
  return {
    ok: memoryOk,
    service: "ikigai-harness",
    pi: {
      cli: PI_CLI,
      skills_dir: PI_SKILLS_DIR,
      routines: routines.size,
      live_sessions: sessions.size,
      busy_sessions: [...sessions.values()].filter((s) => s.turns > 0).length,
    },
    // The routing table, as the harness sees it. A deployment that routes
    // two clients to two runtimes can SEE that it does.
    runtimes: {
      default: registry.default,
      count: registry.runtimes.size,
      clients: registry.clients.size,
      problems: registry.problems,
    },
    memory: memoryOk ? memory.stats() : { error: memoryDetail },
  };
}

/**
 * The deep probe: `pi` really starts and really answers.
 *
 * This is the data plane, not the surface: a socket that returns bytes is
 * not health (contract C-2). So the probe spawns a `pi`, asks it for its
 * state, and checks that a model came back. A container that cannot do that
 * cannot run a routine, and saying so is the whole point of the probe.
 *
 * AND IT MEASURES THE SAME PROVIDER THE ROUTINES USE — `providerArgs()`, the
 * same helper `piArgs()` uses. Measured on the box (2026-11-09): the probe
 * used to spawn the agent WITHOUT the provider flags, so it got pi's own
 * default (the fallback) and reported `provider: deepseek` while the routines
 * ran on `harness`/MiniMax. The container was healthy on the strength of the
 * provider of reserve, and the healthcheck — which reads this probe — said
 * nothing about the primary.
 *
 * It does NOT authenticate: the probe asks for the agent's state, not for a
 * model to answer, so it costs no tokens. What it certifies is "the path the
 * routines take is configured and starts" — not "the provider is serving".
 */
async function ready() {
  const started = Date.now();
  let client = null;
  try {
    client = new RpcClient({
      cliPath: PI_CLI || undefined,
      cwd: PI_CWD,
      args: ["--mode", "rpc", "--no-session", "--no-extensions", ...providerArgs()],
    });
    await client.start();
    const state = await client.getState();
    return {
      ok: Boolean(state && state.model && state.model.id),
      service: "ikigai-harness",
      model: state?.model?.id ?? null,
      provider: state?.model?.provider ?? null,
      context_window: state?.model?.contextWindow ?? null,
      routines: routines.size,
      duration_ms: Date.now() - started,
    };
  } catch (err) {
    return {
      ok: false,
      service: "ikigai-harness",
      error: err && err.message ? err.message : String(err),
      duration_ms: Date.now() - started,
    };
  } finally {
    if (client) {
      try {
        await client.stop();
      } catch {
        /* nothing to close */
      }
    }
  }
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || "localhost"}`);
  try {
    if (req.method === "GET" && url.pathname === "/v1/health") {
      return json(res, 200, health());
    }
    if (req.method === "GET" && url.pathname === "/v1/ready") {
      const body = await ready();
      return json(res, body.ok ? 200 : 503, body);
    }
    if (req.method === "GET" && url.pathname === "/v1/routines") {
      return json(res, 200, { routines: [...routines.values()] });
    }
    if (req.method === "GET" && url.pathname === "/v1/memory") {
      // The session key is SANITISED on the way in and on the way out, so the
      // caller may send the raw key it has (a Telegram chat id, a composite)
      // and still find what the harness wrote.
      const session = url.searchParams.get("session")
        ? sanitiseSessionId(url.searchParams.get("session"))
        : "";
      const kind = url.searchParams.get("kind") || "";
      const limit = Number(url.searchParams.get("limit") || 50);
      return json(res, 200, {
        session_id: session || null,
        entries: memory.recall({ session, kind, limit }),
        events: memory.events({ session, limit: 100 }),
      });
    }
    if (req.method === "GET" && url.pathname === "/v1/runtimes") {
      const registry = currentRegistry();
      return json(res, 200, {
        default: registry.default,
        runtimes: [...registry.runtimes.values()].map((runtime) =>
          describeRuntime(runtime, [...routines.keys()]),
        ),
        // What was REFUSED, and why. A routing table that refuses something
        // quietly is a routing table the operator cannot fix.
        problems: registry.problems,
      });
    }
    if (req.method === "GET" && url.pathname === "/v1/routing") {
      // The routing answer for one client: which runtime answers it, and
      // whether that was a RULE or the default.
      const registry = currentRegistry();
      const client = String(url.searchParams.get("client") || "");
      const routed = routeClient(registry, client);
      return json(res, 200, {
        client: routed.client,
        runtime: describeRuntime(routed.runtime, [...routines.keys()]),
        routed: routed.routed,
        reason: routed.reason,
        session_id: sanitiseSessionId(client || "anon-0"),
        problems: registry.problems,
      });
    }
    if (req.method === "GET" && url.pathname === "/v1/session") {
      // The session of one client: its id, its runtime, and the questions
      // that are still open. The client polls this to know what it missed
      // after a restart.
      const registry = currentRegistry();
      const client = String(url.searchParams.get("client") || "");
      const routed = routeClient(registry, client);
      const sessionId = sanitiseSessionId(client || "anon-0");
      return json(res, 200, {
        client,
        session_id: sessionId,
        runtime: describeRuntime(routed.runtime, [...routines.keys()]),
        questions: owner.pending(sessionId),
      });
    }
    if (req.method === "GET" && url.pathname === "/v1/events") {
      // The agent's own event log, FORWARD, from a cursor — the same shape
      // as the store's change feed (ADR-039): the client sends what it has
      // and gets what it does not, in order.
      //
      // The session is SANITISED here, so the client may send the key it
      // knows (`tg:9138296750`) or the session id it was given
      // (`tg-9138296750`) — the two are the same conversation, and the
      // client should not have to know which spelling the agent's id rules
      // want.
      const raw = String(url.searchParams.get("session") || "");
      const session = raw ? sanitiseSessionId(raw) : "";
      const since = Number(url.searchParams.get("since") || 0);
      const limit = Number(url.searchParams.get("limit") || 200);
      const page = memory.eventsSince({ session, since, limit });
      return json(res, 200, { session_id: session || null, ...page });
    }
    if (req.method === "POST" && url.pathname === "/v1/owner/ask") {
      // The agent asked the owner something. The question is REGISTERED here
      // and the waiting happens in the caller's tool call — so a question
      // that outlives its asker is still answerable.
      const body = await readBody(req);
      const asked = owner.ask({
        session: String(body.session || ""),
        client: String(body.client || ""),
        question: body.question,
        options: body.options,
        kind: body.kind,
        timeoutMs: body.timeout_ms,
      });
      if (!asked.ok) {
        return json(res, 400, { ok: false, error: asked.error });
      }
      return json(res, 200, { ok: true, question: asked.question });
    }
    if (req.method === "GET" && url.pathname === "/v1/owner/answer") {
      // The state of one question, as the WAITING tool call sees it.
      const questionId = String(url.searchParams.get("question_id") || "");
      const answer = owner.read(questionId);
      if (!answer.ok) return json(res, 404, { ok: false, error: answer.error });
      return json(res, 200, {
        ok: true,
        state: answer.state,
        value: answer.value,
        question: answer.question,
      });
    }
    if (req.method === "POST" && url.pathname === "/v1/owner/answer") {
      // The owner's answer. It unblocks the agent's suspended tool call.
      //
      // It arrives either as TEXT (a free-form answer the owner typed) or as
      // an INDEX (the option the owner picked — the index is what travels
      // through a channel with a 64-byte button payload, and the TEXT of the
      // option comes from here, from the question the runtime asked).
      const body = await readBody(req);
      const answer = owner.answer(
        String(body.question_id || ""),
        body.value ?? null,
        body.option_index ?? null,
      );
      if (!answer.ok) {
        return json(res, 409, { ok: false, error: answer.error });
      }
      return json(res, 200, { ok: true, question: answer.question });
    }
    if (req.method === "POST" && url.pathname === "/v1/routine") {
      const body = await readBody(req);
      const out = await runRoutine({
        routine: String(body.routine || ""),
        session_id: body.session_id,
        chat_id: body.chat_id,
        client: body.client,
        message: body.message,
        context: body.context,
        date: body.date,
        timeout_ms: body.timeout_ms,
      });
      return json(res, 200, out);
    }
    return json(res, 404, { ok: false, error: "not found" });
  } catch (err) {
    const status = err && err.status ? err.status : 500;
    return json(res, status, {
      ok: false,
      error: err && err.message ? err.message : String(err),
      detail: err && err.detail ? err.detail : undefined,
    });
  }
});

// THE SERVER'S PATIENCE.
//
// Declared, and derived from the run: the server must not be able to cut a
// run that its own ceiling allows. Node's `requestTimeout` (300 s by default)
// governs the RECEIVING of the request, not the sending of the response —
// measured on the box (2026-11-09), the response arrives at 310 s against a
// server with the default. So this is not a patch for the 300 s that killed a
// run; it is the product stating the order of its own ceilings instead of
// inheriting them from a runtime's defaults.
server.requestTimeout = RUN_TIMEOUT_MS + REQUEST_MARGIN_MS;

const timer = setInterval(() => {
  reapIdle().catch(() => {});
}, 60_000);
timer.unref();

server.listen(PORT, HOST, () => {
  process.stdout.write(
    `[harness] listening on ${HOST}:${PORT} · routines=${routines.size} · memory=${MEMORY_DB}\n`,
  );
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, async () => {
    server.close();
    for (const id of [...sessions.keys()]) await release(id);
    memory.close();
    process.exit(0);
  });
}
