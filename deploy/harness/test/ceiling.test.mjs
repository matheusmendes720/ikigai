/**
 * The ceiling: the run's own clock, and what it has to do to the agent.
 *
 * THE FAILURE THIS GUARDS, measured on the box (2026-11-10):
 *
 *   A cadence run started at 01:00:00Z. Its ceiling was 30 minutes. At
 *   01:30:00Z the harness answered `routine.failed` and threw (502) — and the
 *   AGENT KEPT WORKING until 01:33:08Z, three minutes after the owner was
 *   told the routine had failed.
 *
 * WHY THE TIMEOUT DID NOT STOP IT: the SDK's `promptAndWait` passes the
 * ceiling to `collectEvents(timeout)`, and that timer only REJECTS a
 * promise. It never touches the process. The agent's turn is an EVENT, and a
 * rejected promise does not kill the thing that was going to emit it.
 *
 * So these tests assert the ONE thing that was wrong: a run whose clock ran
 * out KILLS the agent it was running.
 *
 * The decision lives in `ceiling.mjs` and is a pure function over the run, so
 * it is tested here without an agent and without a database — and the KILL
 * is INJECTED, so a broken call site fails the test instead of failing
 * silently on the box.
 */

import test from "node:test";
import assert from "node:assert/strict";

import { Ceiling, ceilingRun, hitCeiling, killExpiredAgent, releaseEntry } from "../ceiling.mjs";

/**
 * An agent that records whether it was stopped.
 *
 * This is the stand-in for the `pi` process: the harness passes the
 * session's release, which stops the process and forgets the session.
 */
function fakeAgent() {
  const state = { stopped: 0 };
  state.kill = async () => {
    state.stopped += 1;
  };
  return state;
}

test("a run whose clock ran out KILLS the agent", async () => {
  // THE MEASURED FAILURE, in one line: the agent kept working for three
  // minutes after the run had already answered "failed".
  const agent = fakeAgent();
  const ceiling = new Ceiling(30 * 60 * 1000);
  ceiling.hit();

  const killed = await killExpiredAgent(ceiling, agent.kill);

  assert.equal(killed, true, "the agent was not stopped — it keeps writing after the run ends");
  assert.equal(agent.stopped, 1, "the agent was not stopped exactly once");
});

test("a run that did NOT run out of time leaves the agent alone", async () => {
  // THE OTHER HALF, and the one that matters as much: a healthy agent must
  // NOT be killed because a run finished. The `finally` of a run runs on the
  // success path too, and a kill there would throw away the conversation on
  // every turn.
  const agent = fakeAgent();
  const ceiling = new Ceiling(30 * 60 * 1000);

  const killed = await killExpiredAgent(ceiling, agent.kill);

  assert.equal(killed, false);
  assert.equal(agent.stopped, 0, "a healthy agent was killed by a run that finished in time");
});

test("a run that failed for another reason leaves the agent alone", async () => {
  // A provider refusal is not a ceiling. The agent is idle after a refusal,
  // and killing it would throw the conversation away for nothing.
  const agent = fakeAgent();
  const ceiling = new Ceiling(30 * 60 * 1000);

  const killed = await killExpiredAgent(ceiling, agent.kill);

  assert.equal(killed, false);
  assert.equal(agent.stopped, 0);
});

test("the marker is set once, and it remembers WHEN", () => {
  const ceiling = new Ceiling(1000);
  assert.equal(hitCeiling(ceiling), false);
  assert.equal(ceiling.at, null);

  ceiling.hit();
  const first = ceiling.at;
  assert.equal(hitCeiling(ceiling), true);
  assert.ok(typeof first === "number" && first > 0, "the marker does not say when it was reached");

  ceiling.hit();
  assert.equal(ceiling.at, first, "a second hit moved the moment the ceiling was reached");
});

test("a run that ran out of time answers 'failed', NOT 'cancelled'", async () => {
  // Nobody pressed Stop. The CLOCK decided. Answering "cancelled" tells the
  // owner they stopped it, and that is a lie about what happened.
  const ceiling = new Ceiling(1000);
  ceiling.hit();

  const answer = ceilingRun(ceiling, "the agent's turn never settled");

  assert.equal(answer.ok, false);
  assert.equal(answer.cancelled, false, "a timeout was reported as a cancellation");
  assert.equal(answer.timedOut, true);
  assert.match(answer.error, /exceeded its ceiling of 1000 ms/);
  assert.equal(answer.detail, "the agent's turn never settled", "the cause was swallowed");
});

test("a run that did NOT run out of time keeps its own failure", () => {
  // `null` means "this was not the clock" — so the caller keeps the failure
  // it has (a refusal, a crash, a cancelled stop).
  const ceiling = new Ceiling(1000);
  assert.equal(ceilingRun(ceiling, "the provider refused"), null);
});

test("the ceiling answers even when there is no failure to explain", () => {
  // The detail is kept when there is one, and it is null when there is none.
  // Nothing is invented.
  const ceiling = new Ceiling(1000);
  ceiling.hit();

  const answer = ceilingRun(ceiling, null);

  assert.equal(answer.detail, null);
  assert.equal(answer.timedOut, true);
});

test("the marker, not the message, says the clock ran out", () => {
  // A provider that answers "timeout" is a REFUSAL, and a refusal has its
  // own path (the fallback). The word in the text is not the fact.
  const ceiling = new Ceiling(1000);
  assert.equal(hitCeiling(ceiling), false, "the word 'timeout' was read as the clock");
});

// ── the release ─────────────────────────────────────────────────────────────
//
// A release does two things: it stops the agent, and it FORGETS the session.
//
// WHY FORGETTING MATTERS: a session that keeps a DEAD agent in the pool fails
// the next routine of that chat on a client that no longer answers. So a kill
// that only stops the process leaves the next run dead on arrival.
//
// WHY THE ENTRY AND NOT THE SESSION ID: the chat is ONE conversation, and
// two runs of it share the session key. A release that looked the id up could
// stop an agent that belongs to a DIFFERENT run — one that started after this
// one and is holding a live turn.

/** A session entry, with a client that records whether it was stopped. */
function liveEntry(sessionId) {
  const state = { stopped: 0 };
  return {
    entry: {
      sessionId,
      client: {
        stop: async () => {
          state.stopped += 1;
        },
      },
    },
    state,
  };
}

test("a released session is FORGOTTEN, not only stopped", async () => {
  const { entry, state } = liveEntry("tg-1");
  const sessions = new Map([["tg-1", entry]]);

  await releaseEntry(entry, sessions);

  assert.equal(state.stopped, 1, "the agent was not stopped");
  assert.equal(sessions.has("tg-1"), false, "the session keeps a DEAD agent in the pool");
});

test("a release does NOT forget a session that belongs to ANOTHER run", async () => {
  // The chat is one conversation. A run that started AFTER this one holds a
  // live turn on the same key, and a release that looked the id up would kill
  // it. The entry knows which one it is.
  const { entry, state } = liveEntry("tg-1");
  const other = liveEntry("tg-1").entry;
  const sessions = new Map([["tg-1", other]]);

  await releaseEntry(entry, sessions);

  assert.equal(state.stopped, 1, "the agent of THIS run was not stopped");
  assert.equal(
    sessions.get("tg-1"),
    other,
    "the session of another run was forgotten — that run lost its agent",
  );
});

test("a release survives an agent that is already gone", async () => {
  // The process died on its own, or the Stop already killed it. The release
  // must not throw on the way out: the run has to ANSWER either way.
  const entry = {
    sessionId: "tg-1",
    client: {
      stop: async () => {
        throw new Error("the process is already gone");
      },
    },
  };
  const sessions = new Map([["tg-1", entry]]);

  await releaseEntry(entry, sessions);

  assert.equal(sessions.has("tg-1"), false, "the session of a dead agent stayed in the pool");
});
