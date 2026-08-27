#!/usr/bin/env python3
"""End-to-end verification — both LangSmith and Langfuse received traces.

Run ``repro_byd_db_error.py`` and ``repro_ops_dir_error.py`` first (within the
last 5 minutes), then run this script. It queries each backend's HTTP API for
traces newer than the cutoff and asserts at least one span arrived at each.

Required env vars (loaded from ``.env`` if present via the standard
``python-dotenv``-style lookup the host app would use — here we read directly):

- ``LANGSMITH_API_KEY``
- ``LANGSMITH_PROJECT`` (defaults to ``ikigai``)
- ``LANGFUSE_PUBLIC_KEY``
- ``LANGFUSE_SECRET_KEY``
- ``LANGFUSE_HOST`` (defaults to ``https://cloud.langfuse.com``)

Usage::

    python scripts/verify_traces.py
"""
from __future__ import annotations

import base64
import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]

# LangSmith endpoints (public, stable per their docs).
LS_RUNS_API = "https://api.smith.langchain.com/api/v1/runs"

# Langfuse traces list endpoint, with the {host} placeholder filled at call time.
LF_TRACES_API_TEMPLATE = "{host}/api/public/traces"


def _load_dotenv() -> None:
    """Best-effort load of ``.env`` from the ikigai project root.

    We avoid hard-depending on python-dotenv so the script works whether or
    not the user has installed it. Format expected: ``KEY=VALUE`` per line,
    optional single quotes around the value, ``#`` for comments.
    """
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        # Don't clobber an env var the user has set externally.
        os.environ.setdefault(k, v)


def fetch_langsmith_runs(minutes: int = 5) -> list:
    """List LangSmith runs in the configured project from the last ``minutes``."""
    headers = {"x-api-key": os.environ["LANGSMITH_API_KEY"]}
    project = os.environ.get("LANGSMITH_PROJECT", "ikigai")
    cutoff_ms = int((time.time() - minutes * 60) * 1000)
    resp = requests.get(
        LS_RUNS_API,
        params={"project_name": project, "start_time": cutoff_ms, "limit": 50},
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("runs", [])


def fetch_langfuse_traces(minutes: int = 5) -> list:
    """List Langfuse traces from the last ``minutes``."""
    host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com").rstrip("/")
    auth = base64.b64encode(
        f"{os.environ['LANGFUSE_PUBLIC_KEY']}:{os.environ['LANGFUSE_SECRET_KEY']}".encode()
    ).decode()
    resp = requests.get(
        LF_TRACES_API_TEMPLATE.format(host=host),
        params={"limit": 50, "fromTimestamp": int((time.time() - minutes * 60) * 1000)},
        headers={"Authorization": f"Basic {auth}"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def main() -> int:
    _load_dotenv()

    # Sanity-check required env vars up front.
    missing = [
        k
        for k in ("LANGSMITH_API_KEY", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")
        if not os.environ.get(k)
    ]
    if missing:
        print(
            f"Missing env vars: {missing}. Populate .env (see .env.example) and retry.",
            file=sys.stderr,
        )
        return 2

    print("─── LangSmith ───")
    ls_runs = fetch_langsmith_runs()
    print(f"  {len(ls_runs)} runs in last 5 min")
    for r in ls_runs[:5]:
        print(f"    {r.get('name')} | {r.get('run_type')} | status={r.get('status')}")

    print("─── Langfuse ───")
    lf_traces = fetch_langfuse_traces()
    print(f"  {len(lf_traces)} traces in last 5 min")
    for t in lf_traces[:5]:
        print(f"    {t.get('name')} | {t.get('timestamp')}")

    # Hard asserts — both backends must have received something.
    assert ls_runs, "No LangSmith runs — check LANGSMITH_API_KEY + endpoint"
    assert lf_traces, "No Langfuse traces — check LANGFUSE_*_KEY + endpoint"
    print("\n✓ Both backends received traces")
    return 0


if __name__ == "__main__":
    sys.exit(main())