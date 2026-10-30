"""Paperclip ``policy`` module — runtime gates consulted before agent invocation.

The MVP cost gate reads ``data/cost-today.json`` (written by the M7
cost-dashboard when running) and refuses to invoke the AI agent if today's
spend exceeds a configured USD threshold. This is the **first auto-throttle**
in the Paperclip architecture; see ``specs/M169-paperclip/SPEC.md`` Deferred
table "N+1: cost gate in ``policy.py``".

Design notes:

* **Fail-open.** The cost-dashboard may not be running in every env (CI,
  ephemeral containers, dev machines without the daemon). If the file is
  missing or malformed, the gate returns ``(allowed=True, reason="...")``
  so the graph does not break. The "reason" string is still informative —
  callers can log it.
* **Threshold from env.** Default ``$5.00/day``; override via
  ``PAPERCLIP_COST_THRESHOLD_USD`` (float). Read once at ``__init__``
  so the value is captured in the gate instance — tests that mutate the
  env get a fresh gate.
* **Pure stdlib** (``json`` / ``os`` / ``pathlib``); no Pydantic, no MCP,
  no new deps. Mirrors the existing zero-deps policy helpers in
  ``sys_ikigai/security/``.

This module is a leaf — it does not import any Paperclip node or agent
adapter (no risk of circular imports). Nodes that consult the gate
(``nodes/implement.py``) instantiate it at node-call time.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

log = logging.getLogger(__name__)


#: Default daily spend ceiling (USD) when ``PAPERCLIP_COST_THRESHOLD_USD``
#: is unset. $5/day is a conservative default for single-user MVP work
#: (a single Sonnet conversation rarely exceeds $1).
DEFAULT_THRESHOLD_USD: float = 5.00

#: Environment-variable name consulted by ``CostGate.__init__``.
ENV_THRESHOLD: str = "PAPERCLIP_COST_THRESHOLD_USD"

#: Default path to the cost-dashboard JSON file. Resolved relative to
#: the current working directory at ``__init__`` time (not stored as a
#: module-level constant so tests can swap it via ``cost_file=`` kwarg).
DEFAULT_COST_FILE: Path = Path("data/cost-today.json")

#: Default wall-clock ceiling (seconds) when ``PAPERCLIP_WALL_CLOCK_THRESHOLD_S``
#: is unset. 3600s = 1 hour is a conservative default for single-task Paperclip
#: runs (a single Sonnet implement pass typically completes in minutes).
DEFAULT_THRESHOLD_S: int = 3600

#: Environment-variable name consulted by ``WallClockGate.__init__``.
ENV_WALL_CLOCK_THRESHOLD: str = "PAPERCLIP_WALL_CLOCK_THRESHOLD_S"

#: Environment-variable name consulted by ``RiskGate.__init__`` (M176).
#: Comma-separated override for :data:`DEFAULT_RISK_KEYWORDS`. An empty
#: or unset value falls back to the default list (fail-CLOSED default
#: semantics — never silently empty the dangerous-keyword list).
ENV_RISK_KEYWORDS: str = "PAPERCLIP_RISK_KEYWORDS"

#: Default dangerous-keyword list consulted by ``RiskGate.check()`` (M176).
#:
#: Substring match (case-insensitive) against the spec + prompt concatenation.
#: Categories:
#:
#: * Destructive shell — ``rm -rf``, ``drop database``, ``truncate table``.
#: * Git / VCS — ``git push --force``, ``git reset --hard``.
#: * Secrets / credentials — ``.env``, ``secrets``, ``private_key``,
#:   ``id_rsa``, ``~/.ssh``, ``password=``, ``api_key=``.
#: * Persistence — ``chmod 777``, fork-bomb ``:(){:|:&};:``.
#:
#: Overridable via :data:`ENV_RISK_KEYWORDS` (comma-separated).
DEFAULT_RISK_KEYWORDS: tuple[str, ...] = (
    # Destructive shell
    "rm -rf",
    "rm -fr",
    "drop database",
    "drop schema",
    "truncate table",
    # Git / VCS
    "git push --force",
    "git push -f",
    "git push --force-with-lease",
    "git reset --hard",
    # Secrets / credentials
    ".env",
    "secrets",
    "private_key",
    "id_rsa",
    "~/.ssh",
    "password=",
    "api_key=",
    # Persistence
    "chmod 777",
    ":(){:|:&};:",
)


class CostGate:
    """Auto-throttle gate that blocks agent invocation when daily spend is high.

    Attributes:
        cost_file: Path to ``cost-today.json``. ``None`` at construction
            resolves to :data:`DEFAULT_COST_FILE` at the time of the gate.
        threshold_usd: Daily USD ceiling. ``$5.00`` unless
            :data:`ENV_THRESHOLD` is set to a parseable float.

    The gate is **stateless beyond its two attributes** — calling
    ``check()`` repeatedly returns the same answer for the same file
    contents. Construct one gate per node call (cheap, no caching needed).
    """

    def __init__(
        self,
        cost_file: Path | None = None,
        threshold_usd: float | None = None,
    ) -> None:
        """Resolve cost_file + threshold; defer all I/O to ``check()``.

        Args:
            cost_file: path to ``cost-today.json``. Defaults to
                :data:`DEFAULT_COST_FILE` (``data/cost-today.json``).
            threshold_usd: explicit override. When ``None``, the env
                var :data:`ENV_THRESHOLD` is consulted; if unset or
                unparseable, :data:`DEFAULT_THRESHOLD_USD` is used.
        """
        if cost_file is None:
            self.cost_file: Path = DEFAULT_COST_FILE
        else:
            self.cost_file = cost_file

        if threshold_usd is not None:
            self.threshold_usd: float = float(threshold_usd)
        else:
            self.threshold_usd = self._resolve_threshold_from_env()

    @staticmethod
    def _resolve_threshold_from_env() -> float:
        """Read ``PAPERCLIP_COST_THRESHOLD_USD``; fall back to default.

        Invalid (non-float, negative) values fall back silently — fail-open
        is the project-wide invariant for any gate that could break the
        graph if misconfigured.
        """
        raw = os.environ.get(ENV_THRESHOLD)
        if raw is None or raw.strip() == "":
            return DEFAULT_THRESHOLD_USD
        try:
            value = float(raw)
        except ValueError:
            log.warning(
                "paperclip cost gate: %s=%r is not a float; using default $%.2f",
                ENV_THRESHOLD,
                raw,
                DEFAULT_THRESHOLD_USD,
            )
            return DEFAULT_THRESHOLD_USD
        if value < 0:
            log.warning(
                "paperclip cost gate: %s=%r is negative; using default $%.2f",
                ENV_THRESHOLD,
                raw,
                DEFAULT_THRESHOLD_USD,
            )
            return DEFAULT_THRESHOLD_USD
        return value

    def check(self) -> tuple[bool, str]:
        """Decide whether the agent may be invoked right now.

        Returns:
            ``(allowed, reason)`` tuple:

            * ``allowed=True`` — gate is open; caller may proceed to
              invoke the agent. ``reason`` is a short human-readable
              explanation (``"no cost data"``, ``"under threshold"``).
            * ``allowed=False`` — gate is closed; caller MUST refuse to
              invoke the agent. ``reason`` includes the current total
              and threshold so the operator can decide what to do.

            Fail-open semantics (per the SPEC): missing file, malformed
            JSON, missing ``total_usd`` key, non-numeric total, IOError
            all return ``allowed=True``. The rationale is that the
            cost-dashboard daemon may not be running in every env, and
            breaking the Paperclip graph because a sidecar service is
            offline is the wrong default.
        """
        if not self.cost_file.exists():
            return True, f"no cost data (file not found: {self.cost_file})"

        try:
            text = self.cost_file.read_text(encoding="utf-8")
        except OSError as exc:
            log.warning("paperclip cost gate: failed to read %s: %s", self.cost_file, exc)
            return True, f"cost data unreadable ({exc.__class__.__name__}); allowing"

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            log.warning(
                "paperclip cost gate: %s is not valid JSON (%s); allowing",
                self.cost_file,
                exc.msg,
            )
            return True, f"cost data malformed ({exc.msg}); allowing"

        if not isinstance(payload, dict):
            log.warning(
                "paperclip cost gate: %s top-level is %s, not an object; allowing",
                self.cost_file,
                type(payload).__name__,
            )
            return True, "cost data shape unexpected (not an object); allowing"

        total_usd = payload.get("total_usd")
        if total_usd is None:
            return True, "cost data missing total_usd; allowing"
        if not isinstance(total_usd, (int, float)):
            return True, f"cost data total_usd is {type(total_usd).__name__}; allowing"
        total_usd_f = float(total_usd)

        if total_usd_f >= self.threshold_usd:
            return (
                False,
                (f"today's spend ${total_usd_f:.2f} exceeds threshold ${self.threshold_usd:.2f}"),
            )
        return (
            True,
            f"under threshold (${total_usd_f:.2f} / ${self.threshold_usd:.2f})",
        )


__all__ = [
    "DEFAULT_COST_FILE",
    "DEFAULT_RISK_KEYWORDS",
    "DEFAULT_THRESHOLD_S",
    "DEFAULT_THRESHOLD_USD",
    "ENV_RISK_KEYWORDS",
    "ENV_THRESHOLD",
    "ENV_WALL_CLOCK_THRESHOLD",
    "CostGate",
    "RiskGate",
    "WallClockGate",
]


class WallClockGate:
    """Auto-throttle gate that blocks agent invocation when wall-clock duration is too long.

    The M175-paperclip-wall-clock-gate is the **second auto-throttle** in the
    Paperclip architecture, complementing :class:`CostGate` (M173). It reads
    ``state["task_started_at"]`` (an ISO 8601 UTC timestamp set by
    ``read_spec_node`` on first invocation) and refuses to invoke the agent
    if ``now - task_started_at >= threshold_seconds``.

    Fail-open semantics (mirrors :class:`CostGate`): missing or malformed
    ``task_started_at`` returns ``allowed=True`` so the graph does not break.
    The "reason" string is still informative — callers can log it. The
    rationale is that older callers / replayed checkpoints may not carry
    the timestamp, and breaking the Paperclip graph because a field is
    missing is the wrong default.

    Attributes:
        threshold_seconds: Wall-clock ceiling. Default 3600s (1 hour).
            Overridable via env ``PAPERCLIP_WALL_CLOCK_THRESHOLD_S``.

    The gate is **stateless beyond its attributes** — calling ``check()``
    repeatedly for the same ``now_iso`` returns the same answer. Construct
    one gate per node call (cheap, no caching needed).
    """

    def __init__(
        self,
        task_started_at: str | None = None,
        now_iso: str | None = None,
        threshold_seconds: int | None = None,
    ) -> None:
        """Capture inputs. ``now_iso`` is injectable for tests (avoids
        ``datetime.now()`` which is non-deterministic across test runs).

        Args:
            task_started_at: ISO 8601 UTC timestamp from ``state['task_started_at']``.
                ``None`` / empty string → fail-open on ``check()``.
            now_iso: ISO 8601 UTC timestamp representing the current time.
                ``None`` falls back to ``datetime.now(timezone.utc).isoformat()``
                (production path).
            threshold_seconds: explicit override. When ``None``, the env
                var :data:`ENV_WALL_CLOCK_THRESHOLD` is consulted; if
                unset or unparseable, :data:`DEFAULT_THRESHOLD_S` is used.
        """
        self.task_started_at: str | None = task_started_at
        self.now_iso: str | None = now_iso
        if threshold_seconds is not None:
            self.threshold_seconds: int = int(threshold_seconds)
        else:
            self.threshold_seconds = self._resolve_threshold_from_env()

    @staticmethod
    def _resolve_threshold_from_env() -> int:
        """Read ``PAPERCLIP_WALL_CLOCK_THRESHOLD_S``; fall back to default.

        Invalid (non-int, negative) values fall back silently — fail-open
        is the project-wide invariant for any gate that could break the
        graph if misconfigured.
        """
        raw = os.environ.get(ENV_WALL_CLOCK_THRESHOLD)
        if raw is None or raw.strip() == "":
            return DEFAULT_THRESHOLD_S
        try:
            value = int(raw)
        except ValueError:
            log.warning(
                "paperclip wall-clock gate: %s=%r is not an int; using default %ds",
                ENV_WALL_CLOCK_THRESHOLD,
                raw,
                DEFAULT_THRESHOLD_S,
            )
            return DEFAULT_THRESHOLD_S
        if value < 0:
            log.warning(
                "paperclip wall-clock gate: %s=%r is negative; using default %ds",
                ENV_WALL_CLOCK_THRESHOLD,
                raw,
                DEFAULT_THRESHOLD_S,
            )
            return DEFAULT_THRESHOLD_S
        return value

    @staticmethod
    def _parse_iso(value: str) -> datetime | None:
        """Parse an ISO 8601 string into a timezone-aware ``datetime``.

        Accepts both ``...Z`` (Python <3.11 friendly) and ``...+00:00``
        offsets. Returns ``None`` on any parse failure — caller treats
        ``None`` as fail-open.
        """
        # Tolerate trailing 'Z' that ``datetime.fromisoformat`` (pre-3.11)
        # refuses; the Python 3.11+ stdlib handles 'Z' natively but the
        # repo pins ``.python-version = 3.11`` — handle both forms.
        candidate = value.strip()
        if candidate.endswith("Z"):
            candidate = candidate[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed

    def check(self) -> tuple[bool, str]:
        """Decide whether the agent may be invoked right now.

        Returns:
            ``(allowed, reason)`` tuple:

            * ``allowed=True`` — gate is open; caller may proceed to
              invoke the agent. Reasons include ``"no start time"``,
              ``"start time malformed"``, ``"under threshold"``.
            * ``allowed=False`` — gate is closed; caller MUST refuse to
              invoke the agent. ``reason`` includes the elapsed seconds
              and threshold so the operator can decide whether to extend
              the threshold or kill the task.

            Fail-open semantics (per the SPEC): missing ``task_started_at``,
            empty string, unparseable ISO 8601 string, naive-vs-aware
            mismatch, or any combination thereof returns ``allowed=True``.
            The rationale is that older callers / replayed checkpoints may
            not carry the timestamp, and breaking the Paperclip graph
            because a field is missing is the wrong default.
        """
        if not self.task_started_at:
            return True, "no start time (task_started_at missing); allowing"

        started = self._parse_iso(self.task_started_at)
        if started is None:
            log.warning(
                "paperclip wall-clock gate: task_started_at=%r is not valid ISO 8601; allowing",
                self.task_started_at,
            )
            return True, f"start time malformed ({self.task_started_at!r}); allowing"

        now = self._parse_iso(self.now_iso) if self.now_iso else datetime.now(UTC)
        if now is None:
            log.warning(
                "paperclip wall-clock gate: now_iso=%r is not valid ISO 8601; allowing",
                self.now_iso,
            )
            return True, f"current time malformed ({self.now_iso!r}); allowing"

        elapsed = (now - started).total_seconds()
        if elapsed < 0:
            # Defensive: clock skew / replayed checkpoint with future
            # timestamp. Treat as "just started" — the gate never blocks
            # the first invocation.
            return True, f"start time in the future ({elapsed:.1f}s); allowing"

        if elapsed >= self.threshold_seconds:
            return (
                False,
                (f"elapsed {elapsed:.1f}s exceeds wall-clock threshold {self.threshold_seconds}s"),
            )
        return True, f"under threshold ({elapsed:.1f}s / {self.threshold_seconds}s)"


class RiskGate:
    """Auto-throttle gate that BLOCKS agent invocation when spec/prompt
    matches dangerous keyword patterns. **Fail-CLOSED** (unlike
    :class:`CostGate` / :class:`WallClockGate` which are fail-open).

    The M176-paperclip-risk-gate is the **third auto-throttle** in the
    Paperclip architecture. It scans the resolved spec text + the agent
    prompt for dangerous keyword patterns (``rm -rf``, ``git push --force``,
    ``.env``, ``api_key=``, etc.) and refuses to invoke the agent when any
    match is found.

    Rationale: cost overrun wastes money, wall-clock overrun wastes time,
    but a ``rm -rf /`` or ``git push --force`` mistake **destroys state**.
    The risk gate must refuse.

    Attributes:
        text_to_check: Concatenated spec + prompt string the gate scans.
            Empty string is a no-op (returns ``allowed=True``) — the
            caller is responsible for concatenating the right fields.
        keywords: Tuple of substring tokens. Match is **case-insensitive
            substring** against ``text_to_check``. Default from
            :data:`DEFAULT_RISK_KEYWORDS`; overridable via the env
            :data:`ENV_RISK_KEYWORDS` (comma-separated list). An empty
            env value falls back to the default — never silently empty
            the dangerous-keyword list (that would defeat the gate).

    The gate is **stateless beyond its attributes** — calling ``check()``
    repeatedly returns the same answer for the same inputs. Construct one
    gate per node call (cheap, no caching needed).
    """

    def __init__(
        self,
        text_to_check: str = "",
        keywords: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        """Capture inputs. ``text_to_check`` is the spec + prompt
        concatenation (caller responsibility — typically
        ``state.get("spec_text", "") + "\\n" + prompt``).

        Args:
            text_to_check: String to scan for dangerous keywords.
            keywords: Explicit override. When ``None``, the env var
                :data:`ENV_RISK_KEYWORDS` is consulted; if unset or empty,
                :data:`DEFAULT_RISK_KEYWORDS` is used. An empty override
                list (e.g. ``[]``) is honored as "no keywords" — this
                is the documented escape hatch for tests that need to
                disable the gate.
        """
        self.text_to_check: str = text_to_check
        if keywords is not None:
            # Honor explicit override (including empty list for tests).
            self.keywords: tuple[str, ...] = tuple(kw for kw in keywords if kw)
        else:
            self.keywords = self._resolve_keywords_from_env()

    @staticmethod
    def _resolve_keywords_from_env() -> tuple[str, ...]:
        """Read ``PAPERCLIP_RISK_KEYWORDS`` (comma-separated); fall back to default.

        Splits on comma + strips whitespace per item. Empty / unset env
        falls back to :data:`DEFAULT_RISK_KEYWORDS` — this is the
        fail-CLOSED invariant: a missing config MUST NOT silently empty
        the dangerous-keyword list.
        """
        raw = os.environ.get(ENV_RISK_KEYWORDS)
        if raw is None or raw.strip() == "":
            return DEFAULT_RISK_KEYWORDS
        parsed = tuple(item.strip() for item in raw.split(",") if item.strip())
        if not parsed:
            log.warning(
                "paperclip risk gate: %s=%r yielded empty keyword list; using default",
                ENV_RISK_KEYWORDS,
                raw,
            )
            return DEFAULT_RISK_KEYWORDS
        return parsed

    def check(self) -> tuple[bool, str]:
        """Decide whether the agent may be invoked right now.

        Returns:
            ``(allowed, reason)`` tuple:

            * ``allowed=True`` — gate is open; caller may proceed to
              invoke the agent. ``reason`` is a short human-readable
              explanation (e.g. ``"no text to scan"``,
              ``"no dangerous keyword match"``).
            * ``allowed=False`` — gate is closed; caller MUST refuse to
              invoke the agent. ``reason`` lists EVERY matched keyword
              (not just the first) so the operator can decide whether
              to rewrite the spec or force-allow via env.

            Fail-CLOSED semantics: an empty ``text_to_check`` returns
            ``allowed=True`` (nothing to scan), but ANY non-empty text
            with ANY keyword substring match returns ``allowed=False``.
            Unlike :class:`CostGate` / :class:`WallClockGate`, there is
            no "missing data → allow" escape hatch — a missing field
            would let ``rm -rf /`` through, which is exactly what this
            gate exists to prevent.
        """
        if not self.text_to_check:
            return True, "no text to scan (text_to_check is empty); allowing"

        if not self.keywords:
            # Should not happen in production (env override defaults to
            # the dangerous list), but be defensive: if someone has
            # explicitly set PAPERCLIP_RISK_KEYWORDS to a non-empty
            # value AND filtered every keyword, the gate is open.
            return True, "no keywords configured; allowing (explicit override)"

        haystack = self.text_to_check.lower()
        matches: list[str] = []
        for kw in self.keywords:
            if kw.lower() in haystack:
                matches.append(kw)

        if matches:
            quoted = ", ".join(repr(m) for m in matches)
            return (
                False,
                f"dangerous keyword match: {quoted} (refusing; first match is the most likely intent)",
            )

        return True, "no dangerous keyword match"
