/**
 * The `ask` tool: the agent's door to the owner.
 *
 * THIS IS THE HUMAN IN THE LOOP, AS A TOOL.
 *
 * The agent, in the middle of a turn, calls `ask`. The call BLOCKS until the
 * owner answers, and the answer comes back as the tool's result. The agent
 * is not told "the owner will answer later" — it is SUSPENDED, with its
 * context intact, on the question.
 *
 * WHY A TOOL AND NOT A CONVENTION: a convention ("end your turn with
 * PENDENCIA: ...") is a promise the model may keep, may forget, or may
 * phrase differently. A tool is a capability: the model cannot ask the owner
 * anything without calling it, and the call is what suspends the turn.
 *
 * WHY AN MCP SERVER AND NOT A SEVENTH TOOL ON THE API: the api's surface is
 * exactly six tools, it is drift-guarded, and a seventh is a CONTRACT CHANGE
 * (ADR-011). Worse, asking the owner is not a store operation — the api is
 * the DOM's door, and the owner is not the DOM. This server is the AGENT's
 * tool surface, which is a different surface, in a different process, next
 * to the agent that owns the question.
 *
 * WHY IT RUNS OVER STDIO: the agent spawns its MCP servers, so this server
 * is the agent's child — one per session, with the session's own lifetime.
 * The session id travels in the environment (the harness puts it there when
 * it spawns the agent) and, as a second witness, in the agent's own command
 * line. Two witnesses that DISAGREE are a refusal: a question asked in the
 * wrong conversation is worse than no question at all.
 *
 * THE WAITING: the call registers the question with the harness, then polls
 * for the answer until it comes, the deadline passes, or the question is
 * abandoned. Polling and not a held socket: the answer lives in the
 * harness's SQLite, so it survives a restart of anything but this process,
 * and a held socket would die with it.
 */

import { readFileSync } from "node:fs";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

/** The harness's own door — the same process that runs the agent. */
const HARNESS_URL = (
  process.env.OWNER_HARNESS_URL || `http://127.0.0.1:${process.env.HARNESS_PORT || 8002}`
).replace(/\/+$/, "");

/** How often the waiting call looks for the answer. */
const POLL_MS = Number(process.env.OWNER_POLL_MS || 1000);

/**
 * The session id, from the two witnesses.
 *
 * 1. the environment — the harness put it there when it spawned the agent,
 *    and the agent passes its environment to the servers it spawns;
 * 2. the agent's command line — the harness ALWAYS passes `--session-id`,
 *    and the parent of this process IS the agent.
 *
 * If they disagree, the answer is unknown, and an unknown session is a
 * refusal: the tool returns an error instead of asking somebody else.
 */
function resolveSessionId() {
  const fromEnv = String(process.env.IKIGAI_SESSION_ID || "").trim();
  let fromArgs = "";
  try {
    const cmdline = readFileSync(`/proc/${process.ppid}/cmdline`, "utf8");
    const parts = cmdline.split("\0");
    const index = parts.findIndex((part) => part === "--session-id");
    if (index >= 0 && parts[index + 1]) fromArgs = parts[index + 1].trim();
  } catch {
    // No /proc, no parent, no second witness. The environment still counts.
  }
  if (fromEnv && fromArgs && fromEnv !== fromArgs) {
    return { ok: false, reason: `the session id disagrees: env=${fromEnv} args=${fromArgs}` };
  }
  const session = fromEnv || fromArgs;
  if (!session) {
    return { ok: false, reason: "the session id is unknown" };
  }
  return { ok: true, session };
}

/** Register the question with the harness. */
async function askHarness(payload) {
  const response = await fetch(`${HARNESS_URL}/v1/owner/ask`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok || !body.ok) {
    throw new Error(body.error || `the harness refused the question (HTTP ${response.status})`);
  }
  return body.question;
}

/** Look for the answer. */
async function readAnswer(questionId) {
  const response = await fetch(`${HARNESS_URL}/v1/owner/answer?question_id=${encodeURIComponent(questionId)}`);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error || `the harness did not answer (HTTP ${response.status})`);
  return body;
}

const server = new McpServer(
  { name: "ikigai-owner", version: "1.0.0" },
  {
    capabilities: { tools: {} },
    instructions:
      "The owner is the person who reads the chat. Call `ask` when the routine needs a decision " +
      "that only the owner can make — a classification the evidence does not settle, a choice " +
      "between two readings. The call waits for the answer, so you will receive it as the tool " +
      "result. Do not guess, and do not ask a question whose answer is already in the store.",
  },
);

server.registerTool(
  "ask",
  {
    title: "Ask the owner",
    description:
      "Ask the owner a question and WAIT for the answer. Use it when the work needs a decision " +
      "that only the owner can make. The call blocks until the owner answers or the deadline " +
      "passes; the answer comes back as the tool result.",
    inputSchema: {
      question: z.string().describe("The question, in one sentence, in the owner's language."),
      kind: z
        .enum(["choice", "confirm", "text", "editor"])
        .optional()
        .describe(
          "choice: the owner picks one of `options`. confirm: yes or no. " +
            "text: the owner writes a line. editor: the owner writes several lines.",
        ),
      options: z
        .array(z.string())
        .optional()
        .describe("The options, for `choice`. Each one is a value the owner can pick."),
      timeout_ms: z.number().int().positive().optional().describe("The ceiling of the wait."),
    },
  },
  async (args) => {
    const resolved = resolveSessionId();
    if (!resolved.ok) {
      // Fail closed: without a session the question has no addressee.
      return {
        isError: true,
        content: [{ type: "text", text: `The question could not be asked: ${resolved.reason}.` }],
      };
    }

    let question;
    try {
      question = await askHarness({
        session: resolved.session,
        question: args.question,
        kind: args.kind || "text",
        options: args.options || [],
        timeout_ms: args.timeout_ms || null,
      });
    } catch (err) {
      return {
        isError: true,
        content: [{ type: "text", text: `The question could not be asked: ${err.message}` }],
      };
    }

    // The wait. The deadline belongs to the question, not to this loop: the
    // harness decides when a question is expired, so a restart here cannot
    // extend a question's life.
    const deadline = Number(question.deadline_at) || Date.now() + 15 * 60 * 1000;
    while (Date.now() < deadline) {
      await new Promise((resolve) => setTimeout(resolve, POLL_MS));
      let state;
      try {
        state = await readAnswer(question.id);
      } catch (err) {
        return {
          isError: true,
          content: [{ type: "text", text: `The answer could not be read: ${err.message}` }],
        };
      }
      if (state.state === "answered") {
        return { content: [{ type: "text", text: String(state.value ?? "") }] };
      }
      if (state.state === "expired") {
        return {
          isError: true,
          content: [
            {
              type: "text",
              text: "The owner did not answer in time. Continue with your best reading and say that the owner did not answer.",
            },
          ],
        };
      }
    }
    return {
      isError: true,
      content: [{ type: "text", text: "The owner did not answer in time." }],
    };
  },
);

const transport = new StdioServerTransport();
await server.connect(transport);
