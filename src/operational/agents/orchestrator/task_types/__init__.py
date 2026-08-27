"""Task type implementations — one file per task type.

Per /workflow-orchestrator skill: shell, python, http, docker, conditional,
parallel, loop, data_processor, notify task runners.
"""

from __future__ import annotations

import json
import re
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import requests
from pydantic import BaseModel, Field

_ROOT = Path(__file__).resolve().parents[3].parents[1]


# ── Base ────────────────────────────────────────────────────────────────────

class TaskResult(BaseModel):
    """Standard return type from all task executors."""

    class Config:
        extra = "allow"

    success: bool
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    duration_ms: int = 0


class BaseTaskRunner(ABC):
    """Abstract base for all task type runners."""

    def __init__(self, task_def: dict[str, Any], context: dict[str, Any]):
        self.task_def = task_def
        self.context = context  # shared execution context
        self.env = self._build_env()

    def _build_env(self) -> dict[str, str]:
        env = dict(__import__("os").environ)
        for k, v in self.task_def.get("environment", {}).items():
            env[k] = self._interpolate(str(v))
        return env

    def _interpolate(self, template: str) -> str:
        """Interpolate ${task.xxx} and ${env.YYYY} in strings."""
        def replacer(m: re.Match) -> str:
            path = m.group(1)
            if path.startswith("env."):
                return __import__("os").getenv(path[4:], "")
            if path.startswith("tasks."):
                parts = path.split(".")
                task_id = parts[1]
                field = parts[2] if len(parts) > 2 else "result"
                val = self.context.get("task_results", {}).get(task_id, {})
                return str(val.get(field, ""))
            return m.group(0)

        return re.sub(r"\$\{([^}]+)\}", replacer, template)

    def _interpolate_obj(self, obj: Any) -> Any:
        if isinstance(obj, str):
            return self._interpolate(obj)
        if isinstance(obj, dict):
            return {k: self._interpolate_obj(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._interpolate_obj(v) for v in obj]
        return obj

    def _run(self) -> TaskResult:
        import time
        t0 = time.perf_counter()
        try:
            result = self.execute()
            result.duration_ms = int((time.perf_counter() - t0) * 1000)
            return result
        except Exception as e:
            return TaskResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                duration_ms=int((time.perf_counter() - t0) * 1000),
            )

    @abstractmethod
    def execute(self) -> TaskResult:
        raise NotImplementedError

    def evaluate_condition(self, condition: str) -> bool:
        """Evaluate a JS-like condition against the context."""
        try:
            # Simple expression evaluator
            cond = self._interpolate(condition)
            # Replace Python-style ==/!=/and/or for safety
            cond_safe = cond.replace("&&", " and ").replace("||", " or ")
            return bool(eval(cond_safe, {"__builtins__": {}, "tasks": self.context.get("task_results", {})}))
        except Exception:
            return False


# ── Shell Task ───────────────────────────────────────────────────────────────

class ShellTaskRunner(BaseTaskRunner):
    def execute(self) -> TaskResult:
        cmd = self._interpolate(self.task_def.get("command", ""))
        cwd = self.task_def.get("cwd")
        if cwd:
            cwd = self._interpolate(cwd)
            cwd = Path(cwd) if cwd else None

        timeout = self.task_def.get("timeout_s", 300)
        live = self.task_def.get("live_output", False)

        proc = subprocess.Popen(
            cmd if self.task_def.get("shell", True) else cmd.split(),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(cwd) if cwd else str(_ROOT),
            env=self.env,
        )
        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []

        def pump_stream(stream, chunks):
            for line in iter(stream.readline, b""):
                chunks.append(line.decode("utf-8", errors="replace"))

        out_thread = threading.Thread(target=pump_stream, args=(proc.stdout, stdout_chunks), daemon=True)
        err_thread = threading.Thread(target=pump_stream, args=(proc.stderr, stderr_chunks), daemon=True)
        out_thread.start()
        err_thread.start()

        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            return TaskResult(success=False, error=f"Timeout after {timeout}s", exit_code=-1)

        out_thread.join(timeout=1)
        err_thread.join(timeout=1)
        stdout = "".join(stdout_chunks)
        stderr = "".join(stderr_chunks)

        return TaskResult(
            success=proc.returncode == 0,
            exit_code=proc.returncode,
            stdout=stdout,
            stderr=stderr,
        )


# ── Python Task ──────────────────────────────────────────────────────────────

class PythonTaskRunner(BaseTaskRunner):
    def execute(self) -> TaskResult:
        script = self._interpolate(self.task_def.get("script_path", ""))
        args = [self._interpolate(a) for a in self.task_def.get("args", [])]
        cwd = self.task_def.get("cwd")
        if cwd:
            cwd = Path(self._interpolate(cwd))
        timeout = self.task_def.get("timeout_s", 300)

        cmd = ["python", str(_ROOT / script), *args]
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else str(_ROOT),
            env=self.env,
            timeout=timeout,
        )

        result: dict[str, Any] = {}
        try:
            result = json.loads(r.stdout) if r.stdout.strip().startswith(("{", "[")) else {}
        except Exception:
            pass

        return TaskResult(
            success=r.returncode == 0,
            exit_code=r.returncode,
            stdout=r.stdout or "",
            stderr=r.stderr or "",
            result=result,
        )


# ── HTTP Task ───────────────────────────────────────────────────────────────

class HttpTaskRunner(BaseTaskRunner):
    def execute(self) -> TaskResult:
        url = self._interpolate(self.task_def.get("url", ""))
        method = self.task_def.get("method", "GET").upper()
        headers = {k: self._interpolate(v) for k, v in self.task_def.get("headers", {}).items()}
        data = self._interpolate_obj(self.task_def.get("data"))
        timeout = self.task_def.get("timeout_s", 30)
        auth_cfg = self.task_def.get("auth")

        auth = None
        if auth_cfg:
            if auth_cfg.get("bearer_token"):
                headers["Authorization"] = f"Bearer {self._interpolate(auth_cfg['bearer_token'])}"
            elif auth_cfg.get("username"):
                auth = (self._interpolate(auth_cfg["username"]), self._interpolate(auth_cfg["password"] or ""))

        t0 = time.perf_counter()
        try:
            resp = requests.request(method, url, headers=headers, json=data, auth=auth, timeout=timeout)
            return TaskResult(
                success=resp.status_code < 400,
                exit_code=0 if resp.status_code < 400 else resp.status_code,
                stdout=resp.text[:5000],
                stderr="",
                result={"status_code": resp.status_code, "headers": dict(resp.headers)},
                duration_ms=int((time.perf_counter() - t0) * 1000),
            )
        except requests.Timeout:
            return TaskResult(success=False, error=f"HTTP timeout after {timeout}s", duration_ms=int((time.perf_counter() - t0) * 1000))
        except Exception as e:
            return TaskResult(success=False, error=str(e), duration_ms=int((time.perf_counter() - t0) * 1000))


# ── Docker Task ─────────────────────────────────────────────────────────────

class DockerTaskRunner(BaseTaskRunner):
    def execute(self) -> TaskResult:
        import shutil
        if not shutil.which("docker"):
            return TaskResult(success=False, error="docker not found in PATH")

        subcmd = self.task_def.get("command", "run")
        image = self._interpolate(self.task_def.get("image", ""))
        container = self._interpolate(self.task_def.get("container_name", ""))
        detach = self.task_def.get("detach", False)
        extra_env = {k: self._interpolate(v) for k, v in self.task_def.get("environment", {}).items()}

        cmd_parts = ["docker", subcmd]
        if image:
            cmd_parts.append(image)
        if container and subcmd == "run":
            cmd_parts.extend(["--name", container])
        if detach and subcmd == "run":
            cmd_parts.append("-d")

        cmd_str = " ".join(cmd_parts)
        timeout = self.task_def.get("timeout_s", 300)

        env = dict(self.env)
        env.update(extra_env)

        r = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, env=env, timeout=timeout)
        return TaskResult(
            success=r.returncode == 0,
            exit_code=r.returncode,
            stdout=r.stdout or "",
            stderr=r.stderr or "",
        )


# ── Conditional Task ────────────────────────────────────────────────────────

class ConditionalTaskRunner(BaseTaskRunner):
    def execute(self) -> TaskResult:
        condition = self._interpolate(self.task_def.get("condition", "false"))
        branch: dict[str, Any] = {}

        try:
            cond_safe = condition.replace("&&", " and ").replace("||", " or ")
            matches = eval(cond_safe, {"__builtins__": {}, "tasks": self.context.get("task_results", {})})
        except Exception:
            matches = False

        if matches:
            branch = {"type": "shell", "command": self.task_def.get("then_command", "")}
            if self.task_def.get("then_script_path"):
                branch = {"type": "python", "script_path": self.task_def["then_script_path"]}
        else:
            else_cmd = self.task_def.get("else_command")
            if else_cmd:
                branch = {"type": "shell", "command": else_cmd}
            elif self.task_def.get("else_script_path"):
                branch = {"type": "python", "script_path": self.task_def["else_script_path"]}

        if not branch:
            return TaskResult(success=True, result={"condition": condition, "branch": "none", "skipped": True})

        runner = get_runner(branch, self.context)
        return runner.execute()


# ── Parallel Task ───────────────────────────────────────────────────────────

class ParallelTaskRunner(BaseTaskRunner):
    def execute(self) -> TaskResult:
        subtasks = self.task_def.get("tasks", [])
        wait_for = self.task_def.get("wait_for", "all")
        timeout_s = self.task_def.get("timeout_s", 1800)
        max_parallel = self.task_def.get("max_parallel", len(subtasks))

        t0 = time.perf_counter()
        results: list[TaskResult] = []
        sem = threading.Semaphore(max_parallel)
        lock = threading.Lock()

        def run_one(subtask_def: dict[str, Any]) -> TaskResult:
            sem.acquire()
            try:
                runner = get_runner(subtask_def, self.context)
                result = runner.execute()
                return result
            finally:
                sem.release()

        threads: list[threading.Thread] = []
        for st in subtasks:
            t = threading.Thread(target=lambda st=st: results.append(run_one(st)), daemon=True)
            threads.append(t)
            t.start()

        # Wait with timeout
        deadlined = time.time() + timeout_s
        for t in threads:
            remaining = deadlined - time.time()
            t.join(timeout=max(0.1, remaining))

        # Determine outcome
        all_done = all(not t.is_alive() for t in threads)
        any_failed = any(not r.success for r in results)
        first_success = next((r for r in results if r.success), None)

        if not all_done:
            return TaskResult(
                success=False,
                error=f"Parallel task timeout after {timeout_s}s",
                duration_ms=int((time.perf_counter() - t0) * 1000),
            )

        if wait_for == "first":
            success = first_success is not None
            exit_code = first_success.exit_code if first_success else -1
        elif wait_for == "any":
            success = not any_failed
            exit_code = 0 if not any_failed else -1
        else:  # all
            success = not any_failed
            exit_code = max(r.exit_code for r in results) if results else 0

        return TaskResult(
            success=success,
            exit_code=exit_code,
            result={"subtask_count": len(subtasks), "results": [r.model_dump() for r in results]},
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )


# ── Loop Task ───────────────────────────────────────────────────────────────

class LoopTaskRunner(BaseTaskRunner):
    def execute(self) -> TaskResult:
        items = self.task_def.get("items", [])
        if self.task_def.get("items_from_file"):
            import csv
            path = Path(self._interpolate(self.task_def["items_from_file"]))
            if path.suffix == ".csv":
                with open(path, newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    items = list(reader)
            else:
                items = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(items, list):
                    items = [items]

        item_var = self.task_def.get("item_variable", "item")
        index_var = self.task_def.get("index_variable", "index")
        task_template = self.task_def.get("task", {})
        stop_on_failure = self.task_def.get("stop_on_failure", True)
        max_parallel = self.task_def.get("max_parallel", 1)

        results: list[TaskResult] = []
        sem = threading.Semaphore(max_parallel)
        t0 = time.perf_counter()

        def run_item(idx: int, item_val: Any) -> TaskResult:
            item_context = dict(self.context)
            item_context[item_var] = item_val
            item_context[index_var] = idx
            item_context["loop_item"] = item_val
            item_context["loop_index"] = idx

            # Substitute in task template
            task_copy = json.loads(json.dumps(task_template))
            runner = get_runner(task_copy, item_context)
            return runner.execute()

        threads: list[threading.Thread] = []
        for idx, item in enumerate(items):
            t = threading.Thread(target=lambda i=idx, v=item: results.append(run_item(i, v)), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        any_failed = any(not r.success for r in results)
        return TaskResult(
            success=not any_failed or not stop_on_failure,
            exit_code=max(r.exit_code for r in results) if results else 0,
            result={"iterations": len(items), "results": [r.model_dump() for r in results]},
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )


# ── Data Processor Task ──────────────────────────────────────────────────────

class DataProcessorTaskRunner(BaseTaskRunner):
    def execute(self) -> TaskResult:
        proc_type = self.task_def.get("processor", {}).get("type", "python")
        script_path = self.task_def.get("processor", {}).get("script_path", "")
        fn_name = self.task_def.get("processor", {}).get("fn", "process")
        timeout = self.task_def.get("timeout_s", 60)
        t0 = time.perf_counter()

        input_cfg = self.task_def.get("input", {})
        input_data: Any = None

        if input_cfg.get("type") == "file" and input_cfg.get("path"):
            path = Path(self._interpolate(input_cfg["path"]))
            if path.suffix == ".json":
                input_data = json.loads(path.read_text(encoding="utf-8"))
            elif path.suffix == ".csv":
                import csv
                with open(path, newline="", encoding="utf-8") as f:
                    input_data = list(csv.DictReader(f))
            else:
                input_data = path.read_text(encoding="utf-8")
        elif input_cfg.get("type") == "inline":
            input_data = self._interpolate_obj(input_cfg.get("data"))
        elif input_cfg.get("type") == "http":
            url = self._interpolate(input_cfg.get("url", ""))
            resp = requests.get(url, timeout=30)
            input_data = resp.json()

        output_cfg = self.task_def.get("output", {})

        if proc_type == "python" and script_path:
            result = subprocess.run(
                ["python", str(_ROOT / script_path)],
                input=json.dumps({"input": input_data, "fn": fn_name}),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output: Any = None
            try:
                output = json.loads(result.stdout)
            except Exception:
                output = {"stdout": result.stdout, "stderr": result.stderr}
            return TaskResult(
                success=result.returncode == 0,
                exit_code=result.returncode,
                result={"output": output},
                duration_ms=int((time.perf_counter() - t0) * 1000),
            )

        return TaskResult(success=False, error=f"Unknown processor type: {proc_type}", duration_ms=int((time.perf_counter() - t0) * 1000))


# ── Notify Task ─────────────────────────────────────────────────────────────

class NotifyTaskRunner(BaseTaskRunner):
    def execute(self) -> TaskResult:
        channel = self.task_def.get("channel", "slack")
        template = self._interpolate(self.task_def.get("message_template", "Workflow notification"))
        webhook_url = self._interpolate(self.task_def.get("webhook_url", ""))
        t0 = time.perf_counter()

        if channel == "slack" and webhook_url:
            try:
                resp = requests.post(webhook_url, json={"text": template}, timeout=10)
                return TaskResult(
                    success=resp.status_code == 200,
                    exit_code=0 if resp.status_code == 200 else resp.status_code,
                    result={"channel": "slack", "status_code": resp.status_code},
                    duration_ms=int((time.perf_counter() - t0) * 1000),
                )
            except Exception as e:
                return TaskResult(success=False, error=str(e), duration_ms=int((time.perf_counter() - t0) * 1000))

        return TaskResult(success=True, result={"channel": channel, "skipped": True, "template": template}, duration_ms=int((time.perf_counter() - t0) * 1000))


# ── Factory ─────────────────────────────────────────────────────────────────

_TASK_RUNNERS: dict[str, type[BaseTaskRunner]] = {
    "shell": ShellTaskRunner,
    "python": PythonTaskRunner,
    "http": HttpTaskRunner,
    "docker": DockerTaskRunner,
    "conditional": ConditionalTaskRunner,
    "parallel": ParallelTaskRunner,
    "loop": LoopTaskRunner,
    "data_processor": DataProcessorTaskRunner,
    "notify": NotifyTaskRunner,
}


def get_runner(task_def: dict[str, Any], context: dict[str, Any]) -> BaseTaskRunner:
    task_type = task_def.get("type", "shell")
    runner_cls = _TASK_RUNNERS.get(task_type, ShellTaskRunner)
    return runner_cls(task_def, context)
