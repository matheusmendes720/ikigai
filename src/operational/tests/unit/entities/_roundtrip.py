"""Roundtrip helper for Pydantic v2 models with computed fields.

``model_dump_json()`` includes computed fields by default, which would
then be rejected by ``extra="forbid"`` when re-validating. This helper
builds a nested ``exclude`` dict from class metadata (``computed_fields``)
so that round-tripping remains a pure "user fields in, user fields out"
check. Computed values are re-derived on the decoded model.

The module is **test infrastructure only** — it lives under ``tests/``
and is imported by the entity test files.
"""
from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

__all__ = ["roundtrip"]


T = TypeVar("T", bound=BaseModel)


def _build_exclude(model_cls: type[BaseModel]) -> dict[str, Any]:
    """Build a nested ``exclude`` dict for ``model_dump(exclude=...)``.

    Walks the model class and its ``list[BaseModel]`` fields, collecting
    every computed-field name at every level. The result is a dict
    suitable for direct use as ``exclude=`` in Pydantic's dump methods.

    Args:
        model_cls: A Pydantic ``BaseModel`` subclass.

    Returns:
        A nested dict mapping field names to ``True`` (or to a nested
        ``{"__all__": ...}`` rule for list-typed nested-model fields).
    """
    out: dict[str, Any] = dict.fromkeys(
        model_cls.__pydantic_decorators__.computed_fields, True,
    )
    for fname, finfo in model_cls.model_fields.items():
        ann = finfo.annotation
        origin = getattr(ann, "__origin__", None)
        if origin is list and hasattr(ann, "__args__"):
            inner = ann.__args__[0]
            if isinstance(inner, type) and issubclass(inner, BaseModel):
                nested = _build_exclude(inner)
                if nested:
                    out[fname] = {"__all__": nested}
    return out


def roundtrip(model: T) -> T:
    """JSON roundtrip of a Pydantic v2 model, excluding computed fields.

    The helper produces a JSON payload containing only the user-supplied
    state, then re-validates it with the same model class. Computed
    fields are re-derived on the decoded model automatically.

    Args:
        model: A Pydantic v2 model instance.

    Returns:
        A new instance of the same class, equal to the input under
        Pydantic's ``__eq__`` semantics (which includes computed fields
        when re-derived).
    """
    payload: str = model.model_dump_json(exclude=_build_exclude(type(model)))
    return type(model).model_validate_json(payload)
