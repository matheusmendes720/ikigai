#!/usr/bin/env python3
"""chat.py — E2E test CLI for IKIGAI deep agents + taskdog workflows.

Targets the running `langgraph dev` server. Default URL is localhost:2024;
override with --url or LANGGRAPH_API_URL. Works against the Cloudflare tunnel
too (just point at the trycloudflare.com URL).

Subcommands
-----------
graphs                  List registered graphs (id + assistant_id)
schema <graph>          Show input/output/state schemas of a graph
run <graph> --input J   One-shot run with JSON input; streams SSE events
chat <graph>            Interactive REPL — sends {messages: [human]}, reads state
mcp list                List MCP tools exposed via /mcp JSON-RPC
mcp call <tool> --args  Call an MCP tool via JSON-RPC tools/call
taskdog <op> [...]      Convenience: invoke ikigai_taskdog_mcp with a taskdog op
e2e                     Full smoke test: graphs + schemas + MCP + run each graph

Exit codes: 0 success, 1 partial failure, 2 fatal (server unreachable).

Examples
--------
    python scripts/chat.py graphs
    python scripts/chat.py schema ikigai_maintainer_v2 --full
    python scripts/chat.py run ikigai_maintainer_v2 -i '{"user_input":"olá"}'
    python scripts/chat.py chat ikigai_taskdog_mcp
    python scripts/chat.py mcp list
    python scripts/chat.py mcp call ikigai_maintainer_v2 --args '{"messages":[]}'
    python scripts/chat.py taskdog list_tasks
    python scripts/chat.py taskdog create_task --title "Test from chat.py"
    python scripts/chat.py e2e
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Iterator

import httpx

DEFAULT_API = "http://localhost:2024"
DEFAULT_TIMEOUT = 60.0
TASKDOG_GRAPH = "ikigai_taskdog_mcp"


# ── tiny ANSI helper (auto-disabled on Windows cmd.exe or NO_COLOR) ────────────
class _C:
    R = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
    RED = "\033[31m"; GRN = "\033[32m"; YEL = "\033[33m"
    BLU = "\033[34m"; MAG = "\033[35m"; CYN = "\033[36m"


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty() or os.environ.get("TERM", "") not in ("", "dumb")


_COLOR = _supports_color()


def c(s: str, color: str) -> str:
    return f"{color}{s}{_C.R}" if _COLOR else str(s)


def pp(d: Any, indent: int = 2, maxlen: int = 4000) -> str:
    s = json.dumps(d, indent=indent, default=str, ensure_ascii=False)
    return s if len(s) <= maxlen else s[:maxlen] + f"\n{c('…[truncated]', _C.DIM)}"


# ── HTTP client wrapper ────────────────────────────────────────────────────────
class API:
    def __init__(self, base_url: str, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "API":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def get(self, path: str, **kw: Any) -> httpx.Response:
        return self.client.get(path, **kw)

    def post(self, path: str, json: Any = None, **kw: Any) -> httpx.Response:
        return self.client.post(path, json=json, **kw)

    def stream_post(self, path: str, json: Any = None, **kw: Any):
        """Return a context manager for a streaming POST (use for SSE endpoints).

        Use as `with api.stream_post(path, json=body) as r: ...`
        """
        return self.client.stream("POST", path, json=json, **kw)

    def post_jsonrpc(self, method: str, params: Any = None) -> dict:
        body: dict[str, Any] = {"jsonrpc": "2.0", "id": int(time.time() * 1000), "method": method}
        if params is not None:
            body["params"] = params
        # MCP requires Accept header to include application/json or text/event-stream
        headers = {"Accept": "application/json, text/event-stream"}
        r = self.post("/mcp", json=body, headers=headers)
        r.raise_for_status()
        return r.json()


def resolve_assistant(api: API, graph_id: str) -> str:
    r = api.post("/assistants/search", json={})
    r.raise_for_status()
    for a in r.json():
        if a["graph_id"] == graph_id:
            return a["assistant_id"]
    available = [a["graph_id"] for a in r.json()]
    raise SystemExit(f"graph {graph_id!r} not found; available: {available}")


def health_check(api: API) -> bool:
    try:
        r = api.get("/", timeout=5.0)
        return r.is_success and r.json().get("ok") is True
    except Exception:
        return False


# ── subcommand: graphs ─────────────────────────────────────────────────────────
def cmd_graphs(args: argparse.Namespace) -> None:
    with API(args.url) as api:
        if not health_check(api):
            raise SystemExit(f"server unreachable at {args.url}")
        r = api.post("/assistants/search", json={})
        r.raise_for_status()
        graphs = r.json()
        print(c(f"{len(graphs)} graphs @ {args.url}", _C.BOLD))
        for g in graphs:
            print(f"  {c(g['graph_id'], _C.CYN):40} aid={g['assistant_id']}")


# ── subcommand: schema ─────────────────────────────────────────────────────────
def cmd_schema(args: argparse.Namespace) -> None:
    with API(args.url) as api:
        aid = resolve_assistant(api, args.graph)
        r = api.get(f"/assistants/{aid}/schemas")
        r.raise_for_status()
        d = r.json()
        for label in ("input_schema", "output_schema", "state_schema", "config_schema"):
            sub = d.get(label) or {}
            req = sub.get("required", []) if isinstance(sub, dict) else []
            title = sub.get("title", "") if isinstance(sub, dict) else ""
            print(c(f"{label:14}", _C.BOLD) + f" required={req}  title={title!r}")
        if args.full:
            print()
            print(pp(d))


# ── SSE run helpers ────────────────────────────────────────────────────────────
def _iter_sse(response: httpx.Response) -> Iterator[dict]:
    """Yield parsed JSON events from an SSE stream, skipping keepalives.

    The langgraph SSE format is:
        event: <type>
        data: <json>

    The `event:` line carries the type (values | messages | metadata | end);
    the `data:` line carries the JSON payload (which IS the state for a
    `values` event — no extra wrapper). We track the event type alongside the
    payload so consumers can dispatch on it.
    """
    current_event = "message"
    for line in response.iter_lines():
        if not line:
            current_event = "message"
            continue
        if line.startswith("event:"):
            current_event = line[6:].strip()
            continue
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            yield {"_event": current_event, **json.loads(payload)}
        except json.JSONDecodeError:
            continue


def _print_event(evt: dict, *, verbose: bool = False) -> None:
    etype = evt.get("_event", "message")
    body = {k: v for k, v in evt.items() if k != "_event"}
    if etype == "values" and isinstance(body, dict):
        last_step = body.get("last_step", "")
        iter_n = body.get("iteration", "")
        terminated = body.get("terminated", False)
        msgs_n = len(body.get("messages", []))
        summary = f"iter={iter_n} last={last_step} msgs={msgs_n} terminated={terminated}"
        if body.get("error_type"):
            summary += f" err={body['error_type']}:{body.get('error_message', '')}"
        print(c("• state ", _C.DIM) + summary)
        if verbose:
            print(c(pp({k: body[k] for k in list(body)[:8]}), _C.DIM))
    elif etype == "messages":
        print(c("• message ", _C.DIM) + str(body.get("messages") or body)[:200])
    elif etype == "metadata":
        rid = str((body.get("run_id") if isinstance(body, dict) else ""))[:24]
        print(c("• meta run_id=", _C.DIM) + rid)
    elif etype == "error" or body.get("error"):
        print(c("✗ error " + pp(body), _C.RED))
    elif etype == "end":
        print(c("✓ end", _C.GRN))


# ── subcommand: run ────────────────────────────────────────────────────────────
def cmd_run(args: argparse.Namespace) -> None:
    with API(args.url) as api:
        if not health_check(api):
            raise SystemExit(f"server unreachable at {args.url}")
        aid = resolve_assistant(api, args.graph)
        # thread
        tr = api.post("/threads", json={})
        tr.raise_for_status()
        tid = tr.json()["thread_id"]
        print(c(f"thread {tid}", _C.DIM))
        # build input
        try:
            input_data = json.loads(args.input) if args.input else {}
        except json.JSONDecodeError as e:
            raise SystemExit(f"--input not valid JSON: {e}")
        body = {
            "assistant_id": aid,
            "input": input_data,
            "stream_mode": ["values", "messages"],
        }
        print(c(f"▶ run on {args.graph}", _C.BOLD))
        with api.stream_post(f"/threads/{tid}/runs/stream", json=body) as r:
            if not r.is_success:
                raise SystemExit(f"run {r.status_code}: {r.text[:300]}")
            for evt in _iter_sse(r):
                _print_event(evt, verbose=args.verbose)


# ── subcommand: chat (interactive REPL) ────────────────────────────────────────
def cmd_chat(args: argparse.Namespace) -> None:
    with API(args.url) as api:
        if not health_check(api):
            raise SystemExit(f"server unreachable at {args.url}")
        aid = resolve_assistant(api, args.graph)
        print(c(f"Chat with {args.graph}  (Ctrl+C / Ctrl+D to exit)", _C.BOLD))
        print(c(f"  endpoint: {args.url}", _C.DIM))
        tid: str | None = None
        while True:
            try:
                text = input(c("❯ ", _C.GRN))
            except (EOFError, KeyboardInterrupt):
                print("\nbye")
                return
            text = text.strip()
            if not text:
                continue
            if text in ("/exit", "/quit"):
                return
            if not tid:
                tr = api.post("/threads", json={})
                tr.raise_for_status()
                tid = tr.json()["thread_id"]
            body = {
                "assistant_id": aid,
                "input": {"messages": [{"role": "human", "content": text}]},
                "stream_mode": ["values", "messages"],
            }
            last_state: dict | None = None
            with api.stream_post(f"/threads/{tid}/runs/stream", json=body) as r:
                if not r.is_success:
                    print(c(f"✗ run failed {r.status_code}: {r.text[:200]}", _C.RED))
                    tid = None  # reset thread
                    break
                for evt in _iter_sse(r):
                    if evt.get("_event") == "values":
                        body = {k: v for k, v in evt.items() if k != "_event"}
                        if isinstance(body, dict):
                            last_state = body
            # extract reply: prefer assistant msg; fallback last message; fallback state
            assistant_text = ""
            if last_state:
                msgs = last_state.get("messages") or []
                for m in reversed(msgs):
                    if isinstance(m, dict) and m.get("role") == "assistant":
                        content = m.get("content", "")
                        if isinstance(content, list):
                            content = " ".join(
                                p.get("text", "") for p in content if isinstance(p, dict)
                            )
                        assistant_text = str(content)
                        break
            if assistant_text:
                print(c("◀ ", _C.MAG) + assistant_text)
            elif last_state:
                print(c("◀ (state only, no assistant msg)", _C.YEL))
                print(c(pp({k: last_state[k] for k in list(last_state)[:6]}), _C.DIM))
            else:
                print(c("◀ (no response)", _C.YEL))


# ── subcommand: mcp (JSON-RPC over /mcp) ───────────────────────────────────────
def cmd_mcp(args: argparse.Namespace) -> None:
    with API(args.url, timeout=120.0) as api:
        if args.action == "list":
            d = api.post_jsonrpc("tools/list")
            tools = (d.get("result") or {}).get("tools") or []
            print(c(f"{len(tools)} MCP tools", _C.BOLD))
            for t in tools:
                desc = (t.get("description") or "").split("\n")[0][:90]
                print(f"  {c(t['name'], _C.CYN):35} {desc}")
        elif args.action == "call":
            if not args.name:
                raise SystemExit("--name required for `mcp call`")
            try:
                arguments = json.loads(args.args) if args.args else {}
            except json.JSONDecodeError as e:
                raise SystemExit(f"--args not valid JSON: {e}")
            d = api.post_jsonrpc("tools/call", {"name": args.name, "arguments": arguments})
            if "error" in d:
                print(c("✗ " + pp(d["error"]), _C.RED))
            else:
                print(pp(d.get("result", d)))


# ── subcommand: taskdog (shortcut to ikigai_taskdog_mcp graph) ─────────────────
def cmd_taskdog(args: argparse.Namespace) -> None:
    """Convenience wrapper: routes taskdog ops through ikigai_taskdog_mcp graph.

    Sub-ops:
      list_tasks [--status S] [--limit N]      → list tasks
      create_task --title T [--priority P]      → create a task
      get_task --ueid U                         → fetch a single task
      run <op> ...                              → raw op passthrough (advanced)
    """
    with API(args.url) as api:
        if not health_check(api):
            raise SystemExit(f"server unreachable at {args.url}")
        aid = resolve_assistant(api, TASKDOG_GRAPH)
        op = args.op
        # build chat-message input the ReAct agent can route to taskdog_* tools
        if op == "list_tasks":
            nl = f"list tasks, max {args.limit}"
            if args.status:
                nl += f", status={args.status}"
            inp = {"messages": [{"role": "human", "content": nl}]}
        elif op == "create_task":
            if not args.title:
                raise SystemExit("--title required for create_task")
            inp = {"messages": [{"role": "human", "content": (
                f"create a new task titled {args.title!r} with priority {args.priority}"
            )}]}
        elif op == "get_task":
            if not args.ueid:
                raise SystemExit("--ueid required for get_task")
            inp = {"messages": [{"role": "human", "content": (
                f"get task with ueid {args.ueid}"
            )}]}
        elif op == "run":
            inp = json.loads(args.input) if args.input else {}
        else:
            raise SystemExit(f"unknown taskdog op: {op!r}")
        # call via run
        tr = api.post("/threads", json={})
        tr.raise_for_status()
        tid = tr.json()["thread_id"]
        body = {"assistant_id": aid, "input": inp, "stream_mode": ["values"]}
        last_state = None
        last_msgs = None
        # Use streaming context manager so SSE events arrive incrementally
        with api.stream_post(f"/threads/{tid}/runs/stream", json=body) as r:
            if not r.is_success:
                raise SystemExit(f"run failed {r.status_code}: {r.text[:300]}")
            for evt in _iter_sse(r):
                etype = evt.get("_event")
                body = {k: v for k, v in evt.items() if k != "_event"}
                if etype == "values" and isinstance(body, dict):
                    last_state = body
                    if "messages" in last_state:
                        last_msgs = last_state["messages"]
                elif etype == "messages" and isinstance(body, list):
                    last_msgs = body
                elif etype == "messages" and isinstance(body, dict) and isinstance(body.get("messages"), list):
                    last_msgs = body["messages"]
        if last_msgs:
            # pretty-print last assistant message if any
            for m in reversed(last_msgs):
                if isinstance(m, dict) and m.get("role") == "assistant":
                    content = m.get("content", "")
                    if isinstance(content, list):
                        content = " ".join(
                            p.get("text", "") for p in content if isinstance(p, dict)
                        )
                    print(c("◀ assistant: ", _C.MAG) + str(content))
                    break
        if last_state:
            print(pp(last_state))
        elif not last_msgs:
            print(c("(empty state)", _C.YEL))


# ── subcommand: e2e (full smoke suite) ─────────────────────────────────────────
def cmd_e2e(args: argparse.Namespace) -> None:
    failures: list[str] = []
    with API(args.url, timeout=180.0) as api:
        if not health_check(api):
            raise SystemExit(f"server unreachable at {args.url}")

        print(c("[1] list graphs", _C.BOLD))
        r = api.post("/assistants/search", json={})
        r.raise_for_status()
        graphs = r.json()
        print(f"  {c('ok', _C.GRN)} {len(graphs)} graphs")

        print(c("[2] schemas (per graph)", _C.BOLD))
        for g in graphs:
            r = api.get(f"/assistants/{g['assistant_id']}/schemas")
            if not r.is_success:
                failures.append(f"schema/{g['graph_id']}: {r.status_code}")
                print(f"  {c('fail', _C.RED)} {g['graph_id']}")
                continue
            d = r.json()
            req = d.get("input_schema", {}).get("required", [])
            print(f"  {c('ok', _C.GRN)} {g['graph_id']:30} required={req}")

        print(c("[3] MCP tools", _C.BOLD))
        d = api.post_jsonrpc("tools/list")
        tools = (d.get("result") or {}).get("tools") or []
        if not tools:
            failures.append("mcp/tools/list returned no tools")
        else:
            print(f"  {c('ok', _C.GRN)} {len(tools)} tools")
            for t in tools[:8]:
                print(f"    - {t['name']}")
            if len(tools) > 8:
                print(f"    …+{len(tools) - 8} more")

        print(c("[4] smoke run each graph (empty input)", _C.BOLD))
        for g in graphs:
            tr = api.post("/threads", json={})
            tid = tr.json()["thread_id"]
            body = {
                "assistant_id": g["assistant_id"],
                "input": {},
                "stream_mode": ["values"],
            }
            try:
                with api.stream_post(f"/threads/{tid}/runs/stream", json=body, timeout=120.0) as r:
                    if not r.is_success:
                        failures.append(f"run/{g['graph_id']}: {r.status_code}")
                        print(f"  {c('fail', _C.RED)} {g['graph_id']}: {r.status_code}")
                        continue
                    # read first event or hit error
                    first = None
                    for evt in _iter_sse(r):
                        first = evt
                        break
                status = "ok"
                if first and first.get("_event") == "error":
                    status = "err:" + str(first.get("data", {}).get("message", ""))[:60]
                    failures.append(f"run/{g['graph_id']} -> {status}")
                etype = (first or {}).get("_event", "?")
                print(f"  {c(status if status == 'ok' else 'fail', _C.GRN if status == 'ok' else _C.RED)} "
                      f"{g['graph_id']:30} first={etype}")
            except httpx.HTTPError as e:
                failures.append(f"run/{g['graph_id']}: {e}")
                print(f"  {c('fail', _C.RED)} {g['graph_id']}: {e}")

    print()
    if failures:
        print(c(f"FAILURES: {len(failures)}", _C.RED))
        for f in failures:
            print(f"  • {f}")
        sys.exit(1)
    print(c("ALL PASS ✓", _C.GRN))


# ── argparse wiring ────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="chat",
        description="E2E test CLI for IKIGAI agents + taskdog workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--url", default=os.environ.get("LANGGRAPH_API_URL", DEFAULT_API),
        help=f"LangGraph API base URL (default: {DEFAULT_API}, env: LANGGRAPH_API_URL)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("graphs", help="List registered graphs")

    p_schema = sub.add_parser("schema", help="Show graph schemas")
    p_schema.add_argument("graph")
    p_schema.add_argument("--full", action="store_true", help="dump full JSON")

    p_run = sub.add_parser("run", help="One-shot run with --input JSON")
    p_run.add_argument("graph")
    p_run.add_argument("--input", "-i", default="{}",
                       help="JSON input dict (default: empty {})")
    p_run.add_argument("--verbose", "-v", action="store_true")

    p_chat = sub.add_parser("chat", help="Interactive REPL")
    p_chat.add_argument("graph")

    p_mcp = sub.add_parser("mcp", help="MCP tools via JSON-RPC /mcp")
    p_mcp.add_argument("action", choices=["list", "call"])
    p_mcp.add_argument("--name", help="tool name (for call)")
    p_mcp.add_argument("--args", help="JSON args (for call)")

    p_td = sub.add_parser("taskdog", help="taskdog ops via ikigai_taskdog_mcp graph")
    p_td.add_argument("op", choices=["list_tasks", "create_task", "get_task", "run"])
    p_td.add_argument("--title", help="(create_task)")
    p_td.add_argument("--priority", default="medium", help="(create_task) low/medium/high")
    p_td.add_argument("--status", help="(list_tasks) filter by status")
    p_td.add_argument("--limit", type=int, default=20, help="(list_tasks) max results")
    p_td.add_argument("--ueid", help="(get_task) task UEID")
    p_td.add_argument("--input", "-i", help="(run) raw JSON input")

    sub.add_parser("e2e", help="Full E2E smoke suite (graphs+schemas+MCP+run)")

    return p


def main() -> None:
    args = build_parser().parse_args()
    handlers = {
        "graphs": cmd_graphs, "schema": cmd_schema, "run": cmd_run,
        "chat": cmd_chat, "mcp": cmd_mcp, "taskdog": cmd_taskdog, "e2e": cmd_e2e,
    }
    try:
        handlers[args.cmd](args)
    except httpx.ConnectError as e:
        raise SystemExit(f"cannot connect to {args.url}: {e}")
    except httpx.HTTPStatusError as e:
        raise SystemExit(f"HTTP {e.response.status_code} on {e.request.url}: {e.response.text[:200]}")


if __name__ == "__main__":
    main()