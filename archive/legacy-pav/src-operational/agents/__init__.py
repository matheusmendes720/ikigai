"""PAV Agent Harness — CLI entry point."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    from agents.harness.file_harness import FileBasedHarness
    import argparse

    ap = argparse.ArgumentParser(description="PAV Agent Harness Runner")
    ap.add_argument(
        "--workflow",
        default="agents/workflows/qa_swarm.yaml",
        help="Path to workflow YAML",
    )
    ap.add_argument(
        "--dataset",
        default="datasets/6month/synthetic_180d.csv",
        help="Path to synthetic dataset CSV",
    )
    ap.add_argument(
        "--workflow-id",
        default=None,
        help="Override workflow ID",
    )
    ap.add_argument(
        "--node",
        default=None,
        help="Run only a specific node ID",
    )
    args = ap.parse_args()

    harness = FileBasedHarness(
        workflow_path=ROOT / args.workflow,
        dataset_path=ROOT / args.dataset,
        workflow_id=args.workflow_id,
    )

    result = harness.run()
    print("\n" + "=" * 60)
    print("FINAL STATE")
    print("=" * 60)
    for key, val in result.items():
        if isinstance(val, (dict, list)):
            print(f"  {key}: {type(val).__name__} ({len(val)} items)")
        else:
            print(f"  {key}: {val}")
