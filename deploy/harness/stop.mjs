/**
 * The Stop: the owner pressed the button, and the work behind it has to stop.
 *
 * Telegram's Stop does not stop anything by itself. It is an UPDATE — "the
 * owner wants the generation to stop" — and what has to stop is the AGENT: a
 * `pi` process holding a turn, with the store open. Killing only the
 * client's wait would leave the agent working, and an agent that keeps
 * working keeps writing: the owner cancelled the routine and the note
 * arrived anyway.
 *
 * So a stop is two facts, and they live HERE so that the route and the run
 * agree on them:
 *
 *   1. the session was MARKED — so the run that is in flight can answer
 *      "cancelled" instead of "failed" (a cancelled run did not fail, and
 *      the owner is told the truth);
 *   2. the session's PROCESS is released — so the agent stops.
 *
 * The decision itself is a pure function over the session entry, because it
 * is the decision that is easy to get wrong: a stop for a session that is
 * NOT running must not kill anything, and must not leave a mark that stops
 * the NEXT run of that session.
 */

/**
 * A stop was asked for. What it means, and whether it marked anything.
 *
 * `entry` is the session — the live `pi` process and the turn in flight. It
 * is `null` when there is no such session, and that is NOT an error: the
 * owner may press Stop after the run is already over, and the answer then
 * is "there was nothing to stop", not a failure.
 *
 * `turns` is the COUNTER of the turns in flight, not a flag — a flag is
 * cleared by a request that was REFUSED, and a session that was busy a
 * moment ago must not look idle now (the reaper kills idle sessions, and
 * it once killed a live agent mid-write because of exactly that).
 */
export function requestStop(entry) {
  if (!entry) {
    return { cancelled: false, reason: "there is no session for that key" };
  }
  if (!(entry.turns > 0)) {
    // No turn is in flight. Marking it would stop the NEXT run of that
    // session — a stop that arrives late must not cancel tomorrow.
    return { cancelled: false, reason: "nothing was running" };
  }
  entry.cancelled = true;
  return { cancelled: true, reason: "the run was stopped" };
}

/**
 * The run's answer, when it was stopped.
 *
 * `null` means "this run was not stopped" — so the caller keeps its own
 * failure. An object IS the answer: `ok: false` with `cancelled: true`,
 * because a cancelled routine produced nothing and said nothing, and
 * "it failed" would put a red mark on the owner's decision.
 */
export function stoppedRun(entry, failure) {
  if (!entry || !entry.cancelled) return null;
  return {
    ok: false,
    cancelled: true,
    error: "the routine was cancelled",
    detail: failure || null,
  };
}
