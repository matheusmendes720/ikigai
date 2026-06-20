import json
from datetime import date
from unittest.mock import patch, MagicMock
import pytest

from vibe_ops.src.pipeline.knowledge_telemetry import KnowledgeTelemetryPipeline
from vibe_ops.src.models.knowledge_entities import DailyKnowledgeReport

def test_daily_knowledge_report_consolidation():
    # Test 1: Studied 2, Applied 1 + code link
    report = DailyKnowledgeReport(
        id="kr_20260518",
        date=date(2026, 5, 18),
        mental_models_studied=["solid", "cybernetics"],
        mental_models_applied=["solid"],
        code_execution_links=["link1"]
    )
    # Ratio: 1/2 = 0.5. 0.5 * 0.7 = 0.35. Plus 0.3 for code link = 0.65
    assert abs(report.consolidation_kpi - 0.65) < 0.001

    # Test 2: Studied 1, Applied 1, no link
    report2 = DailyKnowledgeReport(
        id="kr_20260519",
        date=date(2026, 5, 19),
        mental_models_studied=["solid"],
        mental_models_applied=["solid"],
        code_execution_links=[]
    )
    # Ratio: 1/1 = 1.0. 1.0 * 0.7 = 0.7. No code link.
    assert abs(report2.consolidation_kpi - 0.7) < 0.001

    # Test 3: Studied 0, Applied 1
    report3 = DailyKnowledgeReport(
        id="kr_20260520",
        date=date(2026, 5, 20),
        mental_models_studied=[],
        mental_models_applied=["cybernetics"],
        code_execution_links=["link2"]
    )
    # Applied but not studied today = 1.0
    assert report3.consolidation_kpi == 1.0

def test_telemetry_generation():
    pipeline = KnowledgeTelemetryPipeline("dummy_script.ps1")
    
    mock_telemetry = [
        {
            "CommitHash": "abc",
            "Date": "2026-05-18T10:00:00Z",
            "Message": "feat: test",
            "ModelsApplied": ["solid"],
            "Link": "link1"
        },
        {
            "CommitHash": "def",
            "Date": "2026-05-18T11:00:00Z",
            "Message": "feat: test 2",
            "ModelsApplied": ["cybernetics"],
            "Link": "link2"
        },
        {
            "CommitHash": "ghi",
            "Date": "2026-05-19T10:00:00Z",
            "Message": "feat: next day",
            "ModelsApplied": ["solid"],
            "Link": "link3"
        }
    ]
    
    studied = {
        date(2026, 5, 18): ["solid", "cybernetics"],
        date(2026, 5, 19): []
    }
    
    reports = pipeline.generate_daily_reports(mock_telemetry, studied)
    
    assert len(reports) == 2
    
    r1 = next(r for r in reports if r.date == date(2026, 5, 18))
    assert set(r1.mental_models_applied) == {"solid", "cybernetics"}
    assert set(r1.mental_models_studied) == {"solid", "cybernetics"}
    assert set(r1.code_execution_links) == {"link1", "link2"}
    # Ratio: 2/2 = 1.0 -> 0.7. Links present -> +0.3 = 1.0
    assert abs(r1.consolidation_kpi - 1.0) < 0.001
    
    r2 = next(r for r in reports if r.date == date(2026, 5, 19))
    assert set(r2.mental_models_applied) == {"solid"}
    assert r2.mental_models_studied == []
    assert set(r2.code_execution_links) == {"link3"}
    # Not studied today but applied = 1.0
    assert r2.consolidation_kpi == 1.0

@patch("vibe_ops.src.pipeline.knowledge_telemetry.subprocess.run")
def test_fetch_telemetry(mock_run, tmp_path):
    # Create a dummy script file to bypass the exists() check
    script_file = tmp_path / "dummy.ps1"
    script_file.write_text("echo hello")
    
    pipeline = KnowledgeTelemetryPipeline(str(script_file))
    
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps([{"CommitHash": "123", "Date": "2026-05-18T00:00:00Z"}])
    mock_run.return_value = mock_result
    
    data = pipeline.fetch_telemetry(".", date(2026, 5, 18))
    assert len(data) == 1
    assert data[0]["CommitHash"] == "123"
