"""Drift test — UEID regex pattern must be byte-equal across both canonical locations.

R1.5 from ``vault/run-continuation/2026-09-21-master-review-revisited.json``.
Codifies the structural invariant mandated by ADR-033: the UEID regex pattern
that lives at ``src/contracts/common.py:_UEID_PATTERN`` (CANONICAL) and the
one consumed by ``sys_ikigai/entities/ueid.py:_UEID_PATTERN`` MUST resolve
to the exact same string. If they drift, every cross-fork join key silently
degrades — one fork validates a UEID that another rejects (or vice versa).

Why this guard is load-bearing:

- The two regexes were reconciled independently across M73 / M73.1 / M73.2
  (see ``memory/ueid-5part-canonical-decision-2026-08-31.md`` and ADR-033 §
  "M73 reconciliation history"). Each reconciliation pass had to touch
  BOTH files in separate commits — a window where the two diverged.
- ``sys_ikigai/entities/ueid.py`` uses Pydantic v2 ``StringConstraints``
  to validate ``UEID = Annotated[str, ...]``; ``src/contracts/common.py``
  uses a custom ``UEID(str)`` subclass. The two validators run on the
  same data but in different layers; inconsistency = silent data-quality
  bugs.

What this test pins:

1. ``_UEID_PATTERN.pattern`` (canonical, compiled) equals the raw-string
   ``_UEID_PATTERN`` consumed by ``sys_ikigai.entities.ueid`` byte-for-byte.
2. Both regexes match the same set of valid UEIDs against a representative
   fixture (canonical 4-part short, canonical 4-part long-UUID, 5-part
   legacy, plus negative cases).
3. The ``sys_ikigai`` file declares an ``_UEID_PATTERN`` symbol that the
   test can import (currently a redeclaration; ADR-033 plans to flip this
   to a re-export, after which the test continues to pass because the
   string content is unchanged).

If any of these is violated, the test FAILS. Drift net guard runs in CI
alongside ``test_drift_extended_invariants.py`` and ``test_drift_invariants.py``.

Run::

    pytest tests/test_ueid_regex_single_source.py -v
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import both pattern sources
# ---------------------------------------------------------------------------
# Canonical (per ADR-014 + ADR-033 R1): src/contracts/common.py defines
# _UEID_PATTERN as a compiled re.Pattern. The bare string lives at
# `.pattern` on the compiled object.
from src.contracts.common import _UEID_PATTERN as _CANONICAL_COMPILED  # type: ignore[attr-defined]

# Bare-namespace consumer (per ADR-033 R2): sys_ikigai/entities/ueid.py
# declares _UEID_PATTERN as a raw string literal that Pydantic's
# StringConstraints(pattern=...) consumes. Today this is a redeclaration
# of the same string; per ADR-033 §"Implementation Rules" R2, future
# edits MUST flip this to `from src.contracts.common import _UEID_PATTERN`.
from sys_ikigai.entities import ueid as _sys_ikigai_ueid_module  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Path resolution — mirror test_drift_extended_invariants.py pattern
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parent.parent  # <repo>/


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _canonical_pattern_string() -> str:
    """Return the canonical regex string from src/contracts/common.py.

    `_UEID_PATTERN` there is a compiled ``re.Pattern``; ``.pattern`` gives
    back the raw string literal that was compiled.
    """
    assert isinstance(_CANONICAL_COMPILED, re.Pattern), (
        f"src.contracts.common._UEID_PATTERN must be a compiled re.Pattern, "
        f"got {type(_CANONICAL_COMPILED).__name__}. If this fires, the "
        f"canonical source has been refactored; update this test."
    )
    return _CANONICAL_COMPILED.pattern


def _sys_ikigai_pattern_string() -> str:
    """Return the regex string consumed by sys_ikigai.entities.ueid.

    `_UEID_PATTERN` there is currently a raw string literal (today the file
    redeclares the regex body; per ADR-033 R2 future edits must replace it
    with a re-export from src.contracts.common). The test treats the value
    opaquely as "whatever object the module exposes under the name
    `_UEID_PATTERN`"; if it is a compiled re.Pattern, we extract `.pattern`;
    if it is a string, we use it directly.
    """
    sys_pat = _sys_ikigai_ueid_module._UEID_PATTERN
    if isinstance(sys_pat, re.Pattern):
        return sys_pat.pattern
    assert isinstance(sys_pat, str), (
        f"sys_ikigai.entities.ueid._UEID_PATTERN must be a str or "
        f"re.Pattern, got {type(sys_pat).__name__}. If this fires, the "
        f"module's contract has changed; update this test."
    )
    return sys_pat


@pytest.fixture(scope="module")
def canonical_pattern_string() -> str:
    """Module-scoped: read once."""
    return _canonical_pattern_string()


@pytest.fixture(scope="module")
def sys_ikigai_pattern_string() -> str:
    """Module-scoped: read once."""
    return _sys_ikigai_pattern_string()


# ---------------------------------------------------------------------------
# Invariant 1 — pattern strings byte-equal
# ---------------------------------------------------------------------------


def test_ueid_pattern_strings_are_byte_equal(
    canonical_pattern_string: str,
    sys_ikigai_pattern_string: str,
) -> None:
    """The canonical regex and the sys_ikigai regex MUST be byte-equal.

    ADR-033 R1 mandates ``src/contracts/common.py`` as the single source
    of truth. The two patterns must be character-identical. If they
    drift, Pydantic ``StringConstraints`` (sys_ikigai) and the
    ``UEID(str)`` subclass (src/contracts/common) will validate the same
    UEID differently — silent data-quality bug across forks.
    """
    assert canonical_pattern_string == sys_ikigai_pattern_string, (
        f"UEID regex patterns have DRIFTED between src/contracts/common.py "
        f"and sys_ikigai/entities/ueid.py.\n"
        f"  Canonical (src/contracts/common.py): {canonical_pattern_string!r}\n"
        f"  Consumer (sys_ikigai/entities/ueid.py): {sys_ikigai_pattern_string!r}\n"
        f"Per ADR-033 R1, the canonical source is src/contracts/common.py "
        f"and any divergence is FORBIDDEN. Edit the canonical, then align "
        f"the consumer (or vice versa per the ADR amendment process)."
    )


def test_ueid_pattern_strings_have_same_length(
    canonical_pattern_string: str,
    sys_ikigai_pattern_string: str,
) -> None:
    """Pinned length check — separate assertion for clearer failure mode."""
    assert len(canonical_pattern_string) == len(sys_ikigai_pattern_string), (
        f"UEID regex pattern length mismatch: "
        f"canonical={len(canonical_pattern_string)} "
        f"sys_ikigai={len(sys_ikigai_pattern_string)}. "
        f"This is the smoking gun for an unsynced edit."
    )


# ---------------------------------------------------------------------------
# Invariant 2 — compiled regex behaves identically on a fixture set
# ---------------------------------------------------------------------------
# Representative fixtures from the canonical regex branches:
# - Branch 1: 4-part short (e.g. `tsk:foo:abc12345:01234567`)
# - Branch 2: 4-part long-UUID (e.g. `tsk:foo:abc12345-1234-...:0123456789abcdef`)
# - Branch 3: 5-part legacy (e.g. `tsk_task:foo:abc12345:01234567`)
# Plus negative cases that must REJECT in both.
VALID_UEIDS = (
    # Branch 1 — 4-part short
    "tsk:foo:abc12345:01234567",
    "hab:sleep-8h:11111111:ffffffff",
    "proj:vaga-remota-2026:00000000:00000000",
    "ikig:test-slug:abcd1234:1234abcd",
    # Branch 2 — 4-part long-UUID
    "tsk:foo:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
    "hab:sleep-8h:11111111-2222-3333-4444-555555555555:ffffffffffffffff",
    # Branch 3 — 5-part legacy (namespace:entity_type:slug:uuid:hash)
    "tsk:task:foo:abc12345:01234567",
    "hab:habit:sleep-8h:11111111:ffffffff",
)
INVALID_UEIDS = (
    "",  # empty
    "tsk",  # only 1 part
    "tsk:foo",  # only 2 parts
    "tsk:foo:abc12345",  # only 3 parts
    "TSK:foo:abc12345:01234567",  # uppercase namespace
    "tsk:FOO:abc12345:01234567",  # uppercase slug
    "tsk:foo:XYZ12345:01234567",  # uppercase hex
    "tsk:foo:abc12345:01234567:extra",  # 5 parts but wrong branch
    "x:foo:abc12345:01234567",  # namespace too short (1 char)
    "toolongnamespace:foo:abc12345:01234567",  # namespace too long (9 chars)
)


@pytest.fixture(scope="module")
def compiled_canonical() -> re.Pattern[str]:
    """Compile the canonical pattern once."""
    return re.compile(_canonical_pattern_string())


@pytest.fixture(scope="module")
def compiled_sys_ikigai() -> re.Pattern[str]:
    """Compile the sys_ikigai pattern once."""
    return re.compile(_sys_ikigai_pattern_string())


@pytest.mark.parametrize("ueid", VALID_UEIDS)
def test_canonical_regex_accepts_valid_ueids(
    ueid: str,
    compiled_canonical: re.Pattern[str],
) -> None:
    """The canonical regex MUST accept every fixture from the three branches."""
    assert compiled_canonical.match(ueid) is not None, (
        f"Canonical UEID regex rejected a valid fixture: {ueid!r}. "
        f"This is a regression on the canonical source. Update the fixture "
        f"set or amend the regex via ADR."
    )


@pytest.mark.parametrize("ueid", VALID_UEIDS)
def test_sys_ikigai_regex_accepts_same_valid_ueids(
    ueid: str,
    compiled_sys_ikigai: re.Pattern[str],
) -> None:
    """The sys_ikigai regex MUST accept every fixture the canonical accepts."""
    assert compiled_sys_ikigai.match(ueid) is not None, (
        f"sys_ikigai UEID regex rejected a valid fixture that the canonical "
        f"accepted: {ueid!r}. The two regexes have DRIFTED — the consumer "
        f"is validating more strictly than the canonical."
    )


@pytest.mark.parametrize("ueid", INVALID_UEIDS)
def test_canonical_regex_rejects_invalid_ueids(
    ueid: str,
    compiled_canonical: re.Pattern[str],
) -> None:
    """The canonical regex MUST reject every invalid fixture."""
    # match() on empty string returns a zero-length match; use fullmatch or
    # explicit pattern anchor (the pattern is anchored with ^...$ so match
    # is equivalent to fullmatch for non-empty inputs).
    if ueid == "":
        assert compiled_canonical.match(ueid) is None
    else:
        assert compiled_canonical.match(ueid) is None, (
            f"Canonical UEID regex accepted an invalid fixture: {ueid!r}. "
            f"This is a regression — the canonical is too permissive."
        )


@pytest.mark.parametrize("ueid", INVALID_UEIDS)
def test_sys_ikigai_regex_rejects_invalid_ueids(
    ueid: str,
    compiled_sys_ikigai: re.Pattern[str],
) -> None:
    """The sys_ikigai regex MUST reject every invalid fixture."""
    if ueid == "":
        assert compiled_sys_ikigai.match(ueid) is None
    else:
        assert compiled_sys_ikigai.match(ueid) is None, (
            f"sys_ikigai UEID regex accepted an invalid fixture: {ueid!r}. "
            f"Either the regex has loosened (regression) or the consumer "
            f"diverged from the canonical."
        )


def test_canonical_and_sys_ikigai_have_identical_match_sets(
    compiled_canonical: re.Pattern[str],
    compiled_sys_ikigai: re.Pattern[str],
) -> None:
    """Aggregate invariant — the two regexes MUST accept the same UEID set.

    Sweeps the entire union of valid + invalid fixtures and asserts the
    accept/reject decision is identical per fixture. This is the strongest
    single-line guarantee that the two patterns are operationally equivalent.
    """
    fixtures = VALID_UEIDS + INVALID_UEIDS
    divergences: list[str] = []
    for ueid in fixtures:
        # Use fullmatch-equivalent semantics: the patterns are anchored
        # (^...$) so .match() on the full string is equivalent.
        canon_accepts = compiled_canonical.match(ueid) is not None
        sys_accepts = compiled_sys_ikigai.match(ueid) is not None
        if canon_accepts != sys_accepts:
            decision_canonical = "ACCEPT" if canon_accepts else "REJECT"
            decision_sys = "ACCEPT" if sys_accepts else "REJECT"
            divergences.append(
                f"  {ueid!r}: canonical={decision_canonical}, sys_ikigai={decision_sys}"
            )
    assert not divergences, (
        "UEID regex accept/reject decisions diverged across canonical "
        "and sys_ikigai:\n" + "\n".join(divergences)
    )


# ---------------------------------------------------------------------------
# Invariant 3 — sys_ikigai module exposes _UEID_PATTERN (consumer contract)
# ---------------------------------------------------------------------------


def test_sys_ikigai_ueid_module_exposes_ueid_pattern() -> None:
    """``sys_ikigai.entities.ueid`` MUST expose ``_UEID_PATTERN``.

    This is the consumer contract that downstream code (Pydantic models,
    validators, mesh adapters) relies on. If a future refactor removes
    the symbol without preserving the import name, every consumer breaks
    silently. ADR-033 R3 explicitly preserves this contract — only the
    regex SOURCE changes (from redeclaration to re-export), not the name.
    """
    assert hasattr(_sys_ikigai_ueid_module, "_UEID_PATTERN"), (
        "sys_ikigai.entities.ueid does not expose _UEID_PATTERN. "
        "Per ADR-033 R3 the symbol name MUST be preserved even if the "
        "source flips to a re-export."
    )


def test_sys_ikigai_ueid_module_exposes_ueid_type() -> None:
    """``sys_ikigai.entities.ueid`` MUST expose the ``UEID`` Annotated type.

    Downstream Pydantic models use ``UEID`` (Annotated[str, ...]) as a
    field type. This symbol must persist across the ADR-033 refactor —
    only the regex source flips, not the public type contract.
    """
    assert hasattr(_sys_ikigai_ueid_module, "UEID"), (
        "sys_ikigai.entities.ueid does not expose UEID. The public type "
        "contract is broken; downstream Pydantic models will fail at "
        "import time."
    )
