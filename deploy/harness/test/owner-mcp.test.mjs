/**
 * The `ask` tool, end to end, over a real MCP connection.
 *
 * This is the test that matters most in the whole chain, because it is the
 * one that proves the HUMAN IN THE LOOP is real and not a convention:
 *
 *   the agent calls `ask`  →  the question is REGISTERED  →  the owner
 *   answers  →  the CALL RETURNS, with the answer, to the agent that is
 *   suspended on it.
 *
 * There is no `pi` in this test, and no mock of the agent: the tool server
 * is the real one, the broker is the real one, the memory is the real one,
 * and the MCP conversation is spoken over the real stdio transport (newline
 * delimited JSON-RPC, as the protocol says).
 *
 * The harness is the ONE piece faked here — a real HTTP server with the two
 * routes the tool uses, backed by the real broker. The reason is the
 * environment: the tool talks to the harness over HTTP, and the harness
 * that would answer it is the one that runs the agent.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { Memory } from "../memory.mjs";
import { Owner } from "../owner.mjs";

const HERE = fileURLToPath(new URL(".", import.meta.url));
const SERVER = join(HERE, "..", "owner-mcp.mjs");

/** The harness's two routes, backed by the real broker. */
async function startHarness(memory) {
  const owner = new Owner({ memory, defaultTimeoutMs: 30_000 });
  const server = createServer(async (req, res) => {
    const url = new URL(req.url, "http://localhost");
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    const body = chunks.length ? JSON.parse(Buffer.concat(chunks).toString("utf8")) : {};
    const json = (status, payload) => {
      res.writeHead(status, { "content-type": "application/json" });
      res.end(JSON.stringify(payload));
    };
    if (req.method === "POST" && url.pathname === "/v1/owner/ask") {
      const asked = owner.ask({
        session: body.session,
        question: body.question,
        kind: body.kind,
        options: body.options,
        timeoutMs: body.timeout_ms,
      });
      return json(asked.ok ? 200 : 400, asked.ok ? { ok: true, question: asked.question } : asked);
    }
    if (req.method === "GET" && url.pathname === "/v1/owner/answer") {
      const read = owner.read(url.searchParams.get("question_id"));
      return json(read.ok ? 200 : 404, read);
    }
    return json(404, { ok: false, error: "not found" });
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();
  return {
    owner,
    url: `http://127.0.0.1:${port}`,
    close: () => new Promise((resolve) => server.close(resolve)),
  };
}

/** A client that speaks MCP over the child's stdio. */
function speak(harnessUrl) {
  const child = spawn("node", [SERVER], {
    env: {
      ...process.env,
      IKIGAI_SESSION_ID: "tg-test",
      OWNER_POLL_MS: "50",
      OWNER_HARNESS_URL: harnessUrl,
    },
    stdio: ["pipe", "pipe", "pipe"],
  });
  const pending = new Map();
  let buffer = "";
  child.stdout.on("data", (chunk) => {
    buffer += chunk.toString("utf8");
    let index = buffer.indexOf("\n");
    while (index >= 0) {
      const line = buffer.slice(0, index).trim();
      buffer = buffer.slice(index + 1);
      if (line) {
        const message = JSON.parse(line);
        const resolver = pending.get(message.id);
        if (resolver) {
          pending.delete(message.id);
          resolver(message);
        }
      }
      index = buffer.indexOf("\n");
    }
  });
  let nextId = 1;
  const send = (method, params) =>
    new Promise((resolve) => {
      const id = nextId++;
      pending.set(id, resolve);
      child.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", id, method, params })}\n`);
    });
  const notify = (method, params) =>
    child.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", method, params })}\n`);
  return { child, send, notify };
}

test("the `ask` tool BLOCKS until the owner answers, and returns the answer", async () => {
  const dir = mkdtempSync(join(tmpdir(), "ikigai-mcp-"));
  const memory = new Memory(join(dir, "memory.sqlite"));
  const harness = await startHarness(memory);
  const client = speak(harness.url);
  try {
    await client.send("initialize", {
      protocolVersion: "2025-06-18",
      capabilities: {},
      clientInfo: { name: "test", version: "1.0.0" },
    });
    client.notify("notifications/initialized", {});

    const listed = await client.send("tools/list", {});
    const names = (listed.result?.tools || []).map((tool) => tool.name);
    assert.deepEqual(names, ["ask"], "the agent's tool surface is exactly ONE tool: ask");

    // The call goes out and does NOT come back: the agent is suspended.
    const call = client.send("tools/call", {
      name: "ask",
      arguments: {
        question: "Isto é uma nota ou um sonho?",
        kind: "choice",
        options: ["nota", "sonho"],
      },
    });

    // The question reaches the harness, with the SESSION of the caller.
    let pending = [];
    for (let attempt = 0; attempt < 50; attempt += 1) {
      pending = harness.owner.pending("tg-test");
      if (pending.length) break;
      await new Promise((resolve) => setTimeout(resolve, 20));
    }
    assert.equal(pending.length, 1, "the question was registered");
    assert.equal(pending[0].question, "Isto é uma nota ou um sonho?");
    assert.deepEqual(pending[0].options, ["nota", "sonho"]);

    // The owner answers.
    const answered = harness.owner.answer(pending[0].id, "sonho");
    assert.equal(answered.ok, true);

    const result = await call;
    assert.equal(result.result?.isError, undefined);
    assert.equal(result.result?.content?.[0]?.text, "sonho");
  } finally {
    client.child.kill();
    await harness.close();
    memory.close();
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a question nobody answers ends with an ERROR, not with a hang", async () => {
  const dir = mkdtempSync(join(tmpdir(), "ikigai-mcp-"));
  const memory = new Memory(join(dir, "memory.sqlite"));
  const harness = await startHarness(memory);
  const client = speak(harness.url);
  try {
    await client.send("initialize", {
      protocolVersion: "2025-06-18",
      capabilities: {},
      clientInfo: { name: "test", version: "1.0.0" },
    });
    client.notify("notifications/initialized", {});

    // A question with a ceiling of one second, and an owner who never answers.
    const call = client.send("tools/call", {
      name: "ask",
      arguments: { question: "Alguém me ouve?", kind: "text", timeout_ms: 1000 },
    });

    const result = await call;
    assert.equal(result.result?.isError, true);
    assert.match(result.result.content[0].text, /did not answer/);
  } finally {
    client.child.kill();
    await harness.close();
    memory.close();
    rmSync(dir, { recursive: true, force: true });
  }
});
