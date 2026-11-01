"""Paperclip browser dashboard — single-file FastAPI server.

Why this exists: ``langgraph dev`` is broken on Python 3.14 (M97/M98
protobuf ``TypeError: Metaclasses with custom tp_new are not supported``)
so we ship a tiny FastAPI dashboard that invokes Paperclip directly.

What it shows:
- Graph topology (9 nodes + edges) — read from ``graph.NODES``
- Adapter health (4 of 6 on PATH — claude, pi, omo, openclaw)
- Throttle gate thresholds (Cost / WallClock / Risk) — read from ``policy.py``
- Recent runs (in-memory ring; lost on restart, intentional)
- Two run buttons:
  - **DRY RUN** — walks the graph without invoking real CLIs (mock adapter)
  - **LIVE RUN** — invokes real CLIs (may fail in sandbox)

Run:
    python scripts/paperclip-dashboard.py
    # open http://127.0.0.1:8765

Stop:
    Ctrl+C  (or kill the background bash)
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import sys
import time
import uuid
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Path setup — add <repo>/src to sys.path so paperclip imports resolve.
# ---------------------------------------------------------------------------
THIS = Path(__file__).resolve()
REPO_ROOT = THIS.parent.parent
SRC_ROOT = REPO_ROOT / "src"
for _p in (str(REPO_ROOT), str(SRC_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ---------------------------------------------------------------------------
# Paperclip imports (verified at startup; friendly error if missing)
# ---------------------------------------------------------------------------
log = logging.getLogger("paperclip.dashboard")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)

PAPERCLIP_IMPORT_ERROR: str | None = None
try:
    from src.ikigai.src.agents.paperclip.agents.claude import ClaudeAdapter
    from src.ikigai.src.agents.paperclip.agents.omo import OmoAdapter
    from src.ikigai.src.agents.paperclip.agents.openclaw import OpenClawAdapter
    from src.ikigai.src.agents.paperclip.agents.pi import PiAdapter
    from src.ikigai.src.agents.paperclip.graph import (
        NODES,
        _build_paperclip_graph,
    )
    from src.ikigai.src.agents.paperclip.policy import (
        DEFAULT_RISK_KEYWORDS,
        DEFAULT_THRESHOLD_S,
        DEFAULT_THRESHOLD_USD,
    )
    from src.ikigai.src.agents.paperclip.policy import (
        ENV_THRESHOLD as COST_ENV,
    )
    from src.ikigai.src.agents.paperclip.router import (
        ADAPTER_PRIORITY,
        pick_adapter,
    )

    PAPERCLIP_IMPORT_ERROR = None
except Exception as exc:
    PAPERCLIP_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"
    log.error("paperclip import failed: %s", PAPERCLIP_IMPORT_ERROR)
    # Don't bail — start the server anyway so the UI can show "import failed".

# ---------------------------------------------------------------------------
# In-memory run store (lost on process restart — intentional for MVP)
# ---------------------------------------------------------------------------
MAX_RUNS = 50
runs: deque[dict[str, Any]] = deque(maxlen=MAX_RUNS)

# Background tasks are referenced here: an unreferenced task may be garbage
# collected before it finishes.
_BACKGROUND_TASKS: set[asyncio.Task[None]] = set()


def _record_run(run: dict[str, Any]) -> None:
    runs.appendleft(run)


# ---------------------------------------------------------------------------
# Adapter health probing
# ---------------------------------------------------------------------------
def _adapter_health() -> list[dict[str, Any]]:
    """Snapshot of all 6 declared adapters: PATH presence + type (real/stub)."""
    adapter_specs = [
        ("claude", ClaudeAdapter),
        ("pi", PiAdapter),
        ("omo", OmoAdapter),
        ("openclaw", OpenClawAdapter),
        # mmx-cli / hermes stay stubs — binaries missing.
    ]
    out = []
    for name, cls in adapter_specs:
        adapter = cls()
        # Real adapters ship a working .run(); stubs raise NotImplementedError.
        is_real = hasattr(adapter, "run") and cls.__module__.endswith(name)
        on_path = shutil.which(name) is not None
        out.append(
            {
                "name": name,
                "on_path": on_path,
                "type": "real" if is_real else "stub",
                "timeout_s": getattr(adapter, "timeout_s", 0),
            }
        )
    # Stub entries for mmx-cli + hermes (binaries not installed)
    out.append({"name": "mcode", "on_path": False, "type": "stub", "timeout_s": 180})
    out.append({"name": "hermes", "on_path": False, "type": "stub", "timeout_s": 180})
    out.sort(
        key=lambda r: ADAPTER_PRIORITY.index(r["name"]) if r["name"] in ADAPTER_PRIORITY else 99
    )
    return out


# ---------------------------------------------------------------------------
# Gate snapshot
# ---------------------------------------------------------------------------
def _gate_snapshot() -> dict[str, Any]:
    """Read current thresholds from policy module state + env."""
    return {
        "cost": {
            "class": "CostGate",
            "threshold_usd": float(os.environ.get(COST_ENV, DEFAULT_THRESHOLD_USD)),
            "env_var": COST_ENV,
            "semantics": "fail-OPEN",
            "milestone": "M173",
        },
        "wall_clock": {
            "class": "WallClockGate",
            "threshold_s": int(
                os.environ.get("PAPERCLIP_WALL_CLOCK_THRESHOLD_S", DEFAULT_THRESHOLD_S)
            ),
            "env_var": "PAPERCLIP_WALL_CLOCK_THRESHOLD_S",
            "semantics": "fail-OPEN",
            "milestone": "M175",
        },
        "risk": {
            "class": "RiskGate",
            "keywords_count": len(DEFAULT_RISK_KEYWORDS),
            "env_var": "PAPERCLIP_RISK_KEYWORDS",
            "semantics": "fail-CLOSED",
            "milestone": "M176",
            "keywords": list(DEFAULT_RISK_KEYWORDS),
        },
    }


# ---------------------------------------------------------------------------
# Graph topology (read from NODES + routing functions)
# ---------------------------------------------------------------------------
GRAPH_EDGES = [
    # read_spec → spec_analyzer (always)
    ("read_spec", "spec_analyzer", "always"),
    # spec_analyzer → hil_pause | worktree_create | END
    ("spec_analyzer", "hil_pause", "spec_gaps non-empty"),
    ("spec_analyzer", "worktree_create", "spec clean"),
    ("spec_analyzer", "END", "error"),
    # hil_pause → merge_user_resolution (always)
    ("hil_pause", "merge_user_resolution", "always"),
    # merge → spec_analyzer (loop back)
    ("merge_user_resolution", "spec_analyzer", "always (loop)"),
    # worktree_create → implement
    ("worktree_create", "implement", "always"),
    # implement → worktree_commit | implement (loop on test fail)
    ("implement", "worktree_commit", "tests pass"),
    ("implement", "implement", "tests fail (loop)"),
    ("implement", "END", "error"),
    # commit → merge
    ("worktree_commit", "worktree_merge", "always"),
    # merge → cleanup
    ("worktree_merge", "worktree_cleanup", "always"),
    ("worktree_merge", "END", "merge conflict"),
    # cleanup → END
    ("worktree_cleanup", "END", "always"),
]


# ---------------------------------------------------------------------------
# Mock adapter for DRY RUN
# ---------------------------------------------------------------------------
class _DryRunAdapter:
    """Returns success without invoking any CLI. Used for DRY RUN button."""

    name = "dry-run"
    timeout_s = 1

    def run(self, prompt, cwd, *, timeout_s=None):
        return AgentResult.__class__(  # type: ignore[attr-defined]
            success=True,
            output="[dry-run] would have invoked AI adapter here",
            duration_s=0.0,
        )


# Lazy import shim for AgentResult (pydantic v2 strict)
try:
    from src.ikigai.src.agents.paperclip.agents.base import AgentResult

    _DryRunAdapter.run = lambda self, prompt, cwd, *, timeout_s=None: AgentResult(  # type: ignore[assignment]
        success=True,
        output=f"[dry-run] would invoke AI adapter on prompt of {len(prompt)} chars in {cwd}",
        duration_s=0.0,
    )
except Exception:
    pass


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Paperclip Dashboard", version="0.1.0")


class InvokeRequest(BaseModel):
    spec_text: str
    task_id: str | None = None
    dry_run: bool = False


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok" if PAPERCLIP_IMPORT_ERROR is None else "degraded",
        "paperclip_import_error": PAPERCLIP_IMPORT_ERROR,
        "ts": datetime.now(UTC).isoformat(),
        "uptime_s": int(time.time() - SERVER_START_TS),
    }


@app.get("/api/graph")
async def graph() -> dict[str, Any]:
    return {
        "nodes": list(NODES),
        "edges": [{"from": a, "to": b, "condition": c} for (a, b, c) in GRAPH_EDGES],
    }


@app.get("/api/adapters")
async def adapters() -> dict[str, Any]:
    return {"priority_order": list(ADAPTER_PRIORITY), "items": _adapter_health()}


@app.get("/api/gates")
async def gates() -> dict[str, Any]:
    return _gate_snapshot()


@app.get("/api/runs")
async def list_runs() -> dict[str, Any]:
    return {"runs": list(runs)}


@app.post("/api/invoke")
async def invoke(req: InvokeRequest) -> dict[str, Any]:
    if PAPERCLIP_IMPORT_ERROR is not None:
        raise HTTPException(
            status_code=503, detail=f"paperclip unavailable: {PAPERCLIP_IMPORT_ERROR}"
        )
    task_id = req.task_id or f"dash-{uuid.uuid4().hex[:8]}"
    run_id = uuid.uuid4().hex[:12]
    started_at = datetime.now(UTC).isoformat()

    record: dict[str, Any] = {
        "run_id": run_id,
        "task_id": task_id,
        "started_at": started_at,
        "finished_at": None,
        "status": "running",
        "dry_run": req.dry_run,
        "spec_chars": len(req.spec_text),
        "steps": [],
        "final_state": None,
        "error": None,
    }
    _record_run(record)

    # Run in background — don't tie up the request thread.
    task = asyncio.create_task(_run_paperclip(record, req.spec_text, req.dry_run))
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)
    return {"run_id": run_id, "task_id": task_id, "status": "started"}


async def _run_paperclip(record: dict[str, Any], spec_text: str, dry_run: bool) -> None:
    """Invoke Paperclip graph in a worker thread; stream progress to ``record``."""
    try:
        # The adapter is chosen BEFORE the graph is built: the graph has to
        # know which adapter its `implement` node must invoke.
        adapter_instance: Any = None
        if dry_run:
            adapter_instance = _DryRunAdapter()
        else:
            # Pick the cheapest healthy adapter
            from src.ikigai.src.agents.paperclip.router import (
                AdapterHealth,
                SpecContext,
            )

            health = {
                a["name"]: AdapterHealth(
                    name=a["name"], on_path=a["on_path"], last_invoked_at=None, last_success=None
                )
                for a in _adapter_health()
            }
            spec_ctx = SpecContext(
                task_id=record["task_id"], spec_text=spec_text, cost_today_usd=0.0
            )
            try:
                decision = pick_adapter(spec_ctx, health)
                adapter_name = decision.adapter
                record["steps"].append(
                    {"node": "router", "decision": adapter_name, "reason": decision.reason}
                )
            except Exception as exc:
                record["status"] = "error"
                record["error"] = f"router failed: {exc}"
                record["finished_at"] = datetime.now(UTC).isoformat()
                return
            cls_map: dict[str, type[Any]] = {
                "claude": ClaudeAdapter,
                "pi": PiAdapter,
                "omo": OmoAdapter,
                "openclaw": OpenClawAdapter,
            }
            adapter_instance = cls_map[adapter_name]()

        # Build the graph fresh per run (SqliteSaver is per-call).
        ckpt = REPO_ROOT / "data" / "paperclip.db"
        ckpt.parent.mkdir(parents=True, exist_ok=True)
        graph = await asyncio.to_thread(
            _build_paperclip_graph,
            checkpoint_db=str(ckpt),
            entry_point="read_spec",
            adapter=adapter_instance,
        )

        config = {"configurable": {"thread_id": record["task_id"]}}
        initial_state = {"task_id": record["task_id"], "spec_text": spec_text, "messages": []}

        # Stream events from the graph (langgraph emits "events" dict per node).
        result = await asyncio.to_thread(_invoke_and_collect, graph, initial_state, config, record)
        record["final_state"] = {
            k: (v if isinstance(v, (str, int, float, bool, list, dict, type(None))) else str(v))
            for k, v in (result or {}).items()
            if k
            in (
                "task_id",
                "spec_gaps",
                "implement_iteration",
                "tests_ok",
                "commit_sha",
                "worktree_path",
                "branch_name",
                "error_type",
                "error_message",
                "last_step",
            )
        }
        record["status"] = "ok" if not (result or {}).get("error_type") else "error"
        record["finished_at"] = datetime.now(UTC).isoformat()
    except Exception as exc:
        log.exception("paperclip run failed")
        record["status"] = "error"
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["finished_at"] = datetime.now(UTC).isoformat()


def _invoke_and_collect(graph, initial_state, config, record):
    """Synchronous invocation that records each node's output to ``record["steps"]``."""
    result = None
    for event in graph.stream(initial_state, config=config):
        # event is {node_name: partial_state} or {node_name: {..., "__interrupt__": ...}}
        for node_name, partial in event.items():
            if node_name.startswith("__"):
                continue
            step = {
                "node": node_name,
                "ts": datetime.now(UTC).isoformat(),
            }
            if isinstance(partial, dict):
                step["keys"] = sorted([k for k in partial.keys() if not k.startswith("__")])
                err = partial.get("error_type")
                if err:
                    step["error_type"] = err
                    step["error_message"] = partial.get("error_message", "")
            record["steps"].append(step)
            if partial.get("error_type") and partial.get("originating_node") != "spec_analyzer":
                # Spec analyzer errors are recovered by the gap loop; not fatal.
                pass
        # Last event wins as the "result" snapshot
        result = event
    # graph.stream returns a generator — final event IS the final state.
    # Re-invoke to get the final state dict explicitly (LangGraph API).
    try:
        final = graph.get_state(config)
        if final and final.values:
            result = final.values
    except Exception:
        pass
    return result


# ---------------------------------------------------------------------------
# HTML page (vanilla JS — no framework)
# ---------------------------------------------------------------------------
HTML_PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>🧠 Paperclip Dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    :root {
      --bg: #0d1117; --fg: #c9d1d9; --dim: #8b949e; --accent: #58a6ff;
      --ok: #3fb950; --warn: #d29922; --err: #f85149; --card: #161b22;
    }
    body { margin: 0; font-family: -apple-system, system-ui, sans-serif; background: var(--bg); color: var(--fg); }
    header { padding: 16px 24px; border-bottom: 1px solid #30363d; display: flex; justify-content: space-between; align-items: center; }
    h1 { margin: 0; font-size: 20px; font-weight: 600; }
    main { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 16px 24px; }
    .card { background: var(--card); border: 1px solid #30363d; border-radius: 6px; padding: 14px 18px; }
    .card h2 { margin: 0 0 10px; font-size: 14px; text-transform: uppercase; letter-spacing: .05em; color: var(--dim); }
    .full { grid-column: 1 / -1; }
    pre { background: #010409; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 12px; line-height: 1.5; }
    code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
    .ok { color: var(--ok); } .warn { color: var(--warn); } .err { color: var(--err); } .dim { color: var(--dim); }
    button { background: #21262d; color: var(--fg); border: 1px solid #30363d; padding: 6px 12px; border-radius: 4px; cursor: pointer; }
    button:hover { background: #30363d; }
    button.primary { background: #1f6feb; border-color: #1f6feb; }
    button.primary:hover { background: #388bfd; }
    textarea { width: 100%; min-height: 80px; background: #010409; color: var(--fg); border: 1px solid #30363d; border-radius: 4px; padding: 8px; font-family: ui-monospace, monospace; font-size: 13px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 6px 10px; border-bottom: 1px solid #21262d; text-align: left; }
    th { color: var(--dim); font-weight: 500; font-size: 11px; text-transform: uppercase; letter-spacing: .05em; }
    .run-row { cursor: pointer; }
    .run-row:hover { background: #1c2128; }
    .status-pill { padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 500; display: inline-block; }
    .status-running { background: #1f6feb33; color: #79c0ff; }
    .status-ok { background: #3fb95033; color: #56d364; }
    .status-error { background: #f8514933; color: #ff7b72; }
    .graph-svg { width: 100%; height: 320px; background: #010409; border-radius: 4px; }
    .edge-label { font-size: 10px; fill: var(--dim); }
    .node-rect { fill: #161b22; stroke: var(--accent); stroke-width: 1.5; }
    .node-rect.error { stroke: var(--err); }
    .node-text { font-size: 11px; fill: var(--fg); text-anchor: middle; dominant-baseline: middle; }
    .node-end .node-rect { fill: #21262d; stroke: var(--dim); stroke-dasharray: 4 2; }
    @media (max-width: 1000px) { main { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <header>
    <h1>🧠 Paperclip Dashboard</h1>
    <div>
      <span id="status" class="dim">connecting…</span>
      &nbsp;
      <button class="primary" onclick="refreshAll()">↻ Refresh</button>
    </div>
  </header>

  <main>
    <section class="card full">
      <h2>Invoke Paperclip</h2>
      <div style="display:flex; gap:8px; align-items:flex-start;">
        <textarea id="spec" placeholder="Spec text (e.g. Add a hello_world() function to src/test_target.py)">Add a function `hello_paperclip()` to `src/test_paperclip_target.py` that returns the string 'world'. Include a docstring. Add a pytest test for it.</textarea>
        <div style="display:flex; flex-direction:column; gap:6px;">
          <button class="primary" onclick="invoke(true)">▶ DRY RUN (mock adapter)</button>
          <button onclick="invoke(false)">▶ LIVE RUN (real CLI)</button>
        </div>
      </div>
      <div id="invoke-status" class="dim" style="margin-top:8px;"></div>
    </section>

    <section class="card full">
      <h2>Graph topology (9 nodes)</h2>
      <svg id="graph" class="graph-svg" viewBox="0 0 1200 320"></svg>
    </section>

    <section class="card">
      <h2>Adapters (priority order)</h2>
      <table>
        <thead><tr><th>Adapter</th><th>Type</th><th>On PATH</th><th>Timeout</th></tr></thead>
        <tbody id="adapters"></tbody>
      </table>
    </section>

    <section class="card">
      <h2>Throttle gates</h2>
      <table>
        <thead><tr><th>Gate</th><th>Milestone</th><th>Threshold</th><th>Semantics</th></tr></thead>
        <tbody id="gates"></tbody>
      </table>
    </section>

    <section class="card full">
      <h2>Recent runs (most recent first)</h2>
      <table>
        <thead><tr><th>Run ID</th><th>Task</th><th>Started</th><th>Status</th><th>Steps</th><th>Detail</th></tr></thead>
        <tbody id="runs"></tbody>
      </table>
    </section>
  </main>

  <script>
    const $ = (id) => document.getElementById(id);
    const svgNS = "http://www.w3.org/2000/svg";

    async function fetchJson(path, opts) {
      const r = await fetch(path, opts);
      if (!r.ok) throw new Error(`${path}: ${r.status}`);
      return r.json();
    }

    async function refreshHealth() {
      try {
        const h = await fetchJson("/api/health");
        $("status").innerHTML = h.status === "ok"
          ? '<span class="ok">● online</span> · uptime ' + h.uptime_s + 's'
          : '<span class="err">● degraded</span> ' + (h.paperclip_import_error || "");
        $("status").className = h.status === "ok" ? "ok" : "err";
      } catch (e) { $("status").textContent = "offline: " + e.message; $("status").className = "err"; }
    }

    async function refreshGraph() {
      const g = await fetchJson("/api/graph");
      const svg = $("graph");
      svg.innerHTML = "";
      // Layout: 9 nodes in 4 columns
      const cols = [
        ["read_spec"],
        ["spec_analyzer", "merge_user_resolution"],
        ["worktree_create", "hil_pause"],
        ["implement", "worktree_commit", "worktree_merge", "worktree_cleanup", "error"],
      ];
      const COL_W = 280; const NODE_H = 28; const COL_GAP = 50;
      const positions = {};
      cols.forEach((col, ci) => {
        const x = 20 + ci * (COL_W + COL_GAP);
        col.forEach((name, ri) => {
          const y = 20 + ri * (NODE_H + 24);
          positions[name] = { x, y, w: COL_W - 20, h: NODE_H };
        });
      });
      // END node at right
      positions["__end__"] = { x: 1170 - 60, y: 20 + 4 * (NODE_H + 24), w: 50, h: NODE_H };
      // Edges first (so nodes draw on top)
      const edges = g.edges;
      edges.forEach(e => {
        const from = e.from === "__end__" ? positions["__end__"] : positions[e.from];
        const to = e.to === "END" ? positions["__end__"] : positions[e.to];
        if (!from || !to) return;
        const x1 = from.x + from.w;
        const y1 = from.y + from.h / 2;
        const x2 = to.x;
        const y2 = to.y + to.h / 2;
        const cx = (x1 + x2) / 2;
        const path = document.createElementNS(svgNS, "path");
        path.setAttribute("d", `M ${x1} ${y1} C ${cx} ${y1}, ${cx} ${y2}, ${x2} ${y2}`);
        path.setAttribute("fill", "none");
        path.setAttribute("stroke", "#30363d");
        path.setAttribute("stroke-width", "1.2");
        if (e.condition && e.condition !== "always") {
          path.setAttribute("stroke-dasharray", "3 3");
          path.setAttribute("stroke", "#d29922");
        }
        svg.appendChild(path);
        // Condition label
        if (e.condition && e.condition !== "always") {
          const tx = document.createElementNS(svgNS, "text");
          tx.setAttribute("x", (x1 + x2) / 2);
          tx.setAttribute("y", (y1 + y2) / 2 - 4);
          tx.setAttribute("text-anchor", "middle");
          tx.setAttribute("class", "edge-label");
          tx.textContent = e.condition.slice(0, 30);
          svg.appendChild(tx);
        }
      });
      // Nodes
      const allNodes = [...Object.keys(positions), ...new Set(edges.map(e => e.to).filter(t => !positions[t]))];
      const seen = new Set();
      allNodes.forEach(name => {
        if (seen.has(name)) return;
        seen.add(name);
        const p = positions[name];
        if (!p) return;
        const g = document.createElementNS(svgNS, "g");
        g.setAttribute("class", name === "END" || name === "__end__" ? "node-end" : "node");
        const rect = document.createElementNS(svgNS, "rect");
        rect.setAttribute("x", p.x);
        rect.setAttribute("y", p.y);
        rect.setAttribute("width", p.w);
        rect.setAttribute("height", p.h);
        rect.setAttribute("rx", "4");
        rect.setAttribute("class", "node-rect");
        g.appendChild(rect);
        const text = document.createElementNS(svgNS, "text");
        text.setAttribute("x", p.x + p.w / 2);
        text.setAttribute("y", p.y + p.h / 2);
        text.setAttribute("class", "node-text");
        text.textContent = name === "__end__" ? "END" : name;
        g.appendChild(text);
        svg.appendChild(g);
      });
    }

    async function refreshAdapters() {
      const a = await fetchJson("/api/adapters");
      $("adapters").innerHTML = a.items.map(x =>
        `<tr><td><code>${x.name}</code></td><td>${x.type}</td><td class="${x.on_path ? "ok" : "err"}">${x.on_path ? "✓" : "✗"}</td><td>${x.timeout_s}s</td></tr>`
      ).join("");
    }

    async function refreshGates() {
      const g = await fetchJson("/api/gates");
      const rows = [
        [g.cost, "cost"],
        [g.wall_clock, "wall"],
        [g.risk, "risk"],
      ].map(([g, kind]) => {
        let val = "";
        if (kind === "cost") val = "$" + g.threshold_usd.toFixed(2) + "/day";
        if (kind === "wall") val = g.threshold_s + "s (" + Math.round(g.threshold_s / 3600 * 10) / 10 + "h)";
        if (kind === "risk") val = g.keywords_count + " keywords";
        const semClass = g.semantics.includes("OPEN") ? "warn" : "err";
        return `<tr><td>${g.class}</td><td>${g.milestone}</td><td><code>${val}</code></td><td class="${semClass}">${g.semantics}</td></tr>`;
      });
      $("gates").innerHTML = rows.join("");
    }

    async function refreshRuns() {
      const r = await fetchJson("/api/runs");
      if (!r.runs.length) {
        $("runs").innerHTML = '<tr><td colspan="6" class="dim">no runs yet — try the DRY RUN button above</td></tr>';
        return;
      }
      $("runs").innerHTML = r.runs.map(x => {
        const sClass = x.status === "ok" ? "status-ok" : x.status === "error" ? "status-error" : "status-running";
        const detail = x.error || (x.final_state && x.final_state.error_type) || (x.final_state && x.final_state.last_step) || "—";
        return `<tr class="run-row" onclick='alert(JSON.stringify(${JSON.stringify(x)}, null, 2))'>
          <td><code>${x.run_id}</code></td>
          <td>${x.task_id}</td>
          <td class="dim">${(x.started_at || "").slice(11, 19)}</td>
          <td><span class="status-pill ${sClass}">${x.status}</span></td>
          <td>${(x.steps || []).length}</td>
          <td><code style="font-size:11px;">${(detail || "").slice(0, 80)}</code></td>
        </tr>`;
      }).join("");
    }

    async function invoke(dryRun) {
      const spec = $("spec").value;
      if (!spec.trim()) { alert("spec is empty"); return; }
      $("invoke-status").textContent = "invoking...";
      try {
        const r = await fetchJson("/api/invoke", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ spec_text: spec, dry_run: dryRun }),
        });
        $("invoke-status").innerHTML = `<span class="ok">started</span> run_id=<code>${r.run_id}</code> task_id=<code>${r.task_id}</code>`;
        setTimeout(refreshAll, 500);
      } catch (e) {
        $("invoke-status").innerHTML = `<span class="err">${e.message}</span>`;
      }
    }

    async function refreshAll() {
      await Promise.all([refreshHealth(), refreshGraph(), refreshAdapters(), refreshGates(), refreshRuns()]);
    }

    refreshAll();
    setInterval(refreshAll, 3000);
  </script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse(content=HTML_PAGE)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
SERVER_START_TS = time.time()


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Run the uvicorn server. Called by ``paperclip dashboard`` subcommand."""
    import uvicorn

    log.info("starting paperclip dashboard on http://%s:%d", host, port)
    log.info(
        "paperclip imports: %s",
        "OK" if PAPERCLIP_IMPORT_ERROR is None else f"FAILED — {PAPERCLIP_IMPORT_ERROR}",
    )
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    port = int(os.environ.get("PAPERCLIP_DASHBOARD_PORT", "8765"))
    host = os.environ.get("PAPERCLIP_DASHBOARD_HOST", "127.0.0.1")
    run_server(host=host, port=port)
