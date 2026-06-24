"""Structured time-block parser — convert CSV lines and dicts to TimeBlock entities.

Supports two input formats:

1. **CSV line** — ``id,label,start,end,period,routine_id``
2. **Dict** — from JSON/YAML sources

All parsers strip whitespace and coerce strings to appropriate types.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from operational.entities.time_block import TimeBlock
from operational.enums import Period
from operational.types import UEID

__all__ = [
    "parse_time_block_dict",
    "parse_time_block_line",
    "serialize_time_block_line",
]


def parse_time_block_dict(data: dict[str, Any]) -> TimeBlock:
    """Build a TimeBlock from a dictionary (JSON/YAML source).

    Args:
        data: Dict with keys matching TimeBlock fields. Accepts
            ``start``/``end`` as ISO strings or datetime objects,
            ``period`` as string or Period enum.

    Returns:
        A validated TimeBlock entity.

    Raises:
        ValueError: If required fields are missing or invalid.
    """
    raw_id = str(data.get("id", ""))
    if not raw_id:
        msg = "time_block dict requires 'id' field"
        raise ValueError(msg)

    # Parse start/end
    start = _coerce_datetime(data.get("start", data.get("inicio")))
    end = _coerce_datetime(data.get("end", data.get("fim")))
    if start is None:
        msg_0 = f"time_block {raw_id} missing 'start' field"
        raise ValueError(msg_0)
    if end is None:
        msg_0 = f"time_block {raw_id} missing 'end' field"
        raise ValueError(msg_0)

    # Parse period
    period_raw = data.get("period", data.get("periodo", Period.TARDE.value))
    period = Period(period_raw.upper() if isinstance(period_raw, str) else period_raw)

    return TimeBlock(
        id=UEID(raw_id),
        label=str(data.get("label", data.get("rotulo", ""))),
        start=start,
        end=end,
        period=period,
        routine_id=data.get("routine_id", data.get("rotina_id")),
        energia_nivel=data.get("energia_nivel", data.get("energia")),
        foco_nivel=data.get("foco_nivel", data.get("foco")),
        notes=data.get("notes", data.get("notas", "")),
        created_at=data.get("created_at", datetime.now(UTC)),
    )


def parse_time_block_line(line: str, delimiter: str = ",") -> TimeBlock:
    """Parse a CSV line into a TimeBlock.

    Expected columns:
        ``id, label, start, end, period``

    Example::

        blk_manha_01,Morning workout,2026-06-07T04:00:00,2026-06-07T05:00:00,MANHA

    Args:
        line: CSV line (no header).
        delimiter: Field separator (default ``,``).

    Returns:
        A TimeBlock entity.

    Raises:
        ValueError: If the line has fewer than 5 fields.
    """
    parts = [p.strip() for p in line.split(delimiter)]
    if len(parts) < 5:
        msg = f"Expected at least 5 CSV fields, got {len(parts)}: {line}"
        raise ValueError(
            msg
        )

    raw_id = parts[0]
    label = parts[1] if len(parts) > 1 else ""
    start = _coerce_datetime(parts[2]) if len(parts) > 2 else None
    end = _coerce_datetime(parts[3]) if len(parts) > 3 else None
    period_raw = parts[4] if len(parts) > 4 else Period.TARDE.value

    if start is None:
        msg = f"time_block {raw_id}: could not parse start={parts[2]!r}"
        raise ValueError(msg)
    if end is None:
        msg = f"time_block {raw_id}: could not parse end={parts[3]!r}"
        raise ValueError(msg)

    period = Period(period_raw.upper() if isinstance(period_raw, str) else period_raw)

    return TimeBlock(
        id=UEID(raw_id),
        label=label,
        start=start,
        end=end,
        period=period,
        routine_id=parts[5] if len(parts) > 5 else None,
        energia_nivel=int(parts[6]) if len(parts) > 6 and parts[6] else None,
        foco_nivel=int(parts[7]) if len(parts) > 7 and parts[7] else None,
        notes="",
        created_at=datetime.now(UTC),
    )


def serialize_time_block_line(block: TimeBlock, delimiter: str = ",") -> str:
    """Serialize a TimeBlock to a CSV line.

    Args:
        block: The TimeBlock to serialize.
        delimiter: Field separator.

    Returns:
        CSV string (without trailing newline).
    """
    fields = [
        str(block.id),
        block.label,
        block.start.isoformat() if hasattr(block.start, "isoformat") else str(block.start),
        block.end.isoformat() if hasattr(block.end, "isoformat") else str(block.end),
        block.period.value,
    ]
    if block.routine_id:
        fields.append(str(block.routine_id))
    if block.energia_nivel is not None:
        fields.append(str(block.energia_nivel))
    if block.foco_nivel is not None:
        fields.append(str(block.foco_nivel))
    return delimiter.join(fields)


def _coerce_datetime(raw: Any) -> datetime | None:
    """Parse a datetime from string, datetime, or date."""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str):
        return datetime.fromisoformat(raw)
    msg = f"Cannot coerce {type(raw).__name__} to datetime: {raw!r}"
    raise TypeError(msg)
