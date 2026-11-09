/**
 * The Stop: what a stop means, and — more importantly — what it must NOT
 * mean.
 *
 * The failures here are quiet ones. A stop that marks an IDLE session stops
 * the NEXT run of that session, hours later, for no reason the owner can
 * reconstruct. A run that answers "failed" for a routine the owner
 * deliberately stopped tells the owner their decision was a malfunction.
 *
 * The decision lives in `stop.mjs` and is a pure function over the session
 * entry, so it is tested here without an agent and without a database.
 */

import test from "node:test";
import assert from "node:assert/strict";

import { requestStop, stoppedRun } from "../stop.mjs";

test("a stop for a session that is NOT running changes nothing", () => {
  const entry = { turns: 0, cancelled: false };
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
  const entry = { turns: 1, cancelled: false };
  const outcome = requestStop(entry);
  assert.equal(outcome.cancelled, true);
  assert.equal(entry.cancelled, true, "the run in flight was not marked");
  assert.match(outcome.reason, /stopped/);
});

test("a stopped run answers 'cancelled', not 'failed'", () => {
  const entry = { turns: 1, cancelled: false };
  requestStop(entry);
  const answer = stoppedRun(entry, "the agent's process died");
  assert.equal(answer.ok, false);
  assert.equal(answer.cancelled, true);
  assert.equal(answer.detail, "the agent's process died", "the cause is kept, not swallowed");
});

test("a run that was NOT stopped keeps its failure", () => {
  const entry = { turns: 1, cancelled: false };
  assert.equal(stoppedRun(entry, "the provider refused"), null);
});

test("a run that was stopped and then succeeded still answers 'cancelled'", () => {
  // The mark is the fact: the owner stopped it, and the run did not get to
  // say otherwise.
  const entry = { turns: 1, cancelled: false };
  requestStop(entry);
  const answer = stoppedRun(entry, null);
  assert.equal(answer.cancelled, true);
  assert.equal(answer.detail, null);
});
