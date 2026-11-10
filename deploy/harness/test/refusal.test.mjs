/**
 * The refusal: what it says, and — more importantly — what it must NOT say.
 *
 * The refusal is the product's sentence, not the agent SDK's. Measured on the
 * box (2026-11-10), the second routine in a busy session was refused by the
 * SDK with a sentence about `streamingBehavior` — a parameter the owner does
 * not have and cannot set. If the harness passes that on, the owner reads a
 * stranger's error; if it passes it on as a 502, the owner reads a failure
 * for a request that never ran.
 *
 * So the contract is asserted here, in the house's own shape: a pure
 * function, tested without an agent and without a database.
 */

import test from "node:test";
import assert from "node:assert/strict";

import { SESSION_BUSY_STATUS, sessionBusyRefusal } from "../refusal.mjs";

test("the refusal is a conflict, not a failure", () => {
  assert.equal(SESSION_BUSY_STATUS, 409);
});

test("the refusal says what happened", () => {
  const refusal = sessionBusyRefusal("daily-note");
  assert.match(refusal.error, /session is busy/);
  assert.match(refusal.error, /did not start/);
});

test("the refusal says what to do", () => {
  const refusal = sessionBusyRefusal("daily-note");
  assert.match(refusal.detail, /another routine is running/);
  assert.match(refusal.detail, /wait for it to finish/);
  assert.match(refusal.detail, /daily-note/);
});

test("the refusal is the PRODUCT's sentence, not the SDK's", () => {
  const refusal = sessionBusyRefusal("daily-note");
  const said = `${refusal.error} ${refusal.detail}`;
  assert.doesNotMatch(said, /already processing/);
  assert.doesNotMatch(said, /streamingBehavior/);
  assert.doesNotMatch(said, /steer/);
  assert.doesNotMatch(said, /followUp/);
});
