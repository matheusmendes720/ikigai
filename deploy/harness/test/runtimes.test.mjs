/**
 * The routing table: which client reaches which runtime.
 *
 * These are the tests of a FAIL-CLOSED table. The cases that matter are the
 * ones where the table is wrong: a runtime that names a provider the
 * container does not have, a client routed to a runtime that does not exist,
 * a typo in an id. In each of them the answer must be a refusal WITH a
 * reason — never a silent fallback that looks like success.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  DEFAULT_RUNTIME_ID,
  buildRegistry,
  describeRuntime,
  readRegistryConfig,
  routeClient,
} from "../runtimes.mjs";

const ENV = {
  HARNESS_PROVIDER_ID: "harness",
  HARNESS_MODEL_ID: "MiniMax-M2.7",
  HARNESS_FALLBACK_PROVIDER: "deepseek",
  HARNESS_FALLBACK_MODEL: "deepseek-flash",
};

test("with no configuration there is ONE runtime, and it is the old behaviour", () => {
  const registry = buildRegistry({ env: ENV, config: null });
  assert.equal(registry.default, DEFAULT_RUNTIME_ID);
  assert.equal(registry.runtimes.size, 1);
  const runtime = registry.runtimes.get(DEFAULT_RUNTIME_ID);
  assert.equal(runtime.provider, "harness");
  assert.equal(runtime.model, "MiniMax-M2.7");
  // No list means EVERY published routine.
  assert.equal(runtime.routines, null);
  assert.deepEqual(registry.problems, []);
});

test("a client is routed to the runtime the table names", () => {
  const registry = buildRegistry({
    env: ENV,
    config: {
      runtimes: {
        owner: { provider: "harness", model: "MiniMax-M2.7" },
        archive: { provider: "deepseek", model: "deepseek-flash", routines: ["store-read"] },
      },
      clients: { "tg:111": "archive" },
    },
  });
  const routed = routeClient(registry, "tg:111");
  assert.equal(routed.runtime.id, "archive");
  assert.equal(routed.routed, true);
  assert.equal(routed.reason, "");
});

test("a client nobody routed gets the DEFAULT, and says so", () => {
  const registry = buildRegistry({
    env: ENV,
    config: { runtimes: { owner: { provider: "harness" } }, clients: {} },
  });
  const routed = routeClient(registry, "tg:999");
  assert.equal(routed.runtime.id, "owner");
  assert.equal(routed.routed, false);
  assert.match(routed.reason, /default runtime/);
});

test("a runtime that names an unknown provider is REFUSED, with the reason", () => {
  const registry = buildRegistry({
    env: ENV,
    config: { runtimes: { ghost: { provider: "openai", model: "gpt" } } },
  });
  assert.equal(registry.runtimes.has("ghost"), false);
  assert.equal(registry.problems.length, 1);
  assert.match(registry.problems[0], /ghost/);
  assert.match(registry.problems[0], /not configured/);
  // And the client that wanted it falls back to the default.
  const routed = routeClient(registry, "tg:1");
  assert.equal(routed.runtime.id, DEFAULT_RUNTIME_ID);
});

test("a client routed to a runtime that does not exist is refused, not honoured", () => {
  const registry = buildRegistry({
    env: ENV,
    config: {
      runtimes: { owner: { provider: "harness" } },
      clients: { "tg:1": "nowhere" },
    },
  });
  assert.equal(registry.clients.has("tg:1"), false);
  assert.match(registry.problems[0], /does not exist/);
  const routed = routeClient(registry, "tg:1");
  assert.equal(routed.runtime.id, DEFAULT_RUNTIME_ID);
});

test("a runtime id that is not a slug is refused", () => {
  const registry = buildRegistry({
    env: ENV,
    config: { runtimes: { "Not A Slug": { provider: "harness" } } },
  });
  assert.match(registry.problems[0], /slug/);
});

test("a runtime may NARROW the routines it runs", () => {
  const registry = buildRegistry({
    env: ENV,
    config: {
      runtimes: { reader: { provider: "deepseek", routines: ["store-read"] } },
    },
  });
  const described = describeRuntime(registry.runtimes.get("reader"), [
    "daily-note",
    "store-read",
  ]);
  assert.deepEqual(described.routines, ["store-read"]);
  assert.equal(described.narrowed, true);
});

test("a runtime that does not narrow runs the whole projection", () => {
  const registry = buildRegistry({ env: ENV, config: { runtimes: { owner: { provider: "harness" } } } });
  const described = describeRuntime(registry.runtimes.get("owner"), ["daily-note", "store-read"]);
  assert.deepEqual(described.routines, ["daily-note", "store-read"]);
  assert.equal(described.narrowed, false);
});

test("the inline configuration is read, and a broken one is refused with a reason", () => {
  const ok = readRegistryConfig({ HARNESS_RUNTIMES: '{"runtimes":{"a":{"provider":"harness"}}}' });
  assert.equal(ok.error, null);
  assert.equal(ok.config.runtimes.a.provider, "harness");

  const broken = readRegistryConfig({ HARNESS_RUNTIMES: "{not json" });
  assert.equal(broken.config, null);
  assert.match(broken.error, /not valid JSON/);
});

test("the default runtime named in the configuration is used when it exists", () => {
  const registry = buildRegistry({
    env: ENV,
    config: {
      default: "archive",
      runtimes: {
        owner: { provider: "harness" },
        archive: { provider: "deepseek" },
      },
    },
  });
  assert.equal(registry.default, "archive");
});

test("a default runtime that does not exist is refused, with the default kept", () => {
  const registry = buildRegistry({
    env: ENV,
    config: { default: "ghost", runtimes: { owner: { provider: "harness" } } },
  });
  assert.equal(registry.default, DEFAULT_RUNTIME_ID);
  assert.match(registry.problems[0], /does not exist/);
});
