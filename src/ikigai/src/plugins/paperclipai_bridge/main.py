from __future__ import annotations

import logging
import os
import shutil
import sys
import time as _time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from agents.paperclip.agents.claude import ClaudeAdapter
from agents.paperclip.agents.omo import OmoAdapter
from agents.paperclip.agents.openclaw import OpenClawAdapter
from agents.paperclip.agents.pi import PiAdapter
from agents.paperclip.graph import _build_paperclip_graph
from agents.paperclip.persistence import build_record_from_state, persist_run
from agents.paperclip.policy import (
    DEFAULT_RISK_KEYWORDS,
    DEFAULT_THRESHOLD_S,
    DEFAULT_THRESHOLD_USD,
    CostGate,
    RiskGate,
    WallClockGate,
)
from agents.paperclip.router import ADAPTER_PRIORITY, AdapterHealth, SpecContext, pick_adapter

from .schemas import (
    InvokeRequest,
    InvokeResponse,
    IssueSyncRequest,
    IssueSyncResponse,
    StatusResponse,
    VaultSyncRequest,
    VaultSyncResponse,
)

log = logging.getLogger("paperclipai_bridge")

# Adapter class per router decision name (kept at module level: the router
# returns a name, the concrete class is resolved here for callers).
ADAPTER_CLASSES: dict[str, type] = {
    "claude": ClaudeAdapter,
    "pi": PiAdapter,
    "omo": OmoAdapter,
    "openclaw": OpenClawAdapter,
}

PAPERCLIPAI_BRIDGE_VERSION = "0.1.0"
DEFAULT_VAULT_ROOT = Path("vault").resolve()


app = FastAPI(
    title="paperclipai_bridge",
    version=PAPERCLIPAI_BRIDGE_VERSION,
    description="IPC bridge between PaperclipAI plugin and life-oss Paperclip graph.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _vault_root() -> Path:
    root = os.environ.get("LIFE_VAULT_ROOT")
    return Path(root).resolve() if root else DEFAULT_VAULT_ROOT


def _graph_invoke(req: InvokeRequest) -> InvokeResponse:
    task_id = req.task_id or f"pc-ai-{uuid.uuid4().hex[:8]}"

    health = {
        n: AdapterHealth(
            name=n, on_path=shutil.which(n) is not None, last_invoked_at=None, last_success=None
        )
        for n in ("claude", "pi", "omo", "openclaw")
    }
    try:
        decision = pick_adapter(
            SpecContext(task_id=task_id, spec_text=req.spec_text, cost_today_usd=0.0), health
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"router error: {exc}") from exc

    ckpt = Path(os.environ.get("PAPERCLIP_CHECKPOINT_DB", "data/paperclip.db")).resolve()
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    graph = _build_paperclip_graph(checkpoint_db=str(ckpt), entry_point="read_spec")

    initial_state = {"task_id": task_id, "spec_text": req.spec_text, "messages": []}
    config = {"configurable": {"thread_id": task_id}}

    gates_consulted = []
    cost_gate = CostGate()
    cost_ok, cost_reason = cost_gate.check()
    gates_consulted.append({"gate": "CostGate", "allowed": cost_ok, "reason": cost_reason})
    if not cost_ok:
        return InvokeResponse(
            task_id=task_id, status="blocked_by_cost", gates_consulted=gates_consulted
        )

    now_iso = _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime())
    started_iso = _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime())
    wall_gate = WallClockGate(task_started_at=started_iso, now_iso=now_iso, threshold_seconds=None)
    wall_ok, wall_reason = wall_gate.check()
    gates_consulted.append({"gate": "WallClockGate", "allowed": wall_ok, "reason": wall_reason})
    if not wall_ok:
        return InvokeResponse(
            task_id=task_id, status="blocked_by_wall", gates_consulted=gates_consulted
        )

    risk_gate = RiskGate(text_to_check=req.spec_text)
    risk_ok, risk_reason = risk_gate.check()
    gates_consulted.append({"gate": "RiskGate", "allowed": risk_ok, "reason": risk_reason})
    if not risk_ok:
        return InvokeResponse(
            task_id=task_id, status="blocked_by_risk", gates_consulted=gates_consulted
        )

    run_started_mono = _time.monotonic()
    steps = []
    final_values: dict[str, Any] = {}
    graph_error: str | None = None

    try:
        for event in graph.stream(initial_state, config=config):
            for node_name, partial in event.items():
                if node_name.startswith("__"):
                    continue
                steps.append(
                    {"node": node_name, "ts": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime())}
                )
                if partial.get("error_type"):
                    final_values = partial
                    break
        try:
            final_state = graph.get_state(config)
            if final_state and final_state.values:
                final_values = final_state.values
        except Exception:
            pass
    except Exception as exc:
        graph_error = f"{type(exc).__name__}: {exc}"

    finished_iso = _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime())
    duration_s = round(_time.monotonic() - run_started_mono, 3)

    persisted_path: Path | None = None
    try:
        safe_state = {
            k: v
            for k, v in final_values.items()
            if k
            in (
                "commit_sha",
                "worktree_path",
                "branch_name",
                "error_type",
                "error_message",
                "last_step",
                "implement_iteration",
                "tests_ok",
            )
            and isinstance(v, (str, int, float, bool, list, dict, type(None)))
        }
        record = build_record_from_state(
            task_id=task_id,
            adapter=decision.adapter,
            started_at=started_iso,
            finished_at=finished_iso,
            steps=steps,
            final_state=safe_state,
            gates_consulted=gates_consulted,
            error=graph_error,
        )
        record.duration_s = duration_s
        persisted_path = persist_run(record)
    except Exception as exc:
        log.warning("persist_run failed (non-fatal): %s", exc)

    status = "error" if graph_error or final_values.get("error_type") else "ok"
    return InvokeResponse(
        task_id=task_id,
        run_id=persisted_path.stem if persisted_path else None,
        status=status,
        commit_sha=final_values.get("commit_sha"),
        worktree_path=final_values.get("worktree_path"),
        branch_name=final_values.get("branch_name") or req.branch_name,
        steps=steps,
        duration_s=duration_s,
        error_type=final_values.get("error_type"),
        error_message=final_values.get("error_message") or graph_error,
        gates_consulted=gates_consulted,
    )


def _sync_issue(req: IssueSyncRequest) -> IssueSyncResponse:
    vault = _vault_root()
    date_dir = req.created_at[:10] if req.created_at else _time.strftime("%Y-%m-%d")
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in req.title)[:60]
    file_name = f"{date_dir}_{safe_title}.md"
    vault_entry = vault / "paperclipai_sync" / file_name
    vault_entry.parent.mkdir(parents=True, exist_ok=True)

    frontmatter_lines = [
        "---",
        f"issue_id: {req.issue_id}",
        f"title: {req.title}",
        f"status: {req.status or 'open'}",
        f"author: {req.author or 'unknown'}",
        f"labels: [{', '.join(req.labels)}]",
        f"created_at: {req.created_at}",
        f"synced_at: {_time.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "---",
        "",
    ]
    vault_entry.write_text("\n".join(frontmatter_lines) + req.body, encoding="utf-8")
    return IssueSyncResponse(vault_path=str(vault_entry), synced=True)


def _sync_vault(req: VaultSyncRequest) -> VaultSyncResponse:
    return VaultSyncResponse(ok=True, comment_url=None)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": PAPERCLIPAI_BRIDGE_VERSION}


@app.post("/invoke", response_model=InvokeResponse)
def invoke(req: InvokeRequest) -> InvokeResponse:
    return _graph_invoke(req)


@app.post("/sync/issues", response_model=IssueSyncResponse)
def sync_issue(req: IssueSyncRequest) -> IssueSyncResponse:
    return _sync_issue(req)


@app.post("/sync/vault", response_model=VaultSyncResponse)
def sync_vault(req: VaultSyncRequest) -> VaultSyncResponse:
    return _sync_vault(req)


@app.get("/status", response_model=StatusResponse)
def status() -> StatusResponse:
    from agents.paperclip.graph import NODES

    return StatusResponse(
        bridge_version=PAPERCLIPAI_BRIDGE_VERSION,
        vault_root=str(_vault_root()),
        graph_nodes=list(NODES),
        adapter_priority=list(ADAPTER_PRIORITY),
        gates={
            "cost": {"threshold_usd": DEFAULT_THRESHOLD_USD, "semantics": "fail-OPEN"},
            "wall_clock": {"threshold_s": DEFAULT_THRESHOLD_S, "semantics": "fail-OPEN"},
            "risk": {"keywords_count": len(DEFAULT_RISK_KEYWORDS), "semantics": "fail-CLOSED"},
        },
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("LIFE_PAPERCLIP_BRIDGE_PORT", "8741"))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
