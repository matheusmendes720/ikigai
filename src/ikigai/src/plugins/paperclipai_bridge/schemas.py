from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class InvokeRequest(BaseModel, frozen=True):
    spec_text: str
    task_id: str | None = None
    dry_run: bool = False
    branch_name: str | None = None


class InvokeResponse(BaseModel, frozen=True):
    task_id: str
    run_id: str | None = None
    status: str
    commit_sha: str | None = None
    worktree_path: str | None = None
    branch_name: str | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)
    duration_s: float | None = None
    error_type: str | None = None
    error_message: str | None = None
    gates_consulted: list[dict[str, Any]] = Field(default_factory=list)


class IssueSyncRequest(BaseModel, frozen=True):
    issue_id: str
    title: str
    body: str
    status: str | None = None
    labels: list[str] = Field(default_factory=list)
    author: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class IssueSyncResponse(BaseModel, frozen=True):
    vault_path: str
    synced: bool


class VaultSyncRequest(BaseModel, frozen=True):
    issue_id: str
    vault_path: str
    summary: str
    diff: str | None = None


class VaultSyncResponse(BaseModel, frozen=True):
    ok: bool
    comment_url: str | None = None


class StatusResponse(BaseModel, frozen=True):
    bridge_version: str
    vault_root: str
    graph_nodes: list[str]
    adapter_priority: list[str]
    gates: dict[str, Any]
