/**
 * The harness's persistent memory — SQLite, and nothing else.
 *
 * WHY SQLite and not the store: the store (Postgres + pgvector) is the DOM,
 * and the DOM is the PRODUCT's state — the artifacts, their revisions and
 * their relations (ADR-037 D4). This file is the AGENT's state: what the
 * harness learned in a session, when it learned it, and the log of what it
 * did. Two different lifetimes, two different owners:
 *
 *   - the store has ONE writer (`src/services/`), and the harness reaches it
 *     ONLY through MCP (`store-read` / `store-write`);
 *   - this database has ONE writer too: this module, inside the harness
 *     container. Nothing else opens it.
 *
 * The consequence is the rule that keeps it honest: the harness NEVER writes
 * the DOM directly. It asks the api through MCP, exactly like every other
 * client. This database is a cache of the agent's own experience, not a
 * second copy of the truth — a stale row here costs a re-read, not a
 * divergence.
 *
 * WHY no vectors here: the api embeds every write it accepts (ADR-037 D4), so
 * the vector index belongs to the store and is served by MCP. A second vector
 * index in the harness would be a second answer to the same question, and the
 * two would drift. Retrieval that needs semantics goes through MCP.
 *
 * The schema follows the house pattern (the same shape the owner's own
 * agent-memory store uses): `entries` is the materialised memory, `events` is
 * the append-only log, `sessions` is the lifecycle.
 *
 * WHAT THIS FILE IS NOT: it is not a domain model and it is not a port of the
 * store. It is a journal with a query surface.
 */

import { createHash } from "node:crypto";
import { DatabaseSync } from "node:sqlite";

const SCHEMA = `
CREATE TABLE IF NOT EXISTS sessions (
    session_id  TEXT PRIMARY KEY,
    routine     TEXT NOT NULL DEFAULT '',
    agent       TEXT NOT NULL DEFAULT '',
    started_at  INTEGER NOT NULL,
    ended_at    INTEGER,
    turns       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS entries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    kind         TEXT NOT NULL,
    key          TEXT NOT NULL DEFAULT '',
    content      TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT '',
    source       TEXT NOT NULL DEFAULT '',
    agent        TEXT NOT NULL DEFAULT '',
    session      TEXT NOT NULL DEFAULT '',
    confidence   REAL NOT NULL DEFAULT 1.0,
    created_at   INTEGER NOT NULL,
    updated_at   INTEGER NOT NULL,
    last_used_at INTEGER,
    uses         INTEGER NOT NULL DEFAULT 0,
    content_hash TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS entries_hash ON entries(content_hash);
CREATE INDEX IF NOT EXISTS entries_session ON entries(session, id);
CREATE INDEX IF NOT EXISTS entries_kind ON entries(kind, id);

CREATE TABLE IF NOT EXISTS events (
    seq     INTEGER PRIMARY KEY AUTOINCREMENT,
    ts      INTEGER NOT NULL,
    kind    TEXT NOT NULL,
    key     TEXT NOT NULL DEFAULT '',
    agent   TEXT NOT NULL DEFAULT '',
    session TEXT NOT NULL DEFAULT '',
    payload TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS events_session ON events(session, seq);
`;

export function hashContent(content) {
  return createHash("sha256").update(content, "utf8").digest("hex");
}

/**
 * The memory. One instance per process; the file is the state.
 */
export class Memory {
  constructor(dbPath) {
    this.dbPath = dbPath;
    this.db = new DatabaseSync(dbPath);
    this.db.exec("PRAGMA journal_mode = WAL;");
    this.db.exec("PRAGMA foreign_keys = ON;");
    this.db.exec(SCHEMA);
  }

  close() {
    try {
      this.db.close();
    } catch {
      /* already closed */
    }
  }

  /**
   * Open (or resume) a session. The session id is the Telegram chat's key:
   * the same chat always resumes the same line of work, across restarts,
   * because the row is here and pi's own session file is on the volume.
   */
  beginSession(sessionId, { routine = "", agent = "pi" } = {}) {
    const now = Date.now();
    const row = this.db
      .prepare("SELECT session_id FROM sessions WHERE session_id = ?")
      .get(sessionId);
    if (row) {
      this.db
        .prepare(
          "UPDATE sessions SET ended_at = NULL, turns = turns + 1 WHERE session_id = ?",
        )
        .run(sessionId);
    } else {
      this.db
        .prepare(
          "INSERT INTO sessions (session_id, routine, agent, started_at, turns) VALUES (?, ?, ?, ?, 1)",
        )
        .run(sessionId, routine, agent, now);
    }
    return this.db
      .prepare("SELECT * FROM sessions WHERE session_id = ?")
      .get(sessionId);
  }

  endSession(sessionId) {
    this.db
      .prepare("UPDATE sessions SET ended_at = ? WHERE session_id = ?")
      .run(Date.now(), sessionId);
  }

  /**
   * Remember something. Idempotent on the CONTENT: the same text is the same
   * memory, so a routine that repeats itself does not grow the database. The
   * `uses` counter is the signal of a memory that keeps mattering.
   */
  remember({
    kind = "note",
    key = "",
    content = "",
    status = "",
    source = "",
    agent = "pi",
    session = "",
    confidence = 1.0,
  }) {
    const now = Date.now();
    const hash = hashContent(`${kind}\u0000${content}`);
    const existing = this.db
      .prepare("SELECT id, uses FROM entries WHERE content_hash = ?")
      .get(hash);
    if (existing) {
      this.db
        .prepare(
          "UPDATE entries SET updated_at = ?, last_used_at = ?, uses = uses + 1 WHERE id = ?",
        )
        .run(now, now, existing.id);
      return { id: existing.id, created: false };
    }
    const info = this.db
      .prepare(
        `INSERT INTO entries
         (kind, key, content, status, source, agent, session, confidence,
          created_at, updated_at, last_used_at, uses, content_hash)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)`,
      )
      .run(
        kind,
        key,
        content,
        status,
        source,
        agent,
        session,
        confidence,
        now,
        now,
        now,
        hash,
      );
    return { id: Number(info.lastInsertRowid), created: true };
  }

  /** The append-only log. What happened, when, in which session. */
  logEvent({ kind = "", key = "", session = "", agent = "pi", payload = {} }) {
    const info = this.db
      .prepare(
        "INSERT INTO events (ts, kind, key, agent, session, payload) VALUES (?, ?, ?, ?, ?, ?)",
      )
      .run(
        Date.now(),
        kind,
        key,
        agent,
        session,
        JSON.stringify(payload ?? {}),
      );
    return Number(info.lastInsertRowid);
  }

  /** What the harness remembers about a session (or everything). */
  recall({ session = "", kind = "", limit = 50 } = {}) {
    const clauses = [];
    const params = [];
    if (session) {
      clauses.push("session = ?");
      params.push(session);
    }
    if (kind) {
      clauses.push("kind = ?");
      params.push(kind);
    }
    const where = clauses.length ? `WHERE ${clauses.join(" AND ")}` : "";
    params.push(Math.min(Math.max(Number(limit) || 50, 1), 500));
    return this.db
      .prepare(
        `SELECT id, kind, key, content, status, source, agent, session,
                confidence, created_at, updated_at, last_used_at, uses
         FROM entries ${where} ORDER BY id DESC LIMIT ?`,
      )
      .all(...params);
  }

  /** The log of a session. */
  events({ session = "", limit = 100 } = {}) {
    const params = [];
    let where = "";
    if (session) {
      where = "WHERE session = ?";
      params.push(session);
    }
    params.push(Math.min(Math.max(Number(limit) || 100, 1), 1000));
    return this.db
      .prepare(`SELECT * FROM events ${where} ORDER BY seq DESC LIMIT ?`)
      .all(...params);
  }

  stats() {
    const one = (sql) => this.db.prepare(sql).get();
    return {
      db: this.dbPath,
      sessions: one("SELECT COUNT(*) AS n FROM sessions").n,
      entries: one("SELECT COUNT(*) AS n FROM entries").n,
      events: one("SELECT COUNT(*) AS n FROM events").n,
    };
  }
}
