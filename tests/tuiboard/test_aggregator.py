"""Tests for tuiboard aggregator — multi-fork task read with dedup."""

from __future__ import annotations
from pathlib import Path

from src.tuiboard.aggregator import TaskAggregator


def test_aggregator_empty_when_no_forks(tmp_path: Path):
    """No tasks.jsonl -> empty list."""
    agg = TaskAggregator(data_dir=tmp_path)
    tasks = agg.aggregate()
    assert tasks == []


def test_aggregator_reads_cli_adapter(tmp_path: Path):
    """Write a tasks.jsonl entry -> aggregator returns it with source='cli'."""
    data_dir = tmp_path
    (data_dir / "data").mkdir(parents=True, exist_ok=True)
    # UEID matches regex: prefix=sc, slug=task, hex=a, hex=0 — both single chars
    (data_dir / "data" / "tasks.jsonl").write_text(
        '{"ueid": "sc:task:a:0:0", "title": "A", "status": "planned"}\n',
        encoding="utf-8",
    )
    agg = TaskAggregator(data_dir=data_dir)
    tasks = agg.aggregate()
    assert len(tasks) == 1
    assert tasks[0].ueid == "sc:task:a:0:0"
    assert tasks[0].title == "A"
    assert tasks[0].status == "planned"
    assert tasks[0].source == "cli"
