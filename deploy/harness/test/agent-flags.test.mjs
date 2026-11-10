/**
 * THE AGENT KEEPS ITS WAY INTO THE STORE.
 *
 * `piArgs` passes `--no-extensions` on purpose: `RpcClient` does not implement
 * the `extension_ui` sub-protocol, so an extension that opens a dialog would
 * block the agent forever with nobody to answer it.
 *
 * AND THAT FLAG IS WHAT SILENTLY TOOK THE STORE AWAY. `builtin:mcp` is a
 * BUILT-IN EXTENSION — `pi`'s `docs/settings.md` lists it as one and says
 * `--no-extensions` disables them too — so the run that disabled extensions
 * also disabled the six tools. The comment in `piArgs` claimed the opposite
 * ("the MCP client is CORE"), and nothing tested the claim.
 *
 * Measured on the box, 2026-11-10: asked what it had, the agent answered
 * "Ferramentas de um servidor MCP chamado `ikigai`: nenhuma — apenas as quatro
 * ferramentas nativas"; a whole `daily-note` run made **480 tool calls** —
 * 438 `bash`, 0 store tools — building its own JSON-RPC client in Node,
 * because it had no other way in. It then burned its 30-minute ceiling and
 * answered `routine.failed`.
 *
 * The fix is the combination `pi`'s own `docs/cli.md` names:
 * "`pi -ne -e builtin:mcp` keeps only the built-in MCP support".
 *
 * THESE ASSERTIONS RUN ON THE CODE WITH THE COMMENTS STRIPPED, and that is not
 * fussiness: the first version of this test asserted `body.includes(
 * "builtin:mcp")` over the raw source, the new comment block says
 * `builtin:mcp` four times, and the test passed against a source with the FLAG
 * deleted. A test that the prose can satisfy is a test that measures the
 * prose.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const SERVER = join(HERE, "..", "server.mjs");

/** A line of JavaScript with its `//` comment removed. */
const stripComment = (line) => line.replace(/\/\/.*$/, "");

/**
 * The body of `piArgs` with the comments removed — the ARGS, not the prose.
 *
 * The source is read as text because `piArgs` lives inside `server.mjs`, which
 * starts a server when imported.
 */
function piArgsCode() {
  const source = readFileSync(SERVER, "utf8");
  const start = source.indexOf("function piArgs(");
  assert.notEqual(start, -1, "server.mjs no longer defines piArgs — this test measures nothing");
  const opening = source.indexOf("const args = [", start);
  assert.notEqual(opening, -1, "piArgs no longer builds an args array — this test measures nothing");
  const closing = source.indexOf("];", opening);
  assert.notEqual(closing, -1, "piArgs's args array is unterminated");
  return source
    .slice(opening, closing)
    .split("\n")
    .map(stripComment)
    .join("\n");
}

test("the agent is launched with the MCP built-in ON, even with extensions off", () => {
  const code = piArgsCode();

  assert.ok(
    code.includes("--no-extensions"),
    "piArgs stopped disabling extensions: the extension_ui risk the comment names is back",
  );
  assert.ok(
    /["']-e["']\s*,\s*["']builtin:mcp["']/.test(code),
    "piArgs disables extensions without re-enabling builtin:mcp — the agent would start with " +
      "no store tools, script its own JSON-RPC client, and burn the run's ceiling",
  );
});

test("the MCP built-in is named EXACTLY as the agent's docs name it", () => {
  const code = piArgsCode();

  assert.ok(
    code.includes('"builtin:mcp"'),
    "the MCP built-in is not named `builtin:mcp` — pi would load nothing and say nothing",
  );
  assert.ok(
    !code.includes("--no-mcp"),
    "piArgs passes --no-mcp: the run disables MCP support outright, whatever else it loads",
  );
});

test("the project is trusted, or the configuration is never read", () => {
  const code = piArgsCode();

  assert.ok(
    code.includes("--approve"),
    "piArgs no longer approves the project: `.pi/mcp.json` and `.pi/skills/` are only read " +
      "after trust, so the harness would start with no store and no routines",
  );
});
