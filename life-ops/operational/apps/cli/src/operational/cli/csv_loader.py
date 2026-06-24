r"""CSV I/O for the operational CLI — read/write entity datasets.

The CSV file is the canonical read-only source of truth for datasets
(synthetic, golden, production). The JSON files in TIME_TASKER_STATE_DIR
are the runtime read-write store.

CSV format: one file per dataset, with a `entity_type` column to
discriminate rows. Each row is a single entity serialized via Pydantic's
``model_dump(mode="json")`` — this converts datetimes, dates, times,
sets, and enums to their JSON-compatible string representations.

Schema (header row):
    entity_type,id,field1,field2,...

Conventions:
* All fields stored as JSON strings (e.g. dates as ISO 8601).
* Lists and dicts stored as JSON-encoded strings.
* Empty/null values stored as empty string.
* File encoding: UTF-8 with BOM (utf-8-sig) — Excel-friendly.
* Line endings: CRLF (Windows-friendly) — written via csv.writer with
  lineterminator="\\r\\n".
"""
from __future__ import annotations

import csv
import json
from datetime import date, datetime, time
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable


def _build_model_map() -> dict[str, type]:
    from operational.entities.ajuste_fino import AjusteFino
    from operational.entities.habit import Habit
    from operational.entities.journal import JournalEntry
    from operational.entities.metric import SleepRecord
    from operational.entities.policy import PolicyDecision, PolicySetpoints
    from operational.entities.pomodoro import PomodoroRound
    from operational.entities.routine import Routine, RoutineLog
    from operational.entities.time_block import TimeBlock
    from operational.entities.v3 import (
        DailyReflection,
        DayContext,
        LunchRecord,
        TransicaoRegistrada,
    )
    return {
        "routine": Routine,
        "routine_log": RoutineLog,
        "time_block": TimeBlock,
        "journal_entry": JournalEntry,
        "habit": Habit,
        "sleep_record": SleepRecord,
        "pomodoro_round": PomodoroRound,
        "policy_decision": PolicyDecision,
        "policy_setpoints": PolicySetpoints,
        "ajuste_fino": AjusteFino,
        "day_context": DayContext,
        "daily_reflection": DailyReflection,
        "lunch_record": LunchRecord,
        "transicao": TransicaoRegistrada,
    }


MODEL_MAP: dict[str, type] = _build_model_map()

ENTITY_TYPE_ORDER: tuple[str, ...] = tuple(MODEL_MAP.keys())


def _to_jsonable(value: Any) -> str:
    """Convert any value to a JSON string suitable for a CSV cell.

    - datetime/date/time → ISO format string
    - Enum → .value
    - set → sorted list
    - list/dict → json.dumps
    - other → str(value) or "" for None
    """
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, (set, frozenset)):
        return json.dumps(sorted(value), ensure_ascii=False)
    if isinstance(value, (list, dict, tuple)):
        return json.dumps(
            list(value) if isinstance(value, tuple) else value,
            ensure_ascii=False,
            default=_json_default,
        )
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    return str(value)


def _json_default(obj: Any) -> Any:
    """Fallback JSON encoder for non-native types (datetime, Enum, etc.)."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, time):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (set, frozenset)):
        return sorted(obj)
    msg = f"Object of type {type(obj).__name__} is not JSON serializable"
    raise TypeError(msg)


def _from_jsonable(raw: str, target_type: type | None = None) -> Any:
    """Reverse of _to_jsonable — best-effort parser.

    If target_type is given, attempt a direct cast. Otherwise:
    - "" → None
    - "true"/"false" → bool
    - digit-only → int
    - float-shaped → float
    - JSON-shaped (starts with [, {, ") → json.loads
    - else → raw string
    """
    if raw == "" or raw is None:
        return None
    if raw in ("true", "True"):
        return True
    if raw in ("false", "False"):
        return False
    if target_type is datetime:
        return datetime.fromisoformat(raw)
    if target_type is date:
        return date.fromisoformat(raw)
    if target_type is time:
        return time.fromisoformat(raw)
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    if raw.startswith(("[", "{", '"')):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return raw


def export_to_csv(
    rows: Iterable[tuple[str, str, dict[str, Any]]],
    csv_path: str | Path,
) -> int:
    """Write entities to a CSV file. Returns the number of rows written.

    Args:
        rows: Iterable of (entity_type, entity_id, entity_data_dict).
            entity_data_dict is the result of Pydantic's
            ``model_dump(mode="python")`` — keys are field names, values
            are Python objects (datetimes, enums, etc.).
        csv_path: Destination file path (overwritten if exists).

    Returns:
        int: Number of data rows written (excluding header).
    """
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    all_rows = list(rows)
    type_fields: dict[str, list[str]] = {}
    for etype, _eid, data in all_rows:
        if etype not in type_fields:
            type_fields[etype] = []
        for f in data:
            if f not in type_fields[etype]:
                type_fields[etype].append(f)
    header: list[str] = ["entity_type", "id"]
    seen: set[str] = set()
    for etype in ENTITY_TYPE_ORDER:
        if etype in type_fields:
            for f in type_fields[etype]:
                if f not in seen:
                    header.append(f)
                    seen.add(f)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(header)
        count = 0
        for etype, eid, data in all_rows:
            row = [etype, eid]
            for col in header[2:]:
                if col in data:
                    row.append(_to_jsonable(data[col]))
                else:
                    row.append("")
            writer.writerow(row)
            count += 1
    return count


def import_from_csv(csv_path: str | Path) -> dict[str, list[dict[str, Any]]]:
    """Read entities from a CSV file, grouped by entity_type.

    Args:
        csv_path: Source file path.

    Returns:
        dict: ``{entity_type: [entity_data_dict, ...]}``. Each dict has
        an "id" key added.

    Raises:
        FileNotFoundError: If csv_path does not exist.
        ValueError: If entity_type is unknown or data is malformed.
    """
    path = Path(csv_path)
    if not path.exists():
        msg = f"CSV file not found: {path}"
        raise FileNotFoundError(msg)
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        try:
            header = next(reader)
        except StopIteration as exc:
            msg = "CSV file is empty"
            raise ValueError(msg) from exc
        if len(header) < 2 or header[0] != "entity_type" or header[1] != "id":
            msg = f"Invalid CSV header: expected entity_type,id,... got {header[:5]}"
            raise ValueError(
                msg
            )
        result: dict[str, list[dict[str, Any]]] = {}
        for row_num, row in enumerate(reader, start=2):
            if not row or all(c == "" for c in row):
                continue
            if len(row) != len(header):
                msg = f"Row {row_num} has {len(row)} columns, expected {len(header)}"
                raise ValueError(
                    msg
                )
            etype = row[0]
            eid = row[1]
            if etype not in MODEL_MAP:
                msg = (
                    f"Row {row_num}: unknown entity_type {etype!r} "
                    f"(known: {sorted(MODEL_MAP.keys())})"
                )
                raise ValueError(
                    msg
                )
            data: dict[str, Any] = {"id": eid}
            for i, col in enumerate(header[2:], start=2):
                data[col] = _from_jsonable(row[i])
            result.setdefault(etype, []).append(data)
    return result


def import_from_csv_as_entities(
    csv_path: str | Path,
) -> dict[str, list[Any]]:
    """Like import_from_csv but validates each row through Pydantic.

    Returns:
        dict: ``{entity_type: [Pydantic_instance, ...]}``.

    Raises:
        pydantic.ValidationError: If any row fails validation.
    """
    raw = import_from_csv(csv_path)
    out: dict[str, list[Any]] = {}
    for etype, rows in raw.items():
        model_cls = MODEL_MAP[etype]
        allowed = set(model_cls.model_fields.keys())
        fields_info = model_cls.model_fields
        out[etype] = []
        for r in rows:
            filtered: dict[str, Any] = {}
            for k, v in r.items():
                if k not in allowed:
                    continue
                if v is None:
                    # Drop None if the field has a default (including
                    # None itself for Optional fields) — lets Pydantic
                    # apply the default instead of forcing None.
                    if k in fields_info and fields_info[k].is_required() is False:
                        continue
                filtered[k] = v
            out[etype].append(model_cls.model_validate(filtered))
    return out


__all__ = [
    "ENTITY_TYPE_ORDER",
    "MODEL_MAP",
    "export_to_csv",
    "import_from_csv",
    "import_from_csv_as_entities",
]
