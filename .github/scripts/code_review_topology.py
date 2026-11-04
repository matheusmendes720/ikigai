"""Repository topology: which package owns a file, and which lines the diff touched.

The repository is a set of independent packages. Each has its own environment,
its own mypy configuration and its own Ruff configuration. A file therefore
belongs to exactly one bucket, and the review has to run inside that bucket's
own environment — running the packages together in one mypy invocation is not
possible (the Ikigai package would be analysed under a second, competing
module identity).

2026-11-02 (ADR-037 cut): the `vibe-ops`, `interfaces-cli` and `src-mesh`
buckets were removed with the trees they review. The buckets below are the
canonical surface: the DOM, the store client, the domain rules, the MCP
transport, and the package that holds their tests.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from code_review_model import ROOT, PackageSpec, run

# Mirrors the `quality-gates` matrix in .github/workflows/ci.yml.
PACKAGES: tuple[PackageSpec, ...] = (
    PackageSpec(
        name="ikigai",
        path="src/ikigai",
        manager="poetry",
        mypy_target=("-p", "src.ikigai.src"),
        ruff_target="src/",
        pytest=True,
    ),
    # The canonical data layer (ADR-037): the DOM, the Postgres client, the
    # domain rules and the MCP transport. None of them has a pyproject.toml,
    # so they are linted only — their tests live in `src/ikigai/tests/` and
    # run under the `ikigai` entry.
    PackageSpec(
        name="src-contracts",
        path="src/contracts",
        manager="ruff-only",
        ruff_target=".",
    ),
    PackageSpec(
        name="src-data",
        path="src/data",
        manager="ruff-only",
        ruff_target=".",
    ),
    PackageSpec(
        name="src-services",
        path="src/services",
        manager="ruff-only",
        ruff_target=".",
    ),
    PackageSpec(
        name="src-transport",
        path="src/transport",
        manager="ruff-only",
        ruff_target=".",
    ),
)

# The repository root is not a package: it has no lockfile-driven CI entry.
# Its Python files (.github/scripts/, deploy/) are reviewed as one bucket with
# the root environment and the root mypy config.
ROOT_BUCKET = "root"

# The root has no environment of its own that can even collect its tests.
# The canonical suite lives in `src/ikigai/tests/` and runs under the Ikigai
# Poetry environment, with the repository root exposed on PYTHONPATH.
#
# The tool names are resolved lazily (at call time), not at import time: the
# review job must not fail on import when a manager is absent — it has to
# report which environment is missing.
ROOT_TEST_CWD = str(ROOT / "src/ikigai")
ROOT_TEST_PREFIX = ("poetry", "run", "python", "-m", "pytest")
ROOT_TEST_ENV = {"PYTHONPATH": str(ROOT)}

_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


@dataclass
class Bucket:
    """The files of one package that the diff touched."""

    name: str
    spec: PackageSpec | None
    files: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    # repo-relative path -> set of line numbers added by the diff
    touched: dict[str, set[int]] = field(default_factory=dict)

    @property
    def is_root(self) -> bool:
        return self.spec is None


def package_for(rel_path: str) -> PackageSpec | None:
    """Return the package that owns `rel_path`, or None for the root bucket."""
    for spec in PACKAGES:
        if rel_path == spec.path or rel_path.startswith(spec.path + "/"):
            return spec
    return None


def is_test_path(rel_path: str) -> bool:
    name = rel_path.rsplit("/", 1)[-1]
    return "/tests/" in f"/{rel_path}" or name.startswith("test_")


def resolve_base_ref(base_ref: str) -> str | None:
    """Resolve a base branch name to a ref that exists in this checkout.

    In CI the PR is checked out in DETACHED HEAD, so the base branch exists
    only as a remote-tracking ref (`origin/master`) — there is no local
    `master` branch. `git diff master...HEAD` then fails with

        fatal: ambiguous argument 'master...HEAD': unknown revision

    and, because the diff produced no stdout, the reviewer silently treated
    the PR as having ZERO changed files and reported "ALL CHECKS PASSED".
    That is a false green: the job proved nothing.

    Try the name as given, then the remote-tracking form. Return None when
    none resolves, so the caller can fail loudly instead of pretending the
    diff was empty.
    """
    for candidate in (base_ref, f"origin/{base_ref}"):
        probe = run(["git", "rev-parse", "--verify", "--quiet", f"{candidate}^{{commit}}"])
        if probe.returncode == 0 and probe.stdout.strip():
            return candidate
    return None


def diff_touched_lines(base_ref: str) -> dict[str, set[int]]:
    """Map repo-relative path -> set of line numbers ADDED by the diff.

    Findings are attributed to the diff this way: an error on a line the
    change introduced belongs to this change; an error on an untouched line
    is pre-existing debt and must not be used to block the pull request.
    """
    result = run(["git", "diff", "--unified=0", f"{base_ref}...HEAD"])
    if result.returncode != 0:
        raise SystemExit(
            f"code_review: `git diff --unified=0 {base_ref}...HEAD` failed "
            f"(rc={result.returncode}): {result.stderr.strip()}"
        )
    touched: dict[str, set[int]] = {}
    current: str | None = None
    for line in result.stdout.splitlines():
        if line.startswith("+++ "):
            path = line[4:].strip()
            if path.startswith("b/"):
                path = path[2:]
            current = None if path == "/dev/null" else path.replace("\\", "/")
            if current:
                touched.setdefault(current, set())
            continue
        if not current:
            continue
        m = _HUNK.match(line)
        if not m:
            continue
        start = int(m.group(1))
        count = int(m.group(2) or 1)
        touched[current].update(range(start, start + count))
    return touched


def build_buckets(rel_paths: list[str], touched: dict[str, set[int]]) -> list[Bucket]:
    """Group the changed files into per-package buckets."""
    buckets: dict[str, Bucket] = {}
    for pkg in PACKAGES:
        buckets[pkg.name] = Bucket(name=pkg.name, spec=pkg)
    buckets[ROOT_BUCKET] = Bucket(name=ROOT_BUCKET, spec=None)

    for rel in rel_paths:
        rel = rel.replace("\\", "/")
        owner = package_for(rel)
        bucket = buckets[owner.name if owner else ROOT_BUCKET]
        if is_test_path(rel):
            bucket.tests.append(rel)
        else:
            bucket.files.append(rel)
        bucket.touched[rel] = touched.get(rel, set())

    return [b for b in buckets.values() if b.files or b.tests]


def package_cwd(spec: PackageSpec | None) -> str:
    return str(ROOT / spec.path) if spec else str(ROOT)
