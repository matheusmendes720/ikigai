import type { PaperclipPluginManifestV1 } from "@paperclipai/plugin-sdk";

export const manifest: PaperclipPluginManifestV1 = {
  id: "life-oss.bridge",
  apiVersion: 1,
  version: "0.1.0",
  displayName: "Life OSS Bridge",
  description:
    "Bridge PaperclipAI agents to the life-oss LangGraph system. Trigger Python graph execution and sync vault issues bidirectionally.",
  author: "Life OSS",
  categories: ["connector"],
  capabilities: [
    "http.outbound",
    "events.subscribe",
    "jobs.schedule",
    "issues.read",
    "issues.create",
    "issues.update",
    "projects.read",
  ],
  entrypoints: {
    worker: "./dist/index.js",
  },
  jobs: [
    {
      jobKey: "vault-sync",
      displayName: "Vault ↔ PaperclipAI Daily Sync",
      description: "Sync open issues from PaperclipAI to the life-oss vault each day at 02:00 UTC.",
      schedule: "0 2 * * *",
    },
  ],
};
