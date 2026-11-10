/**
 * The ceiling of a run: what happens when the run's own clock runs out.
 *
 * THE FAILURE THIS EXISTS TO FIX, measured on the box (2026-11-10):
 *
 *   A cadence run started at 01:00:00Z. Its ceiling was 30 minutes. At
 *   01:30:00Z the harness answered `routine.failed` and threw (502) — and the
 *   AGENT KEPT WORKING until 01:33:08Z, three minutes AFTER the run had
 *   already told the owner it had failed.
 *
 * WHY THE TIMEOUT DID NOT STOP IT: the SDK's `promptAndWait` passes the
 * ceiling to `collectEvents(timeout)`, and that timer only REJECTS a promise
 * (`reject(new Error("Timeout collecting events…"))`). It never touches the
 * process. The agent's turn is an EVENT, and a promise that is rejected does
 * not kill the thing that was going to emit it.
 *
 * So the ceiling was a PROMISE and not a KILL — and the difference is three
 * minutes of writes nobody was waiting for.
 *
 * THE RULE, and it is the mirror of the Stop: a run that ends must leave NO
 * agent working behind it. The Stop kills the agent (`release`); the ceiling
 * kills the agent too. The two differ only in what the run ANSWERS — a stop
 * answers "cancelled" (the owner decided), a ceiling answers "failed" (the
 * clock decided) — and in that BOTH of them stop the agent.
 *
 * WHY IT LIVES HERE AND NOT IN `server.mjs`: the decision is a pure function
 * over the run, and the run is the thing that is easy to get wrong. It is
 * tested here without an agent, without a socket and without a database.
 */

/**
 * Did this run die because its clock ran out?
 *
 * WHY A MARKER AND NOT A MESSAGE: the SDK's timeout message is
 * "Timeout collecting events. Stderr: …" — a string that belongs to the
 * agent, not to us, and it can change under our feet. A marker is a fact the
 * HARNESS owns, and it is set at the moment the harness decides to stop the
 * agent, which is the same moment the answer changes.
 *
 * The marker is an object and not a boolean, so two runs of the same session
 * cannot overwrite each other's marker.
 */
export class Ceiling {
  constructor(ms) {
    this.ms = Number(ms) || 0;
    this.reached = false;
    /** When the ceiling was reached, in epoch millis. Null until it is. */
    this.at = null;
  }

  /** Mark the ceiling as reached. It happens once. */
  hit() {
    if (this.reached) return;
    this.reached = true;
    this.at = Date.now();
  }
}

/**
 * Did this failure come from the ceiling?
 *
 * The SDK rejects with a message; the HARNESS decides. So the run marks its
 * own ceiling when it stops the agent, and this asks the marker — not the
 * text. A message that merely CONTAINS the word "timeout" is not a ceiling:
 * a provider that answers "timeout" is a refusal, and a refusal has its own
 * path (the fallback).
 */
export function hitCeiling(ceiling) {
  return Boolean(ceiling && ceiling.reached);
}

/**
 * Stop the agent whose clock ran out.
 *
 * THIS IS THE WHOLE POINT OF THE MODULE, and it is the mirror of the Stop:
 * a run that ends must leave no agent working behind it.
 *
 * `kill` is the caller's way of stopping the agent — the harness passes the
 * session's release, which stops the `pi` process and forgets the session.
 * It is INJECTED and not imported so that the decision can be tested here
 * without an agent, without a socket and without a database: the test
 * asserts that the kill was called, and a broken call site fails the test
 * instead of failing silently on the box.
 *
 * The answer is a BOOLEAN, not a promise of a message: it says whether the
 * agent was stopped, and the caller decides what the run answers.
 */
export async function killExpiredAgent(ceiling, kill) {
  if (!hitCeiling(ceiling)) return false;
  await kill();
  return true;
}

/**
 * Forget a session and stop the agent it was holding.
 *
 * WHY THE ENTRY IS PASSED AND NOT LOOKED UP: the session id is the
 * CONVERSATION, and two runs of the same chat share it. A release that
 * looked the id up could stop an agent that belongs to a DIFFERENT run — a
 * run that started after this one and is holding a live turn. The caller
 * holds the entry it started with, and that is the one it releases.
 *
 * The run that is releasing has already ended (its turn is over), so the
 * entry it releases is the one whose turn it was.
 *
 * WHY THE SESSION IS FORGOTTEN AND NOT ONLY THE PROCESS STOPPED: a session
 * that keeps a DEAD agent in the pool fails the next routine of that chat on
 * a client that no longer answers. The next run spawns a fresh `pi`.
 *
 * `sessions` is the pool, and it is INJECTED so that this can be tested
 * without an agent, without a socket and without a database.
 */
export async function releaseEntry(entry, sessions) {
  if (!entry) return;
  // Only the session that IS this entry is forgotten. A session that was
  // re-acquired in the meantime belongs to another run and stays.
  if (sessions && sessions.get(entry.sessionId) === entry) sessions.delete(entry.sessionId);
  try {
    await entry.client.stop();
  } catch {
    /* the process is already gone; nothing to close */
  }
}

/**
 * The run's answer, when its clock ran out.
 *
 * `null` means "this run did not hit its ceiling" — so the caller keeps its
 * own failure (a refusal, a crash, a cancelled stop). An object IS the
 * answer: `ok: false` with `cancelled: false`, because a run that ran out of
 * time did NOT fail for a reason the owner chose, and it is not a
 * cancellation either — nobody pressed Stop.
 *
 * `detail` keeps the cause that produced it, so nothing is swallowed.
 */
export function ceilingRun(ceiling, failure) {
  if (!hitCeiling(ceiling)) return null;
  return {
    ok: false,
    cancelled: false,
    timedOut: true,
    error: `the routine exceeded its ceiling of ${ceiling.ms} ms`,
    detail: failure || null,
  };
}
