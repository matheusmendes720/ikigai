/**
 * THE TABLE THE DEPLOYMENT CARRIES.
 *
 * The routing table is not a fixture: it is `deploy/runtimes.json`, the file
 * the compose mounts into the agent and the harness re-reads when its mtime
 * changes. A table the registry REFUSES is a deployment that silently
 * answers every client with the default runtime — the routing would look
 * alive and decide nothing, and the symptom would be a routine that ran on
 * the wrong model.
 *
 * So the table is checked HERE, with the registry's OWN code: the problems it
 * reports have to be empty. Not a second implementation of the rules — the
 * rules, applied to the file that ships.
 *
 * And the providers the table names have to be the ones the DEPLOYMENT
 * configures. A runtime that names a provider the container does not have is
 * refused, and the refusal is invisible from outside: the client simply gets
 * the default. So the provider names are READ from the compose, not assumed.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { buildRegistry, routeClient } from "../runtimes.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const DEPLOY = join(HERE, "..", "..");
const TABLE = join(DEPLOY, "runtimes.json");
const COMPOSE = join(DEPLOY, "compose.yml");

const read = (path) => readFileSync(path, "utf8");

/** The provider names the DEPLOYMENT configures, read from the compose. */
function deploymentProviders() {
  const compose = read(COMPOSE);
  const named = (variable) => {
    const match = compose.match(new RegExp(`${variable}: \\$\\{${variable}:-([A-Za-z0-9_-]+)\\}`));
    return match ? match[1] : "";
  };
  return {
    HARNESS_PROVIDER_ID: named("HARNESS_PROVIDER_ID"),
    HARNESS_FALLBACK_PROVIDER: named("HARNESS_FALLBACK_PROVIDER"),
  };
}

test("the deployment's routing table is ACCEPTED by the registry", () => {
  const config = JSON.parse(read(TABLE));
  const registry = buildRegistry({ env: deploymentProviders(), config });

  assert.deepEqual(
    registry.problems,
    [],
    "the routing table the deployment carries is refused — every client would fall back to the default runtime: "
      + registry.problems.join("; "),
  );
});

test("the table routes AT LEAST ONE client", () => {
  const config = JSON.parse(read(TABLE));
  const registry = buildRegistry({ env: deploymentProviders(), config });

  const routed = [...registry.clients.keys()];
  assert.ok(
    routed.length > 0,
    "the deployment's table routes nobody — the routing would look alive and decide nothing",
  );
  for (const client of routed) {
    const answer = routeClient(registry, client);
    assert.equal(answer.routed, true, `the client ${client} has a rule and is not routed`);
    assert.equal(answer.reason, "", "a routed client has no reason to explain");
  }
});

test("the default runtime of the table EXISTS", () => {
  const config = JSON.parse(read(TABLE));
  const registry = buildRegistry({ env: deploymentProviders(), config });

  assert.ok(
    registry.runtimes.has(registry.default),
    `the table's default runtime "${registry.default}" does not exist`,
  );
});

test("the compose MOUNTS the table and NAMES it", () => {
  const compose = read(COMPOSE);
  const table = "/etc/ikigai/runtimes.json";

  assert.ok(
    compose.includes(`- ./runtimes.json:${table}:ro`),
    "the deployment does not mount the routing table — the agent would carry the table of nobody",
  );
  assert.ok(
    compose.includes(`HARNESS_RUNTIMES_FILE: ${"${HARNESS_RUNTIMES_FILE:-" + table + "}"}`),
    "the deployment does not tell the agent WHERE the table is",
  );
});
