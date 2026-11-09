/**
 * The owner: the questions the agent asks, and the answers that unblock it.
 *
 * THIS IS THE HUMAN IN THE LOOP, AND IT IS A WAITING ROOM.
 *
 * The agent, mid-turn, calls the `ask` tool and the call BLOCKS until the
 * owner answers. The agent is not "notified" later — it is suspended on the
 * question, exactly where it was, with its context intact. That is the
 * difference between an agent that can wait for a human and an agent that
 * ends its turn and hopes the next message is the answer.
 *
 * WHY THE WAITING ROOM IS HERE AND NOT IN THE BOT: the bot is a CHANNEL. It
 * renders what the runtime says and carries what the owner says back. If the
 * pending question lived in the bot's memory, a bot restart would lose the
 * question while the agent kept waiting for it — and the agent would wait
 * until its deadline with nobody able to answer. So the question lives HERE,
 * in the runtime's own SQLite, and it survives the bot, the harness and the
 * phone.
 *
 * WHY THE QUESTION IS PERSISTED AND NOT JUST HELD: the same reason the store
 * persists its change log (ADR-039) — a state that only exists in memory is
 * a state that a restart erases. The row is the truth: it says a question was
 * asked, of whom, with which options, and whether it was answered, expired or
 * abandoned.
 *
 * THE FOUR KINDS, because they are four DIFFERENT TELEGRAM SURFACES:
 *
 *   choice   — the owner picks one of N. An inline keyboard.
 *   confirm  — the owner says yes or no. An inline keyboard.
 *   text     — the owner writes. A button that arms the chat for prose.
 *   editor   — the owner writes, and may write more than one line.
 *
 * The channel decides how to render them; the runtime only knows what was
 * asked and what came back. A channel that cannot render a kind says so
 * rather than pretending the question was answered.
 */

import { randomBytes } from "node:crypto";

/** The default ceiling of a question: a quarter of an hour. */
export const DEFAULT_TIMEOUT_MS = 15 * 60 * 1000;

/** The kinds the owner understands. Anything else is a programming error. */
export const KINDS = Object.freeze(["choice", "confirm", "text", "editor"]);

export class Owner {
  /**
   * @param {object} options
   * @param {import("./memory.mjs").Memory} options.memory the durable log
   * @param {number} [options.defaultTimeoutMs] the ceiling of a question
   */
  constructor({ memory, defaultTimeoutMs = DEFAULT_TIMEOUT_MS }) {
    this.memory = memory;
    this.defaultTimeoutMs = defaultTimeoutMs;
  }

  /**
   * Ask the owner, and register the question.
   *
   * The call does NOT wait: the WAITING happens in the agent's tool call,
   * which polls this question's state. Splitting it this way keeps the
   * broker free of timers and of the caller's lifetime — a question that
   * outlives its asker is still answerable.
   */
  ask({
    session,
    client = "",
    question,
    options = [],
    kind = "text",
    timeoutMs = null,
  }) {
    const text = String(question || "").trim();
    if (!text) {
      return { ok: false, error: "the question is empty" };
    }
    const shape = String(kind || "text");
    if (!KINDS.includes(shape)) {
      return { ok: false, error: `unknown question kind: ${shape}` };
    }
    const choices = (Array.isArray(options) ? options : [])
      .map((o) => String(o).trim())
      .filter(Boolean);
    if (shape === "choice" && choices.length < 2) {
      return { ok: false, error: "a choice needs at least two options" };
    }
    if (shape === "confirm") {
      // A confirmation has exactly two answers, and they are the same two
      // answers every time — so they are written once, here.
      choices.length = 0;
      choices.push("Sim", "Não");
    }

    const now = Date.now();
    const id = randomBytes(6).toString("hex");
    const ceiling = Number(timeoutMs) > 0 ? Number(timeoutMs) : this.defaultTimeoutMs;
    const row = {
      id,
      session: String(session || ""),
      client: String(client || ""),
      kind: shape,
      question: text,
      options: choices,
      state: "pending",
      value: null,
      created_at: now,
      deadline_at: now + ceiling,
    };
    this.memory.putQuestion(row);
    this.memory.logEvent({
      kind: "question.asked",
      key: id,
      session: row.session,
      payload: {
        // The id travels IN the payload as well as in the event's key: the
        // client that draws the question needs it, and a client that reads
        // one field is a client that does not have to know the log's shape.
        id,
        kind: shape,
        question: text,
        options: choices,
        client: row.client,
        deadline_at: row.deadline_at,
      },
    });
    return { ok: true, question: this._public(row) };
  }

  /**
   * The state of one question, as the waiting tool call sees it.
   *
   * A question past its deadline reads as EXPIRED, not as pending: a tool
   * call that waits forever is a turn that never ends, and the agent has to
   * be able to continue with its own default.
   */
  read(questionId) {
    const row = this.memory.getQuestion(String(questionId || ""));
    if (!row) return { ok: false, error: "no such question" };
    if (row.state === "pending" && Date.now() > row.deadline_at) {
      this.memory.updateQuestion(row.id, { state: "expired" });
      this.memory.logEvent({
        kind: "question.expired",
        key: row.id,
        session: row.session,
        payload: { kind: row.kind, question: row.question },
      });
      return { ok: true, state: "expired", value: null, question: this._public(row) };
    }
    return { ok: true, state: row.state, value: row.value, question: this._public(row) };
  }

  /**
   * The owner's answer.
   *
   * Answering a question twice is refused, and the second answer is refused
   * LOUDLY: the first answer moved the agent on, and a second one would be a
   * different conversation pretending to be the same one.
   *
   * The answer can arrive as TEXT or as an INDEX — the index of the option
   * in the question. The index is what a channel sends: Telegram caps a
   * button's payload at 64 bytes, and an option the agent proposed can be a
   * sentence. The text always comes from HERE, from the question the runtime
   * asked, so a truncated option can never become a truncated answer.
   */
  answer(questionId, value, optionIndex = null) {
    const id = String(questionId || "");
    const row = this.memory.getQuestion(id);
    if (!row) return { ok: false, error: "no such question" };
    if (row.state !== "pending") {
      return { ok: false, error: `the question was already ${row.state}` };
    }
    let text = value === null || value === undefined ? "" : String(value);
    if (optionIndex !== null && optionIndex !== undefined) {
      const index = Number(optionIndex);
      if (!Number.isInteger(index) || index < 0 || index >= row.options.length) {
        return { ok: false, error: `not an option of this question: ${optionIndex}` };
      }
      text = row.options[index];
    }
    if (row.kind === "choice" && row.options.length > 0 && !row.options.includes(text)) {
      return {
        ok: false,
        error: `not one of the options: ${row.options.join(" | ")}`,
      };
    }
    if (row.kind === "confirm" && !["Sim", "Não"].includes(text)) {
      return { ok: false, error: "a confirmation is answered with Sim or Não" };
    }
    this.memory.updateQuestion(id, { state: "answered", value: text });
    this.memory.logEvent({
      kind: "question.answered",
      key: id,
      session: row.session,
      payload: { kind: row.kind, value: text },
    });
    return { ok: true, question: this._public({ ...row, state: "answered", value: text }) };
  }

  /** The questions a session still has open. */
  pending(session) {
    const rows = this.memory.listQuestions({ session, state: "pending" });
    const now = Date.now();
    const open = [];
    for (const row of rows) {
      if (now > row.deadline_at) {
        this.memory.updateQuestion(row.id, { state: "expired" });
        continue;
      }
      open.push(this._public(row));
    }
    return open;
  }

  _public(row) {
    return {
      id: row.id,
      session: row.session,
      client: row.client,
      kind: row.kind,
      question: row.question,
      options: row.options || [],
      state: row.state,
      value: row.value ?? null,
      created_at: row.created_at,
      deadline_at: row.deadline_at,
    };
  }
}
