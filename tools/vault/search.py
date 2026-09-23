"""M140 — vault_search.py

Full-text search across `vault/` with line numbers, glob filtering,
frontmatter kind filtering, and structured output.

Commands:
  search QUERY              — substring (case-insensitive) or regex search
       --regex             — interpret QUERY as Python regex
       --glob <pattern>    — restrict files (e.g. 'drafts/*.md', '*.md')
       --kind <kind>       — only files with frontmatter kind=<kind>
       --context N         — N lines of context around each match (default 0)
       --limit N           — max matches (default 100)
       --format FMT        — 'content' | 'paths' | 'json' (default content)
       --case-sensitive    — case-sensitive match (default: insensitive)

Exits 0 if any match found, 1 if none, 2 on error.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path
from typing import Any

# Repo-relative vault path. Use the project's `vault/` directory.
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VAULT = REPO_ROOT / "vault"


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Parse simple YAML-ish frontmatter without external deps.

    Supports `key: value` lines between `---` delimiters at file start.
    Strips quotes. Limited to scalar values (strings, ints).
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    block = text[3:end].strip()
    result: dict[str, str] = {}
    for line in block.splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", line.strip())
        if not m:
            continue
        key = m.group(1)
        val = m.group(2).strip().strip('"').strip("'")
        result[key] = val
    return result


def _list_vault_files(
    vault: Path,
    glob_pattern: str | None = None,
) -> list[Path]:
    """List markdown files in vault, optionally filtered by glob."""
    if not vault.exists():
        return []
    if glob_pattern:
        # Glob is matched against the path relative to vault.
        result: list[Path] = []
        for path in vault.rglob("*.md"):
            rel = path.relative_to(vault).as_posix()
            if fnmatch.fnmatch(rel, glob_pattern):
                result.append(path)
        return sorted(result)
    return sorted(vault.rglob("*.md"))


def search_vault(
    query: str,
    vault: Path = DEFAULT_VAULT,
    *,
    use_regex: bool = False,
    glob_pattern: str | None = None,
    kind: str | None = None,
    context: int = 0,
    limit: int = 100,
    case_sensitive: bool = False,
) -> list[dict[str, Any]]:
    """Search vault for query. Returns list of match dicts.

    Each match: {file: Path, rel_path: str, line: int, match: str,
                 context_before: list[str], context_after: list[str],
                 kind: str|None}
    """
    if not vault.exists():
        return []
    files = _list_vault_files(vault, glob_pattern)
    if kind:
        # Filter by frontmatter kind=kind.
        filtered: list[Path] = []
        for f in files:
            try:
                text = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            fm = _parse_frontmatter(text)
            if fm.get("kind") == kind:
                filtered.append(f)
        files = filtered

    # Compile regex if needed.
    flags = 0 if case_sensitive else re.IGNORECASE
    if use_regex:
        try:
            pat = re.compile(query, flags)
        except re.error as e:
            raise ValueError(f"Invalid regex: {e}") from e
    else:
        # Escape literal query for substring search.
        pat = re.compile(re.escape(query), flags)

    matches: list[dict[str, Any]] = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        lines = text.splitlines()
        rel_path = f.relative_to(vault).as_posix()
        fm = _parse_frontmatter(text) if not kind else {"kind": kind}
        for i, line in enumerate(lines, start=1):
            m = pat.search(line)
            if not m:
                continue
            # Context window.
            start_idx = max(0, i - 1 - context)
            end_idx = min(len(lines), i - 1 + context + 1)
            ctx_before = lines[start_idx : i - 1]
            ctx_after = lines[i : end_idx]
            matches.append({
                "file": str(f),
                "rel_path": rel_path,
                "line": i,
                "match": line,
                "context_before": ctx_before,
                "context_after": ctx_after,
                "kind": fm.get("kind"),
            })
            if len(matches) >= limit:
                return matches
    return matches


def _format_content(matches: list[dict[str, Any]]) -> str:
    """Render matches as `path:line:content` lines (grep-style)."""
    return "\n".join(
        f"{m['rel_path']}:{m['line']}:{m['match']}" for m in matches
    ) + ("\n" if matches else "")


def _format_paths(matches: list[dict[str, Any]]) -> str:
    """Render unique file paths (one per line)."""
    seen: set[str] = set()
    out: list[str] = []
    for m in matches:
        if m["rel_path"] not in seen:
            seen.add(m["rel_path"])
            out.append(m["rel_path"])
    return "\n".join(out) + ("\n" if out else "")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Full-text search across the vault"
    )
    p.add_argument("query", help="Search query (substring or regex with --regex)")
    p.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    p.add_argument("--regex", action="store_true",
                   help="Interpret query as Python regex")
    p.add_argument("--glob", default=None,
                   help="Glob pattern to filter files (relative to vault/)")
    p.add_argument("--kind", default=None,
                   help="Only files with frontmatter kind=<kind>")
    p.add_argument("--context", type=int, default=0,
                   help="Lines of context around each match")
    p.add_argument("--limit", type=int, default=100,
                   help="Max matches to return")
    p.add_argument("--format", choices=("content", "paths", "json"),
                   default="content")
    p.add_argument("--case-sensitive", action="store_true")

    args = p.parse_args(argv)

    try:
        matches = search_vault(
            args.query,
            vault=args.vault,
            use_regex=args.regex,
            glob_pattern=args.glob,
            kind=args.kind,
            context=args.context,
            limit=args.limit,
            case_sensitive=args.case_sensitive,
        )
    except ValueError as e:
        print(f"# Error: {e}", file=sys.stderr)
        return 2

    if args.format == "json":
        # Convert Path fields to strings for JSON.
        out_matches = [
            {**m, "file": str(m["file"])} for m in matches
        ]
        print(json.dumps({
            "query": args.query,
            "match_count": len(out_matches),
            "matches": out_matches,
        }, indent=2))
    elif args.format == "paths":
        print(_format_paths(matches), end="")
    else:
        print(_format_content(matches), end="")

    return 0 if matches else 1


if __name__ == "__main__":
    sys.exit(main())
