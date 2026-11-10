/**
 * The Stop: what a stop means, and — more importantly — what it must NOT
 * mean.
 *
 * The failures here are quiet ones. A stop that marks an IDLE session stops
 * the NEXT run of that session, hours later, for no reason the owner can
 * reconstruct. A run that answers "failed" for a routine the owner
 * deliberately stopped tells the owner their decision was a malfunction.
 *
 * And the one that was MEASURED on the box (2026-11-09): a stopped run
 * answered nothing at all. The agent was killed — the store stayed
 * untouched, 1 973 artefacts before and after — but the run itself waited
 * for an event that a dead agent never emits, and said "cancelled" only
 * twenty minutes later, when its own ceiling rejected the collection. So a
 * stop has to be TOLD to the run, not merely inferred from the agent dying.
 *
 * The decision lives in `stop.mjs` and is a pure function over the session
 * entry, so it is tested here without an agent and without a database.
 */

import test from "node:test";
import assert from "node:assert/strict";

import { createStopSignal, requestStop, stoppedRun } from "../stop.mjs";

/**
 * A session with ONE run in flight.
 *
 * The run registers two things: its NAME (the token, so a stop can say which
 * run it means) and its SIGNAL (what it waits on, so a stop can reach it).
 */
function liveSession(token = null) {
  const stop = createStopSignal();
  const entry = {
    turns: 1,
    cancelled: false,
    runTokens: new Map([[token, 1]]),
    stops: new Set([stop]),
  };
  return { entry, stop };
}

test("a stop for a session that is NOT running changes nothing", () => {
  const entry = { turns: 0, cancelled: false, runTokens: new Map(), stops: new Set() };
  const outcome = requestStop(entry);
  assert.equal(outcome.cancelled, false);
  assert.equal(
    entry.cancelled,
    false,
    "an idle session was marked — the next run of it would be cancelled for no reason",
  );
  assert.match(outcome.reason, /nothing was running/);
});

test("a stop for a session that does not exist changes nothing", () => {
  const outcome = requestStop(null);
  assert.equal(outcome.cancelled, false);
  assert.match(outcome.reason, /no session/);
});

test("a stop MARKS the run in flight", () => {
  const { entry } = liveSession("draft-7");
  const outcome = requestStop(entry, "draft-7");
  assert.equal(outcome.cancelled, true);
  assert.equal(entry.cancelled, true, "the run in flight was not marked");
  assert.match(outcome.reason, /stopped/);
});

test("a stopped run answers 'cancelled', not 'failed'", () => {
  const { entry } = liveSession("draft-7");
  requestStop(entry, "draft-7");
  const answer = stoppedRun(entry, "the agent's process died");
  assert.equal(answer.ok, false);
  assert.equal(answer.cancelled, true);
  assert.equal(answer.detail, "the agent's process died", "the cause is kept, not swallowed");
});

test("a run that was NOT stopped keeps its failure", () => {
  const { entry } = liveSession("draft-7");
  assert.equal(stoppedRun(entry, "the provider refused"), null);
});

test("a run that was stopped and then succeeded still answers 'cancelled'", () => {
  // The mark is the fact: the owner stopped it, and the run did not get to
  // say otherwise.
  const { entry } = liveSession("draft-7");
  requestStop(entry, "draft-7");
  const answer = stoppedRun(entry, null);
  assert.equal(answer.cancelled, true);
  assert.equal(answer.detail, null);
});

test("a stop TELLS the run: the signal the run waits on fires", async () => {
  // The measured failure: the agent died, so the turn never settled, so the
  // run waited for an event that would never come. The signal is how the
  // run learns it was stopped — without it, a cancelled run is a run that
  // hangs until its own ceiling.
  const { entry, stop } = liveSession("draft-7");
  let settled = false;
  stop.promise.then(() => {
    settled = true;
  });

  requestStop(entry, "draft-7");
  await Promise.resolve();

  assert.equal(settled, true, "the run was never told — it would wait for the ceiling");
  assert.equal(stop.fired(), true);
});

test("the signal fires only once", async () => {
  const stop = createStopSignal();
  let fired = 0;
  stop.promise.then(() => {
    fired += 1;
  });
  stop.fire();
  stop.fire();
  await Promise.resolve();
  assert.equal(fired, 1);
});

test("a stop that names a run that is NOT in flight changes nothing", () => {
  // The chat is ONE session, so every routine the owner starts in it shares
  // the session key. A Stop from a preview that is already over would land
  // on the NEXT routine of that chat and kill it — the owner pressed Stop
  // on the daily-note and the weekly-review died instead.
  const { entry, stop } = liveSession("draft-8");
  const outcome = requestStop(entry, "draft-7");

  assert.equal(outcome.cancelled, false);
  assert.equal(entry.cancelled, false, "a run that was not the one in flight was marked");
  assert.match(outcome.reason, /not the one in flight/);
  assert.equal(stop.fired(), false, "a run that was not the one in flight was told");
});

test("a stop with no name does not cancel a NAMED run", () => {
  // The safe direction: a client that cannot say which run it means must
  // not kill a run that can.
  const { entry } = liveSession("draft-8");
  const outcome = requestStop(entry);
  assert.equal(outcome.cancelled, false);
  assert.equal(entry.cancelled, false);
});

test("a stop with no name cancels a run with no name", () => {
  // The cadence does not open a preview, so its run has no name — and a
  // nameless stop is still a stop of whatever is running.
  const { entry, stop } = liveSession(null);
  const outcome = requestStop(entry);
  assert.equal(outcome.cancelled, true);
  assert.equal(stop.fired(), true);
});

test("a run is released when it ends: its name goes with it", () => {
  // The name lives as long as the run. A name that outlived its run would
  // let a stop from a preview that is over land on the next run.
  const { entry } = liveSession("draft-7");
  entry.runTokens.delete("draft-7");
  entry.turns = 0;

  const outcome = requestStop(entry, "draft-7");
  assert.equal(outcome.cancelled, false);
  assert.match(outcome.reason, /nothing was running/);
});

test("two runs that share a name keep it until the LAST one ends", () => {
  // The name is COUNTED. Two nameless runs in one session (the cadence, and
  // an owner routine whose preview Telegram refused) share the name `null`,
  // and the first one to end must not take the other's away — or the second
  // becomes impossible to stop.
  const { entry, stop } = liveSession(null);
  entry.runTokens.set(null, 2);

  entry.runTokens.set(null, (entry.runTokens.get(null) ?? 0) - 1);
  assert.equal(entry.runTokens.has(null), true, "the live run lost its name");

  const outcome = requestStop(entry);
  assert.equal(outcome.cancelled, true);
  assert.equal(stop.fired(), true);
});
