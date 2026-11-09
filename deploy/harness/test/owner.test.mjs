/**
 * The waiting room: the questions the agent asks, and the answers.
 *
 * The cases that matter here are the ones where a question is asked TWICE,
 * answered with something that was not offered, or left to expire. Each of
 * them is a case where a bug would show up to the owner as "the agent
 * decided something on its own".
 */

import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { Memory } from "../memory.mjs";
import { Owner } from "../owner.mjs";

function fresh() {
  const dir = mkdtempSync(join(tmpdir(), "ikigai-owner-"));
  const memory = new Memory(join(dir, "memory.sqlite"));
  const owner = new Owner({ memory, defaultTimeoutMs: 60_000 });
  return { dir, memory, owner };
}

test("a question is asked, and it is pending until it is answered", () => {
  const { dir, memory, owner } = fresh();
  try {
    const asked = owner.ask({
      session: "tg-1",
      client: "tg:1",
      question: "Isto é uma nota ou um sonho?",
      kind: "choice",
      options: ["nota", "sonho"],
    });
    assert.equal(asked.ok, true);
    assert.equal(asked.question.state, "pending");
    assert.deepEqual(asked.question.options, ["nota", "sonho"]);

    const read = owner.read(asked.question.id);
    assert.equal(read.state, "pending");
    assert.equal(read.value, null);
  } finally {
    memory.close();
    rmSync(dir, { recursive: true, force: true });
  }
});

test("the answer unblocks the question, and the question remembers it", () => {
  const { dir, memory, owner } = fresh();
  try {
    const asked = owner.ask({ session: "tg-1", question: "Qual?", kind: "choice", options: ["a", "b"] });
    const answered = owner.answer(asked.question.id, "b");
    assert.equal(answered.ok, true);
    assert.equal(answered.question.state, "answered");
    assert.equal(answered.question.value, "b");

    const read = owner.read(asked.question.id);
    assert.equal(read.state, "answered");
    assert.equal(read.value, "b");
  } finally {
    memory.close();
    rmSync(dir, { recursive: true, force: true });
  }
});

test("answering twice is refused: the first answer moved the agent on", () => {
  const { dir, memory, owner } = fresh();
  try {
    const asked = owner.ask({ session: "tg-1", question: "Qual?", kind: "choice", options: ["a", "b"] });
    owner.answer(asked.question.id, "a");
    const second = owner.answer(asked.question.id, "b");
    assert.equal(second.ok, false);
    assert.match(second.error, /already answered/);
    // And the first answer is the one that stands.
    assert.equal(owner.read(asked.question.id).value, "a");
  } finally {
    memory.close();
    rmSync(dir, { recursive: true, force: true });
  }
});

test("an answer that was not one of the options is refused", () => {
  const { dir, memory, owner } = fresh();
  try {
    const asked = owner.ask({ session: "tg-1", question: "Qual?", kind: "choice", options: ["a", "b"] });
    const wrong = owner.answer(asked.question.id, "c");
    assert.equal(wrong.ok, false);
    assert.match(wrong.error, /not one of the options/);
  } finally {
    memory.close();
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a confirmation has exactly two answers, and they are the same two", () => {
  const { dir, memory, owner } = fresh();
  try {
    const asked = owner.ask({ session: "tg-1", question: "Guardo?", kind: "confirm" });
    assert.deepEqual(asked.question.options, ["Sim", "Não"]);
    assert.equal(owner.answer(asked.question.id, "Sim").ok, true);
    const other = owner.ask({ session: "tg-1", question: "Guardo?", kind: "confirm" });
    assert.equal(owner.answer(other.question.id, "Talvez").ok, false);
  } finally {
    memory.close();
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a question past its deadline reads as EXPIRED, not as pending", async () => {
  const { dir, memory, owner } = fresh();
  try {
    const asked = owner.ask({
      session: "tg-1",
      question: "Qual?",
      kind: "choice",
      options: ["a", "b"],
      timeoutMs: 1,
    });
    await new Promise((resolve) => setTimeout(resolve, 20));
    const read = owner.read(asked.question.id);
    assert.equal(read.state, "expired");
    // And it cannot be answered afterwards: the agent already moved on.
    assert.equal(owner.answer(asked.question.id, "a").ok, false);
  } finally {
    memory.close();
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a timeout that is not positive means the DEFAULT ceiling, not an instant expiry", () => {
  const { dir, memory, owner } = fresh();
  try {
    const asked = owner.ask({
      session: "tg-1",
      question: "Qual?",
      kind: "text",
      timeoutMs: -1,
    });
    const ceiling = asked.question.deadline_at - asked.question.created_at;
    assert.equal(ceiling, 60_000);
    assert.equal(owner.read(asked.question.id).state, "pending");
  } finally {
    memory.close();
    rmSync(dir, { recursive: true, force: true });
  }
});

test("an empty question is refused, and a choice needs two options", () => {
  const { dir, memory, owner } = fresh();
  try {
    assert.equal(owner.ask({ session: "tg-1", question: "   " }).ok, false);
    assert.equal(owner.ask({ session: "tg-1", question: "Qual?", kind: "choice", options: ["a"] }).ok, false);
    assert.equal(owner.ask({ session: "tg-1", question: "Qual?", kind: "wat" }).ok, false);
  } finally {
    memory.close();
    rmSync(dir, { recursive: true, force: true });
  }
});

test("the pending list is the questions of ONE session", () => {
  const { dir, memory, owner } = fresh();
  try {
    owner.ask({ session: "tg-1", question: "A?", kind: "text" });
    owner.ask({ session: "tg-2", question: "B?", kind: "text" });
    const pending = owner.pending("tg-1");
    assert.equal(pending.length, 1);
    assert.equal(pending[0].question, "A?");
  } finally {
    memory.close();
    rmSync(dir, { recursive: true, force: true });
  }
});

test("the question SURVIVES the memory being reopened: it is durable, not in RAM", () => {
  const dir = mkdtempSync(join(tmpdir(), "ikigai-owner-"));
  const db = join(dir, "memory.sqlite");
  try {
    const first = new Memory(db);
    const owner = new Owner({ memory: first });
    const asked = owner.ask({ session: "tg-1", question: "Qual?", kind: "choice", options: ["a", "b"] });
    first.close();

    const second = new Memory(db);
    const reopened = new Owner({ memory: second });
    const read = reopened.read(asked.question.id);
    assert.equal(read.ok, true);
    assert.equal(read.state, "pending");
    assert.equal(reopened.answer(asked.question.id, "a").ok, true);
    second.close();
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("the event log carries the question and the answer, for the feed", () => {
  const { dir, memory, owner } = fresh();
  try {
    const asked = owner.ask({ session: "tg-1", question: "Qual?", kind: "choice", options: ["a", "b"] });
    owner.answer(asked.question.id, "b");
    const page = memory.eventsSince({ session: "tg-1", since: 0 });
    const kinds = page.events.map((event) => event.kind);
    assert.ok(kinds.includes("question.asked"));
    assert.ok(kinds.includes("question.answered"));
    // The cursor moves forward: asking again does not repeat the old events.
    const next = memory.eventsSince({ session: "tg-1", since: page.tip });
    assert.equal(next.events.length, 0);
  } finally {
    memory.close();
    rmSync(dir, { recursive: true, force: true });
  }
});
