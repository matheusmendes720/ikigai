/**
 * The runtime registry: WHICH agentic runtime serves WHICH client.
 *
 * WHY THIS FILE EXISTS: the harness answers a routine by name, and one
 * deployment had exactly one agent behind it — the provider and the model
 * baked into the container's `models.json`. The moment a second client (a
 * second bot token, a second chat, a TUI) appears, "the agent" stops being a
 * single thing: one client may want the strong model and a slow answer, the
 * other a cheap model and a fast one, and a client that must NOT reach the
 * store at all is a client with a different set of routines.
 *
 * So the agent becomes a RUNTIME: a named profile with its own provider, its
 * own model, its own set of routines and its own memory scope. The client
 * does not name a model; the client is ROUTED to one.
 *
 * THE SHAPE:
 *
 *   client (tg:9138296750) ──▶ routing table ──▶ runtime (owner)
 *                                                       ├─ provider: harness
 *                                                       ├─ model:     MiniMax-M2.7
 *                                                       ├─ routines:  daily-note, weekly-review, …
 *                                                       └─ memory:    owner
 *
 * WHY IT FAILS CLOSED: a runtime that names a provider the container does not
 * have, or a client routed to a runtime that does not exist, is REFUSED — with
 * the reason — and the client falls back to the default runtime. A routing
 * table that silently ignored a typo would send an expensive routine to a
 * cheap model, or a client to a runtime that cannot see the store, and the
 * symptom would be a report that is quietly worse.
 *
 * WHY THE CONFIGURATION IS ENVIRONMENT, NOT CODE: the runtimes are a property
 * of a DEPLOYMENT (which keys exist, which model is paid for, which clients
 * are allowed to reach which profile), and a deployment's properties live in
 * its environment — the same rule the house applies to every other secret.
 * With no configuration at all, the registry builds ONE runtime from the
 * container's own provider settings, which is exactly what the harness did
 * before this file existed: the default is the old behaviour, unchanged.
 */

import { readFileSync, existsSync } from "node:fs";

/** The id of the runtime a client gets when nothing routes it elsewhere. */
export const DEFAULT_RUNTIME_ID = "owner";

/**
 * A runtime id is a slug: it becomes part of a session key and of a file
 * name, so it is restricted to the characters that are safe in both.
 */
const SLUG = /^[a-z0-9][a-z0-9_-]{0,31}$/;

/**
 * The client key is the harness's own vocabulary: `tg:<chat_id>` is what the
 * bot sends. It is matched EXACTLY, and a key that is not in the table gets
 * the default runtime — never a near miss.
 */
const CLIENT_KEY = /^[A-Za-z0-9._:-]{1,120}$/;

/**
 * Read the registry out of the environment.
 *
 * Two sources, in this order:
 *
 *   1. `HARNESS_RUNTIMES_FILE` — a JSON file. The readable one: a deployment
 *      with several runtimes has a table, and a table in a JSON string in an
 *      env file is a table nobody can review.
 *   2. `HARNESS_RUNTIMES` — the same JSON, inline. The one-shot one.
 *
 * With neither, the registry is the single default runtime built from the
 * container's own provider settings — the behaviour that existed before.
 */
export function readRegistryConfig(env = process.env) {
  const file = String(env.HARNESS_RUNTIMES_FILE || "").trim();
  if (file) {
    if (!existsSync(file)) {
      return { config: null, error: `HARNESS_RUNTIMES_FILE does not exist: ${file}` };
    }
    try {
      return { config: JSON.parse(readFileSync(file, "utf8")), error: null };
    } catch (err) {
      return {
        config: null,
        error: `HARNESS_RUNTIMES_FILE is not valid JSON: ${err.message}`,
      };
    }
  }
  const inline = String(env.HARNESS_RUNTIMES || "").trim();
  if (!inline) return { config: null, error: null };
  try {
    return { config: JSON.parse(inline), error: null };
  } catch (err) {
    return { config: null, error: `HARNESS_RUNTIMES is not valid JSON: ${err.message}` };
  }
}

/**
 * The provider a runtime may name: the one the container was configured with,
 * and the fallback the container knows how to reach.
 */
export function configuredProviders(env = process.env) {
  const providers = new Set();
  const primary = String(env.HARNESS_PROVIDER_ID || "").trim();
  const fallback = String(env.HARNESS_FALLBACK_PROVIDER || "").trim();
  if (primary) providers.add(primary);
  if (fallback) providers.add(fallback);
  return providers;
}

/**
 * The registry.
 *
 * `runtimes` is a Map of id → profile. `clients` is a Map of client key →
 * runtime id. `problems` is the list of what was REFUSED and why — it is
 * reported by `/v1/routing` and by the health probe, because a routing table
 * that refuses something quietly is a routing table the operator cannot fix.
 */
export function buildRegistry({ env = process.env, config = null } = {}) {
  const problems = [];
  const runtimes = new Map();
  const clients = new Map();

  const providers = configuredProviders(env);
  const primaryProvider = String(env.HARNESS_PROVIDER_ID || "").trim();
  const primaryModel = String(env.HARNESS_MODEL_ID || "").trim();
  const fallbackProvider = String(env.HARNESS_FALLBACK_PROVIDER || "").trim();
  const fallbackModel = String(env.HARNESS_FALLBACK_MODEL || "").trim();

  /** The runtime every deployment has, whether or not it configured any. */
  const fallbackProfile = {
    id: DEFAULT_RUNTIME_ID,
    label: "Default",
    provider: primaryProvider,
    model: primaryModel,
    fallbackProvider,
    fallbackModel,
    // `null` means "every published routine" — the projection is the list.
    routines: null,
    memory: DEFAULT_RUNTIME_ID,
  };

  const raw = config && typeof config === "object" ? config.runtimes : null;
  if (raw && typeof raw === "object") {
    for (const [id, profile] of Object.entries(raw)) {
      if (!SLUG.test(id)) {
        problems.push(`runtime "${id}" is refused: the id must be a slug (a-z, 0-9, _ and -)`);
        continue;
      }
      const provider = String(profile?.provider || "").trim() || primaryProvider;
      if (!provider) {
        problems.push(`runtime "${id}" is refused: it names no provider and none is configured`);
        continue;
      }
      if (providers.size > 0 && !providers.has(provider)) {
        problems.push(
          `runtime "${id}" is refused: provider "${provider}" is not configured ` +
            `(this container knows: ${[...providers].join(", ") || "none"})`,
        );
        continue;
      }
      const model = String(profile?.model || "").trim();
      const routines = Array.isArray(profile?.routines)
        ? profile.routines.map((r) => String(r).trim()).filter(Boolean)
        : null;
      runtimes.set(id, {
        id,
        label: String(profile?.label || id),
        provider,
        model: model || (provider === primaryProvider ? primaryModel : fallbackModel),
        fallbackProvider: String(profile?.fallbackProvider || fallbackProvider || ""),
        fallbackModel: String(profile?.fallbackModel || fallbackModel || ""),
        routines,
        memory: String(profile?.memory || id),
      });
    }
  }

  if (runtimes.size === 0) {
    runtimes.set(DEFAULT_RUNTIME_ID, fallbackProfile);
  } else if (!runtimes.has(DEFAULT_RUNTIME_ID)) {
    // The default id is a NAME the rest of the system uses; it does not have
    // to be a configured runtime, but the fallback profile is always there
    // for a client nobody routed.
    runtimes.set(DEFAULT_RUNTIME_ID, fallbackProfile);
  }

  const rawClients = config && typeof config === "object" ? config.clients : null;
  if (rawClients && typeof rawClients === "object") {
    for (const [client, id] of Object.entries(rawClients)) {
      if (!CLIENT_KEY.test(client)) {
        problems.push(`client "${client}" is refused: the key is not a valid client key`);
        continue;
      }
      const target = String(id || "").trim();
      if (!runtimes.has(target)) {
        problems.push(
          `client "${client}" is refused: it is routed to runtime "${target}", which does not exist`,
        );
        continue;
      }
      clients.set(client, target);
    }
  }

  const declaredDefault = String(config?.default || "").trim();
  const defaultId = runtimes.has(declaredDefault) ? declaredDefault : DEFAULT_RUNTIME_ID;
  if (declaredDefault && !runtimes.has(declaredDefault)) {
    problems.push(
      `the default runtime "${declaredDefault}" does not exist; "${DEFAULT_RUNTIME_ID}" is used instead`,
    );
  }

  return { default: defaultId, runtimes, clients, problems };
}

/**
 * Route one client to one runtime.
 *
 * The answer is ALWAYS a runtime — a client that is not in the table gets the
 * default one — plus the reason, so the caller can tell "routed to the
 * archive runtime" from "routed to the default because the table was
 * silent". The reason is the difference between a working system and a
 * working system nobody trusts.
 */
export function routeClient(registry, client) {
  const key = String(client || "").trim();
  const target = registry.clients.get(key);
  if (target && registry.runtimes.has(target)) {
    return { client: key, runtime: registry.runtimes.get(target), routed: true, reason: "" };
  }
  const runtime = registry.runtimes.get(registry.default);
  return {
    client: key,
    runtime,
    routed: false,
    reason: key ? "no routing rule; the default runtime" : "no client key; the default runtime",
  };
}

/**
 * The public shape of a runtime. The provider's KEY never appears here — the
 * harness holds the credential, not the runtime.
 */
export function describeRuntime(runtime, publishedRoutines = []) {
  const allowed = runtime.routines;
  return {
    id: runtime.id,
    label: runtime.label,
    provider: runtime.provider,
    model: runtime.model,
    memory: runtime.memory,
    // The routines this runtime may run: its own list, or the projection.
    routines: allowed === null ? [...publishedRoutines] : allowed,
    narrowed: allowed !== null,
  };
}
