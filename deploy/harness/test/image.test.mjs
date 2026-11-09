/**
 * THE IMAGE CARRIES THE HARNESS.
 *
 * The image copies the harness's modules ONE BY ONE — and a module that is
 * not copied is a module the container does not have. The symptom is not a
 * build failure: the image builds, the container starts, and the import
 * fails at boot, so the agent is down and the reason is a line in a
 * Dockerfile that nobody read.
 *
 * This is not hypothetical: `stop.mjs` was written, imported by `server.mjs`,
 * tested, and NOT copied — the container would have failed to start with an
 * import error that says nothing about the cause.
 *
 * So the list of modules on disk and the list in the Dockerfile have to be
 * the same list. A module that is added and not copied fails here, in a
 * sentence that names the file.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const HARNESS = join(HERE, "..");
const DOCKERFILE = join(HARNESS, "Dockerfile");

const read = (path) => readFileSync(path, "utf8");

test("every module of the harness is COPIED into the image", () => {
  const dockerfile = read(DOCKERFILE);
  const modules = readdirSync(HARNESS).filter((name) => name.endsWith(".mjs"));

  assert.ok(modules.length > 0, "the harness has no modules — the test proves nothing");
  for (const file of modules) {
    assert.ok(
      dockerfile.includes(`deploy/harness/${file}`),
      `the image does not carry deploy/harness/${file} — the container would fail to import it`,
    );
  }
});

test("the image copies NO module that the harness does not have", () => {
  const dockerfile = read(DOCKERFILE);
  const copied = [...dockerfile.matchAll(/deploy\/harness\/([\w.-]+\.mjs)/g)].map((m) => m[1]);

  for (const file of copied) {
    assert.ok(
      readdirSync(HARNESS).includes(file),
      `the image copies deploy/harness/${file}, which does not exist — the build fails`,
    );
  }
});
