"""Soul loader for the IKIGAI agent layer."""
from __future__ import annotations
from pathlib import Path

_KNOWN_PROFILES = frozenset({"ikigai-planner", "ikigai-critic", "ikigai-stoic"})
_SOULS_DIR = Path(__file__).parent


def load_soul(profile: str) -> str:
    if not isinstance(profile, str) or not profile.strip():
        raise ValueError(f"profile must be a non-empty string, got {profile!r}")
    if "/" in profile or "\\" in profile or ".." in profile:
        raise ValueError(f"profile name must not contain path separators: {profile!r}")
    if profile not in _KNOWN_PROFILES:
        raise FileNotFoundError(f"soul profile not found: {profile}")
    path = (_SOULS_DIR / profile).with_suffix(".md")
    return path.read_text(encoding="utf-8")


def known_profiles() -> frozenset[str]:
    return _KNOWN_PROFILES
