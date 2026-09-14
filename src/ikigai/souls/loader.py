"""Soul loader for the IKIGAI agent layer."""
from __future__ import annotations
from pathlib import Path

_SOULS_DIR = Path(__file__).parent


def _reject_unsafe_profile(profile) -> None:
    """Guard: reject non-str / empty / whitespace / path-traversal profile names.

    Defense-in-depth: must happen BEFORE the filesystem is touched (per
    test_canonical_scope.test_ikigai_serve_soul_loader_chain invariant).
    """
    if not isinstance(profile, str) or not profile.strip():
        raise ValueError(f"profile must be a non-empty string, got {profile!r}")
    if "/" in profile or "\\" in profile or ".." in profile:
        raise ValueError(f"profile name must not contain path separators: {profile!r}")


def _discover_profiles() -> frozenset[str]:
    """Discover soul profiles from the filesystem (single source of truth)."""
    if not _SOULS_DIR.is_dir():
        return frozenset()
    return frozenset(
        entry.name[: -len(".md")]
        for entry in _SOULS_DIR.iterdir()
        if entry.is_file()
        and not entry.name.startswith(".")
        and entry.name.endswith(".md")
    )


def known_profiles() -> frozenset[str]:
    """Return the set of valid soul profile names discovered from disk."""
    return _discover_profiles()


def load_soul(profile: str) -> str:
    """Return the full markdown content of the soul profile."""
    _reject_unsafe_profile(profile)
    available = _discover_profiles()
    if profile not in available:
        raise FileNotFoundError(f"soul profile not found: {profile}")
    path = (_SOULS_DIR / profile).with_suffix(".md")
    return path.read_text(encoding="utf-8")


__all__ = ["load_soul", "known_profiles"]
