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
const RUN_TIMEOUT_MS = Number(process.env.HARNESS_TIMEOUT_MS || 10 * 60 * 1000);

// A model override, when the container should not use whatever the host had.
// The vocabulary is ONE: `HARNESS_PROVIDER_ID` and `HARNESS_MODEL_ID` are the
// names the entrypoint writes into the provider catalog, so the agent and the
// catalog cannot drift apart.
const PI_MODEL = process.env.HARNESS_MODEL_ID || "";
const PI_PROVIDER = process.env.HARNESS_PROVIDER_ID || "";

const memory = new Memory(MEMORY_DB);

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

function piArgs(sessionId) {
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
  if (PI_MODEL) args.push("--model", PI_MODEL);
  if (PI_PROVIDER) args.push("--provider", PI_PROVIDER);
  return args;
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

async function spawnPi(sessionId) {
  const client = new RpcClient({
    cliPath: PI_CLI || undefined,
    cwd: PI_CWD,
    args: piArgs(sessionId),
  });
  await client.start();
  return client;
}

async function acquire(sessionId) {
  const live = sessions.get(sessionId);
  if (live) {
    live.lastUsed = Date.now();
    return live;
  }
  if (sessions.size >= MAX_SESSIONS) {
    // The oldest idle session gives its slot. A session in use is never
    // evicted: killing a running agent loses the turn it is in the middle of.
    let oldest = null;
    for (const [id, s] of sessions) {
      if (s.busy) continue;
      if (!oldest || s.lastUsed < oldest.lastUsed) oldest = { id, s };
    }
    if (!oldest) {
      throw Object.assign(new Error("harness is at capacity"), { status: 503 });
    }
    await release(oldest.id);
  }
  const client = await spawnPi(sessionId);
  const entry = { client, routine: "", lastUsed: Date.now(), busy: false, chain: Promise.resolve() };
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
    if (!s.busy && now - s.lastUsed > SESSION_TTL_MS) await release(id);
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

async function runRoutine({ routine, session_id, chat_id, message, context, date, timeout_ms }) {
  if (!routines.has(routine)) {
    throw Object.assign(
      new Error(`unknown routine: ${routine}`),
      { status: 400, detail: `known routines: ${[...routines.keys()].join(", ")}` },
    );
  }
  const sessionId = sanitiseSessionId(session_id || `anon-${chat_id || "0"}`);
  const started = Date.now();
  const timeout = Number(timeout_ms) || RUN_TIMEOUT_MS;

  const entry = await acquire(sessionId);
  entry.busy = true;
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
      payload: { chat_id, date },
    });

    let events = [];
    let text = "";
    let failure = null;
    try {
      events = await entry.client.promptAndWait(prompt, undefined, timeout);
      text = (await entry.client.getLastAssistantText()) || textFromEvents(events);
    } catch (err) {
      failure = err && err.message ? err.message : String(err);
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
      payload: { chat_id, bytes: text.length, entry_id: wrote.id },
    });

    return {
      ok: true,
      routine,
      session_id: sessionId,
      text,
      bytes: text.length,
      events: (events || []).length,
      memory_entry_id: wrote.id,
      duration_ms: Date.now() - started,
    };
  } finally {
    entry.busy = false;
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
  return {
    ok: memoryOk,
    service: "ikigai-harness",
    pi: {
      cli: PI_CLI,
      skills_dir: PI_SKILLS_DIR,
      routines: routines.size,
      live_sessions: sessions.size,
      busy_sessions: [...sessions.values()].filter((s) => s.busy).length,
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
 */
async function ready() {
  const started = Date.now();
  let client = null;
  try {
    client = new RpcClient({
      cliPath: PI_CLI || undefined,
      cwd: PI_CWD,
      args: ["--mode", "rpc", "--no-session", "--no-extensions"],
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
    if (req.method === "POST" && url.pathname === "/v1/routine") {
      const body = await readBody(req);
      const out = await runRoutine({
        routine: String(body.routine || ""),
        session_id: body.session_id,
        chat_id: body.chat_id,
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
