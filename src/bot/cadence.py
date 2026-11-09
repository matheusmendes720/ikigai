"""The cadence: the one thing in this bot that happens without a message.

Everything else the bot does is a reaction — a command, a button, an event
from the store. The daily routine is a clock, and a clock is the only trigger
that has no input to fail on: nothing arrives, and the report is expected
anyway.

Three decisions, and each one is a trade:

- **The schedule is COMPUTED, never stored.** A timer persisted across a
  restart is a timer that can fire twice or drift; `next_run(now)` taken from
  the wall clock cannot. The cost is honest: a restart at 22:01 schedules
  tomorrow, so a run the machine missed is lost rather than replayed at a
  strange hour. That is the right loss — a daily note delivered at 09:00 the
  next morning is a note about the wrong day.

- **The offset is a fixed UTC offset, not a timezone name.** `zoneinfo` needs
  the tz database, and a slim container does not always carry one; a name
  that fails to resolve would be a cadence that silently never fires. Brazil
  has had no DST since 2019, so `-03:00` is exact all year. A caller that
  knows its zone may pass `IKIGAI_CADENCE_TZ` and the name wins when it
  resolves.

- **It fails closed, and it fails LOUDLY.** No time, no chat or no agent and
  the loop returns instead of guessing who to wake. A time that is SET and
  malformed raises — a typo must not quietly turn the cadence off, because a
  cadence that never fires and a cadence that was never configured look
  identical from the outside.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from datetime import time as clock_time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

__all__ = ["Cadence", "cadence_from_env"]

AT_ENV = "IKIGAI_CADENCE_AT"
OFFSET_ENV = "IKIGAI_CADENCE_UTC_OFFSET"
TZ_ENV = "IKIGAI_CADENCE_TZ"
ROUTINE_ENV = "IKIGAI_CADENCE_ROUTINE"
CHAT_ENV = "IKIGAI_CADENCE_CHAT_ID"

#: The owner's clock, and the default the deployment runs on.
DEFAULT_OFFSET = "-03:00"
DEFAULT_ROUTINE = "daily-note"

_AT_RE = re.compile(r"^(\d{1,2}):(\d{2})$")
_OFFSET_RE = re.compile(r"^([+-])(\d{1,2})(?::?(\d{2}))?$")

#: The spellings that mean "I turned it off".
#:
#: The deployment ships with a time, so the honest way to stop the cadence is
#: a word that says so — not an empty value, which the compose default would
#: replace with the time again, and not a malformed one, which refuses to
#: boot.
_OFF_VALUES = frozenset({"off", "none", "no", "never"})


@dataclass(frozen=True)
class Cadence:
    """One routine, once a day, at a wall-clock time."""

    at: clock_time
    routine: str
    chat_id: str
    offset: timedelta = timedelta(0)
    zone: ZoneInfo | None = None

    def next_run(self, now: datetime) -> datetime:
        """The first occurrence of `at` strictly after `now`, in UTC.

        Strictly after, and that is what makes a restart safe: a process that
        wakes at 22:00:00.4 asks for the next one and gets tomorrow, so no
        restart loop can deliver the same daily note twice.
        """
        zone = self.zone or timezone(self.offset)
        local = now.astimezone(zone)
        candidate = local.replace(hour=self.at.hour, minute=self.at.minute, second=0, microsecond=0)
        if candidate <= local:
            candidate += timedelta(days=1)
        return candidate.astimezone(UTC)


def _parse_at(raw: str) -> clock_time:
    match = _AT_RE.match(raw.strip())
    if match is None:
        raise ValueError(f"{AT_ENV}={raw!r} is not HH:MM")
    hour, minute = int(match.group(1)), int(match.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"{AT_ENV}={raw!r} is not a real time of day")
    return clock_time(hour=hour, minute=minute)


def _parse_offset(raw: str) -> timedelta:
    match = _OFFSET_RE.match(raw.strip())
    if match is None:
        raise ValueError(f"{OFFSET_ENV}={raw!r} is not +HH:MM")
    sign = -1 if match.group(1) == "-" else 1
    hours = int(match.group(2))
    minutes = int(match.group(3) or 0)
    if hours > 14 or minutes > 59:
        raise ValueError(f"{OFFSET_ENV}={raw!r} is outside every real time zone")
    return sign * timedelta(hours=hours, minutes=minutes)


def _parse_zone(raw: str) -> ZoneInfo | None:
    """The named zone, when this machine can resolve it.

    A name that does not resolve falls back to the fixed offset rather than
    raising: the deployment sets both, and a container without a tz database
    must still run the cadence at the right hour.
    """
    try:
        return ZoneInfo(raw.strip())
    except (ZoneInfoNotFoundError, ValueError):
        return None


def cadence_from_env(env: Mapping[str, str], allowed: set[str]) -> Cadence | None:
    """The cadence the environment asks for, or `None`.

    `None` is not an error: a deployment that does not set `IKIGAI_CADENCE_AT`
    runs the bot exactly as it ran before this module existed.

    The chat is `IKIGAI_CADENCE_CHAT_ID` when it is set, and otherwise the
    first id in the allowlist — sorted, so two processes on the same
    configuration wake the same chat instead of alternating.
    """
    raw_at = (env.get(AT_ENV) or "").strip()
    if not raw_at or raw_at.lower() in _OFF_VALUES:
        return None

    at = _parse_at(raw_at)

    raw_offset = (env.get(OFFSET_ENV) or DEFAULT_OFFSET).strip()
    offset = _parse_offset(raw_offset)

    raw_tz = (env.get(TZ_ENV) or "").strip()
    zone = _parse_zone(raw_tz) if raw_tz else None

    routine = (env.get(ROUTINE_ENV) or DEFAULT_ROUTINE).strip() or DEFAULT_ROUTINE

    raw_chat = (env.get(CHAT_ENV) or "").strip()
    if raw_chat:
        chat_id = raw_chat
    elif allowed:
        chat_id = sorted(allowed)[0]
    else:
        # No allowlist is a bot that refuses to start; reaching here means the
        # cadence has nobody to wake.
        return None

    return Cadence(at=at, routine=routine, chat_id=chat_id, offset=offset, zone=zone)
