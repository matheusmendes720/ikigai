"""A local dry run of the deploy's remote script.

The deploy is the one thing in this repository that cannot be tested by
running the tests: it ships to a box, it needs four secrets, and every
failure it has had was a failure of SHAPE rather than of logic.

So the shape is what gets tested, and this runs it — on the box, with the
real compose, the real git and the real healthcheck wait — before a change
to the pipeline is merged.

    python .github/scripts/deploy_extract_script.py /tmp/deploy.sh
    python .github/scripts/deploy_dry_run.py /tmp/deploy.sh /tmp/dry.sh \\
        /opt/mathe/ikigai <image> <harness-image>

Everything is the real script — byte for byte — with three substitutions:

* the `${{ }}` placeholders become the values the pipeline would pass;
* the `docker login` becomes a no-op, because the Actions token that makes it
  work only exists inside a GitHub job. The images must ALREADY be on the
  box, so the script skips both pulls and the login is the only part that
  would have needed it.

Everything else is untouched: the git checkout, the refspec repair, the
compose up, and the `--wait` on the five services. A dry run that ends with
`compose ps` and a healthy stack proves the transport.
"""

from __future__ import annotations

import sys
from pathlib import Path

#: The one command that needs a credential the dry run cannot have.
_LOGIN = 'docker login ghcr.io --username "$IKIGAI_GHCR_USER" --password-stdin'


def build(script: str, repo_path: str, image: str, harness_image: str) -> str:
    script = script.replace("'${{ secrets.IKIGAI_DEPLOY_PATH }}'", f"'{repo_path}'")
    script = script.replace("'${{ steps.target.outputs.tag }}'", f"'{image}'")
    script = script.replace("'${{ steps.target.outputs.harness }}'", f"'{harness_image}'")
    script = script.replace("'${{ secrets.IKIGAI_DEPLOY_GHCR_TOKEN }}'", "''")
    script = script.replace("'${{ secrets.IKIGAI_DEPLOY_GHCR_USER }}'", "''")
    script = script.replace("'${{ secrets.GITHUB_TOKEN }}'", "''")
    script = script.replace("'${{ github.actor }}'", "''")

    # Replacing the login with `true` makes the `if !` guard a no-op.
    script = script.replace(
        _LOGIN,
        'echo "DRY RUN: the ghcr login is skipped; the images are already on this host"',
    )

    if "${{" in script:
        raise SystemExit("a placeholder survived the substitution")
    if _LOGIN in script:
        raise SystemExit("the login was not neutralised — this would log in for real")
    return script


def main() -> None:
    if len(sys.argv) < 5:
        raise SystemExit(
            f"usage: {sys.argv[0]} IN.sh OUT.sh REPO_PATH IMAGE HARNESS_IMAGE"
        )
    source = Path(sys.argv[1]).read_text(encoding="utf-8")
    out = Path(sys.argv[2])
    script = build(source, sys.argv[3], sys.argv[4], sys.argv[5])
    out.write_text(script, encoding="utf-8", newline="\n")
    print(f"dry run script: {len(script)} bytes -> {out}")


if __name__ == "__main__":
    main()
