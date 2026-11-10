/**
 * The refusal: what the harness says when a session is BUSY.
 *
 * WHY A MODULE OF ITS OWN: the refusal is a CONTRACT — a status code, a
 * sentence, an event — and it is the one thing about concurrency that the
 * harness and the bot have to agree on. A pure function over the routine's
 * name is testable without an agent and without a database, the same shape
 * `stop.mjs` has.
 *
 * WHY IT EXISTS AT ALL: measured on the box (2026-11-10, 11:44:41Z–11:45:27Z),
 * a second routine in a busy session was refused by the AGENT'S SDK — *"Agent
 * is already processing. Specify streamingBehavior ('steer' or 'followUp') to
 * queue the message."* The harness turned that into a 502, so the owner would
 * have read a stranger's sentence about a parameter the owner does not have;
 * and the SDK's prompt wrote `routine.started` for a request that never ran,
 * so the log counted two starts and one finish.
 *
 * So the refusal is DECLARED: the harness refuses BEFORE it calls the agent,
 * with its own status, its own sentence and its own event — and the turn that
 * is running is not touched.
 *
 * WHY 409: the request CONFLICTS with the state of the session — a turn is
 * in flight. It is not a failure of the harness (503) and not a bad request
 * (400): the same request, sent a minute later, is fine. The bot tells the
 * two apart by this code, because *"a rotina foi recusada"* and *"a rotina
 * falhou"* are different sentences and the owner acts differently on each.
 */

/** The status of a refusal: a conflict with the session's state. */
export const SESSION_BUSY_STATUS = 409;

/**
 * The refusal of a routine that did not start because the session is busy.
 *
 * The `error` says what happened; the `detail` says what to do. A refusal
 * that does not tell the owner what to do is a refusal that wastes a round
 * trip.
 */
export function sessionBusyRefusal(routine) {
  return {
    status: SESSION_BUSY_STATUS,
    error: "the session is busy: the routine did not start",
    detail: `another routine is running in this session; wait for it to finish and send "${routine}" again`,
  };
}
