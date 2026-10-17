import { definePlugin, runWorker } from "@paperclipai/plugin-sdk";
import { manifest } from "./manifest.js";

const BRIDGE_URL =
  process.env.LIFE_PAPERCLIP_BRIDGE_URL ?? "http://127.0.0.1:8741";

interface TaskParams {
  title: string;
  description?: string;
  priority?: string;
  tags?: string[];
}

interface VaultReadParams {
  path: string;
}

interface PlanRunParams {
  goal: string;
}

const plugin = definePlugin({
  async setup(ctx) {
    ctx.tools.register(
      "task-add",
      {
        displayName: "Add Life OSS Task",
        description:
          "Add a task to the life-oss task system via the bridge server.",
        parametersSchema: {
          type: "object",
          properties: {
            title: { type: "string" },
            description: { type: "string" },
            priority: { type: "string", enum: ["low", "medium", "high", "critical"] },
            tags: { type: "array", items: { type: "string" } },
          },
          required: ["title"],
          additionalProperties: false,
        },
      },
      async (params) => {
        const p = params as TaskParams;
        const res = await ctx.http.fetch(`${BRIDGE_URL}/invoke`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            action: "task_add",
            params: { title: p.title, description: p.description, priority: p.priority, tags: p.tags },
          }),
        });
        if (!res.ok) {
          throw new Error(`Bridge error ${res.status}: ${await res.text()}`);
        }
        const json = (await res.json()) as { ok: boolean; data?: unknown; error?: string };
        return {
          content: json.ok
            ? `Task added: ${p.title}`
            : `Failed: ${json.error ?? "unknown"}`,
          data: json.data ?? null,
        };
      }
    );

    ctx.tools.register(
      "vault-read",
      {
        displayName: "Read Vault Note",
        description: "Read a note from the life-oss vault by path.",
        parametersSchema: {
          type: "object",
          properties: {
            path: { type: "string" },
          },
          required: ["path"],
          additionalProperties: false,
        },
      },
      async (params) => {
        const p = params as VaultReadParams;
        const res = await ctx.http.fetch(
          `${BRIDGE_URL}/sync/vault?path=${encodeURIComponent(p.path)}`,
          { method: "GET" }
        );
        if (!res.ok) {
          throw new Error(`Bridge error ${res.status}`);
        }
        const json = (await res.json()) as { content?: string };
        return { content: json.content ?? "", data: json };
      }
    );

    ctx.tools.register(
      "plan-run",
      {
        displayName: "Run Life OSS Plan",
        description: "Trigger the life-oss v2 plan workflow via the bridge server.",
        parametersSchema: {
          type: "object",
          properties: {
            goal: { type: "string" },
          },
          required: ["goal"],
          additionalProperties: false,
        },
      },
      async (params) => {
        const p = params as PlanRunParams;
        const res = await ctx.http.fetch(`${BRIDGE_URL}/invoke`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "plan_run", params: { goal: p.goal } }),
        });
        if (!res.ok) {
          throw new Error(`Bridge error ${res.status}`);
        }
        const json = (await res.json()) as { ok: boolean; data?: unknown };
        return {
          content: json.ok
            ? `Plan triggered for: ${p.goal}`
            : "Plan trigger failed",
          data: json.data ?? null,
        };
      }
    );

    ctx.tools.register(
      "status",
      {
        displayName: "Life OSS Status",
        description: "Health-check the life-oss bridge server.",
        parametersSchema: { type: "object", properties: {}, additionalProperties: false },
      },
      async () => {
        const res = await ctx.http.fetch(`${BRIDGE_URL}/status`, { method: "GET" });
        const json = (await res.json()) as { status: string; version?: string };
        return {
          content: `Bridge status: ${json.status}${json.version ? ` (v${json.version})` : ""}`,
          data: json,
        };
      }
    );

    ctx.events.on("issue.created", async (event) => {
      ctx.logger.info("issue.created received", { issueId: event.entityId });
      try {
        const res = await ctx.http.fetch(`${BRIDGE_URL}/sync/issues`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            source: "paperclipai",
            event: "issue.created",
            entityId: event.entityId,
          }),
        });
        if (!res.ok) {
          ctx.logger.error("Failed to sync issue to vault", {
            issueId: event.entityId,
            status: res.status,
          });
        }
      } catch (err) {
        ctx.logger.error("Bridge call failed for issue.created", {
          issueId: event.entityId,
          error: String(err),
        });
      }
    });

    ctx.events.on("issue.updated", async (event) => {
      ctx.logger.info("issue.updated received", { issueId: event.entityId });
      try {
        const res = await ctx.http.fetch(`${BRIDGE_URL}/sync/issues`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            source: "paperclipai",
            event: "issue.updated",
            entityId: event.entityId,
          }),
        });
        if (!res.ok) {
          ctx.logger.error("Failed to sync issue update to vault", {
            issueId: event.entityId,
            status: res.status,
          });
        }
      } catch (err) {
        ctx.logger.error("Bridge call failed for issue.updated", {
          issueId: event.entityId,
          error: String(err),
        });
      }
    });

    ctx.jobs.register("vault-sync", async (job) => {
      ctx.logger.info("vault-sync job started", {
        runId: job.runId,
        trigger: job.trigger,
      });
      try {
        const res = await ctx.http.fetch(`${BRIDGE_URL}/sync/issues`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            source: "paperclipai",
            event: "scheduled_sync",
          }),
        });
        if (!res.ok) {
          ctx.logger.error("vault-sync job failed", { status: res.status });
          throw new Error(`Sync failed with status ${res.status}`);
        }
        ctx.logger.info("vault-sync job completed", { runId: job.runId });
      } catch (err) {
        ctx.logger.error("vault-sync job threw", { error: String(err) });
        throw err;
      }
    });
  },

  async onHealth() {
    return { status: "ok", message: "Life OSS Bridge plugin running" };
  },
});

export default plugin;
runWorker(plugin, import.meta.url);
