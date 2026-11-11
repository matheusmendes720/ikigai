"""The write-back: the store writes the prose back into a tree of markdown.

This is the inverse of the ingestion (`src/services/sync.py`) and it is the
arrow that was missing (ADR-043): the store → the vault. Everything else was
already there — the ingestion writes the store from files, the clients write
the store from tools, and the store announces its changes — so what was
missing was one writer, and the rule that keeps it from destroying work.

Three properties matter more than the mapping:

- **Only NEW files.** The writer writes the artifacts that have no
  `vault_path`: the ones that were never a file. An artifact that HAS one
  belongs to whoever wrote that file, and the writer does not touch it. The
  `vault_path` column is the answer to "is this already a file?", and it was
  built for exactly this (migration `0005`).

- **The conflict is EXPLICIT.** A file that exists with a different hash is
  not rewritten. The prose of the owner is never last-write-wins: the
  divergence is recorded and the file stays as it is.

- **The cycle closes in ONE turn.** The file carries the `ueid` of the store,
  so the ingestion recognises it as the same artifact instead of creating a
  second one; and the writer records in the store WHAT it wrote — the body
  and the path — so the ingestion finds the store already saying `unchanged`.
  Without that second half the ingestion would rewrite the artifact (the
  bytes on disk are the file, the bytes in the store are the prose) and the
  revision would rise on every turn.

The rendered file is a pure function of the artifact's stable fields: no
clock, no timestamp. Two runs over the same artifact produce the same bytes,
which is what makes the write idempotent — and a write that embeds "now"
would rewrite the owner's file on every pass.

The tree is NOT the repository's `vault/`: the deploy does
`git reset --hard origin/main`, so that directory is disposable by design.
The tree this writer uses is a tree of its own on the volume, delivered to
the desktop by Syncthing — no token, no branch, no push.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.contracts.dom import Artifact, WriteRequest
from src.contracts.dom_kinds import typed_fields
from src.data.repository import ArtifactRepository
from src.services.embeddings import EmbeddingService
from src.services.sync import slugify

__all__ = [
    "CLIENT_ID",
    "VAULT_WRITE_INTERVAL_ENV",
    "VAULT_WRITE_ROOTS_ENV",
    "VaultWrite",
    "WriteReport",
    "main",
    "relative_path_for",
    "render_artifact",
]

#: The tree the writer writes into, when the container says so.
#:
#: One tree, not several: the store records the path of the file it wrote in
#: a single column, and two trees would make that column ambiguous. A list
#: with more than one entry is refused rather than silently resolved.
VAULT_WRITE_ROOTS_ENV = "IKIGAI_VAULT_WRITE_ROOTS"

#: How long the loop waits between two write-back runs, in seconds.
VAULT_WRITE_INTERVAL_ENV = "IKIGAI_VAULT_WRITE_INTERVAL"

#: Who the writer says it is, in the store.
#:
#: The store distinguishes its writers: the ingestion is `vault-sync`, the
#: owner and the agent are their own clients. Without a name of its own, the
#: writer's rows would be indistinguishable from the ingestion's.
CLIENT_ID = "vault-write"


@dataclass
class WriteReport:
    """What one write-back run did."""

    scanned: int = 0
    written: int = 0
    unchanged: int = 0
    conflicts: int = 0
    skipped: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.written + self.unchanged + self.conflicts


def default_root() -> Path | None:
    """The tree the writer writes into, or None when it was not configured.

    Without the environment variable it writes nothing at all: a writer with
    no tree is a writer that would put prose somewhere nobody looks.
    """
    raw = (os.environ.get(VAULT_WRITE_ROOTS_ENV) or "").strip()
    if not raw:
        return None
    entries = [entry.strip() for entry in raw.split(",") if entry.strip()]
    if len(entries) != 1:
        raise ValueError(
            f"{VAULT_WRITE_ROOTS_ENV} names {len(entries)} trees; the writer "
            f"writes one, because the store records the path of the file it "
            f"wrote in a single column"
        )
    return Path(entries[0])


def _has_front_matter(body: str) -> bool:
    """Whether the text already carries a YAML frontmatter."""
    return body.startswith("---\n") or body.startswith("---\r\n")


def render_artifact(artifact: Artifact) -> str:
    """The markdown the store becomes.

    The frontmatter carries what the ingestion reads back: the `ueid` (which
    closes the cycle), the title and the status (which the ingestion derives
    from the file, and which therefore have to be the ones the store holds),
    the creation date (a fact about the prose, not a reading of the
    clock), and the typed fields of the kind — a KPI's metric and target, an
    OKR's objective, a decision's rationale. Without them the file would be
    a title with no content, and the kind would lose the very numbers that
    make it what it is.

    NO `updated_at`: the clock would make every run a different file, and a
    write-back that rewrites the file on every pass is a write-back that
    fights the owner's edits.
    """
    body = artifact.body or ""
    if _has_front_matter(body):
        # The body IS a file already — the ingestion wrote it back after the
        # owner edited it. Writing it verbatim is what keeps the frontmatter
        # from being written twice, and what keeps the file's hash equal to
        # the store's.
        return body

    fields: dict[str, Any] = {
        "ueid": str(artifact.uid),
        "title": artifact.title,
    }
    if artifact.status:
        fields["status"] = artifact.status
    if artifact.created_at:
        fields["created_at"] = artifact.created_at.isoformat()
    fields.update(typed_fields(artifact))

    try:
        import yaml

        block = yaml.safe_dump(fields, sort_keys=False, allow_unicode=True).rstrip("\n")
    except ImportError:  # pragma: no cover — PyYAML is a declared dependency
        block = "\n".join(f"{key}: {value}" for key, value in fields.items())

    return f"---\n{block}\n---\n\n{body.rstrip()}\n"


def relative_path_for(artifact: Artifact) -> str:
    """Where the artifact lives in the write-back tree.

    `<kind>/<slug>-<hash>.md`, relative to the tree's root — the same
    relativity the ingestion uses when it records the path it read, so the
    two agree on which file is which.

    The first segment IS the kind, in the DOM's own vocabulary (`nota`,
    `plano`, `kpi`): the ingestion reads the kind from the tree, and a kind
    that is lost in the round trip is a thing that quietly changes what it
    is. The zones layout would turn everything that is not a dream or a plan
    into a note.

    The slug is the title's, so the owner reads the file; the hash is the
    artifact's own, so two notes with the same title do not become one file
    — and the name of a file is never allowed to decide the fate of another
    one's prose.
    """
    name = slugify(artifact.title)
    if artifact.quarter:
        name = f"{name}-{artifact.quarter.lower()}"
    short = str(artifact.uid).rsplit(":", 1)[-1][:8]
    return f"{artifact.kind.value}/{name}-{short}.md"


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _repository_vault() -> Path:
    """The repository's own `vault/` — the tree the deploy discards."""
    return (Path(__file__).resolve().parents[2] / "vault").resolve()


def _assert_writable_tree(root: Path) -> None:
    """Refuse the tree the deploy throws away.

    The deploy does `git reset --hard origin/main`, so everything the
    repository's `vault/` holds is disposable by design: a file written
    there is a file that does not exist after the next deploy — and a commit
    made there is a commit the next deploy silently undoes.

    The write-back's tree is a tree of its own (ADR-043 D1). This is the
    check that keeps the two from ever being confused.
    """
    vault = _repository_vault()
    resolved = root.resolve()
    if resolved == vault or vault in resolved.parents:
        raise ValueError(
            f"the write-back refuses {resolved}: it is inside the repository's "
            f"vault ({vault}), which the deploy discards with `git reset --hard`. "
            f"The write-back writes a tree of its own."
        )


class VaultWrite:
    """Writes the store's prose into a tree of markdown."""

    def __init__(
        self,
        repo: ArtifactRepository,
        *,
        root: Path | None = None,
        client_id: str = CLIENT_ID,
        embeddings: EmbeddingService | None = None,
        limit: int = 500,
    ) -> None:
        self._repo = repo
        self._root = root
        self._client_id = client_id
        self._embeddings = embeddings
        self._limit = limit
        self._written_paths: list[str] = []

    async def write_back(self) -> WriteReport:
        report = WriteReport()
        if self._root is None:
            report.skipped.append(f"{VAULT_WRITE_ROOTS_ENV} is not set")
            return report
        # The refusal comes BEFORE the existence check: the tree the deploy
        # discards is the one that is often NOT there yet, and a writer that
        # creates it would put prose where the next deploy erases it.
        _assert_writable_tree(self._root)
        if not self._root.exists():
            report.skipped.append(f"write root not found: {self._root}")
            return report

        self._written_paths = []
        for artifact in await self._repo.artifacts_without_vault_path(limit=self._limit):
            report.scanned += 1
            await self._write_one(artifact, report)

        await self._commit(report)
        return report

    async def _write_one(self, artifact: Artifact, report: WriteReport) -> None:
        """Write one artifact, and record in the store what was written."""
        assert self._root is not None
        content = render_artifact(artifact)
        digest = _hash(content)
        relative = relative_path_for(artifact)
        target = self._root / relative

        if target.exists():
            existing = _hash(target.read_text(encoding="utf-8"))
            if existing != digest:
                # THE CONFLICT. The file on disk is not the file the store
                # describes: somebody edited it. It is not rewritten — the
                # prose of a human is not last-write-wins — and the
                # divergence is recorded.
                report.conflicts += 1
                report.skipped.append(f"{relative}: the file on disk differs from the store")
                return
            # The file is already what the store describes. The store may
            # still not know it exists — that is the case where a previous
            # round wrote the file and the write to the store was refused —
            # so the record is still made below.
            report.unchanged += 1
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            # LF, always: the file travels to a Windows desktop through the
            # Syncthing, and a file whose bytes depend on the platform that
            # wrote it is a file whose hash is a property of the machine.
            target.write_text(content, encoding="utf-8", newline="\n")
            report.written += 1
            self._written_paths.append(relative)

        await self._record(artifact, content, digest, relative, report)

    async def _record(
        self,
        artifact: Artifact,
        content: str,
        digest: str,
        relative: str,
        report: WriteReport,
    ) -> None:
        """Tell the store what was written.

        The store's body becomes the FILE, exactly as it does for every
        artifact that came from a file, and the `vault_path` says which file.
        That is what makes the ingestion find the store already saying
        `unchanged` instead of rewriting the artifact on the next pass.

        The write goes through the same versioned path as every other write
        (ADR-037 D5): a revision that moved under the writer's feet is a
        conflict, and a conflict is recorded, never forced.
        """
        updated = artifact.model_copy(
            update={
                "body": content,
                "body_hash": digest,
                "vault_path": relative,
            }
        )
        request = WriteRequest(
            artifact=updated,
            expected_revision=artifact.revision,
            idempotency_key=f"vault-write:{artifact.uid}:{digest[:16]}:{artifact.revision}",
            client_id=self._client_id,
        )
        try:
            embedding = None
            if self._embeddings is not None:
                embedding = await self._embeddings.embed_artifact(updated)
            await self._repo.upsert(request, embedding=embedding)
        except Exception as exc:  # one artifact must not stop the run
            report.skipped.append(f"{artifact.uid}: {exc}")

    async def _commit(self, report: WriteReport) -> None:
        """A local commit, when the tree is a repository.

        Never a push: the writer has no credential, and the Syncthing delivers
        the file to the desktop without one. When the tree is not a
        repository the file is still on disk — only the git record is lost,
        and that is the whole loss.

        Only the files THIS RUN wrote are staged. The tree may hold the
        owner's own edits, and a commit that swallowed them would be a commit
        the owner did not ask for.
        """
        assert self._root is not None
        if not self._written_paths:
            return
        if not (self._root / ".git").exists():
            report.skipped.append(f"{self._root} is not a git repository; no commit")
            return
        try:
            subprocess.run(
                ["git", "-C", str(self._root), "add", "--", *self._written_paths],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(self._root),
                    "-c",
                    "user.name=ikigai vault-write",
                    "-c",
                    "user.email=vault-write@localhost",
                    "commit",
                    "-m",
                    "vault_write: a prosa do store",
                ],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as exc:
            report.skipped.append(f"the commit failed: {exc}")


def _report_line(report: WriteReport) -> str:
    return (
        f"scanned={report.scanned} written={report.written} "
        f"unchanged={report.unchanged} conflicts={report.conflicts} "
        f"skipped={len(report.skipped)}"
    )


async def _run(interval: int) -> int:
    """Write back, then wait, then write back again — forever, or once."""
    from src.data.client import DataClient

    client = DataClient()
    repo = ArtifactRepository(client)
    writer = VaultWrite(repo, root=default_root(), embeddings=EmbeddingService(client))

    while True:
        try:
            report = await writer.write_back()
            print(_report_line(report), flush=True)
            for skipped in report.skipped:
                print(f"skipped: {skipped}", file=sys.stderr, flush=True)
        except Exception as exc:  # a failed round is not a dead loop
            print(f"write-back failed: {exc}", file=sys.stderr, flush=True)
        if interval <= 0:
            return 0
        await asyncio.sleep(interval)


def main(argv: list[str] | None = None) -> int:
    """Run the write-back.

        python -m src.services.vault_write                # one round, then stop
        python -m src.services.vault_write --interval 300  # every five minutes

    The interval also comes from ``IKIGAI_VAULT_WRITE_INTERVAL``, which is how
    the container asks for the loop without changing the command.
    """
    parser = argparse.ArgumentParser(prog="python -m src.services.vault_write")
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="seconds between two runs; 0 (the default) runs once and stops",
    )
    args = parser.parse_args(argv)

    raw_interval = args.interval
    if raw_interval is None:
        raw_interval = int((os.environ.get(VAULT_WRITE_INTERVAL_ENV) or "0").strip() or 0)

    from src.data.client import ensure_compatible_event_loop

    ensure_compatible_event_loop()
    try:
        return asyncio.run(_run(max(0, raw_interval)))
    except KeyboardInterrupt:  # pragma: no cover — the container stops it
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
