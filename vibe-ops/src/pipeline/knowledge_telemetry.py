import json
import subprocess
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from vibe_ops.src.models.knowledge_entities import DailyKnowledgeReport

class KnowledgeTelemetryPipeline:
    """
    Pipeline to ingest execution telemetry (e.g. from GitHub) and correlate it 
    with abstract study (Mental Models).
    """
    
    def __init__(self, script_path: Optional[str] = None):
        # Default path relative to this file if not provided
        if script_path is None:
            base_dir = Path(__file__).parent.parent.parent
            self.script_path = base_dir / "scripts" / "audit_github_execution.ps1"
        else:
            self.script_path = Path(script_path)
            
    def fetch_telemetry(self, repo_path: str, since_date: date) -> List[Dict[str, Any]]:
        """
        Executes the PowerShell telemetry script and returns the parsed JSON.
        """
        if not self.script_path.exists():
            raise FileNotFoundError(f"Telemetry script not found at {self.script_path}")
            
        cmd = [
            "powershell.exe", 
            "-NoProfile", 
            "-ExecutionPolicy", "Bypass", 
            "-File", str(self.script_path),
            "-RepoPath", repo_path,
            "-SinceDate", since_date.strftime("%Y-%m-%d")
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Telemetry script failed:\n{result.stderr}")
            
        try:
            data = json.loads(result.stdout)
            return data
        except json.JSONDecodeError:
            # Empty output or parse error
            return []

    def generate_daily_reports(self, telemetry_data: List[Dict[str, Any]], studied_models_by_date: Dict[date, List[str]] = None) -> List[DailyKnowledgeReport]:
        """
        Groups telemetry by date and generates DailyKnowledgeReport entities.
        """
        if studied_models_by_date is None:
            studied_models_by_date = {}
            
        # Group by date
        grouped: Dict[date, Dict[str, Any]] = {}
        
        for item in telemetry_data:
            # Parse ISO date string
            # e.g. "2026-05-18T10:11:12Z" or "2026-05-18T10:11:12-03:00"
            dt = datetime.fromisoformat(item["Date"].replace("Z", "+00:00"))
            d = dt.date()
            
            if d not in grouped:
                grouped[d] = {
                    "models_applied": set(),
                    "links": set()
                }
                
            grouped[d]["models_applied"].update(item.get("ModelsApplied", []))
            if item.get("Link"):
                grouped[d]["links"].add(item["Link"])
                
        reports = []
        # Create reports for dates that have telemetry
        for d, data in grouped.items():
            report_id = f"kr_{d.strftime('%Y%m%d')}"
            studied = studied_models_by_date.get(d, [])
            
            report = DailyKnowledgeReport(
                id=report_id,
                date=d,
                mental_models_studied=studied,
                mental_models_applied=list(data["models_applied"]),
                code_execution_links=list(data["links"])
            )
            reports.append(report)
            
        # Add reports for dates that only have studied models but no execution
        for d, studied in studied_models_by_date.items():
            if d not in grouped:
                report_id = f"kr_{d.strftime('%Y%m%d')}"
                report = DailyKnowledgeReport(
                    id=report_id,
                    date=d,
                    mental_models_studied=studied,
                    mental_models_applied=[],
                    code_execution_links=[]
                )
                reports.append(report)
                
        return sorted(reports, key=lambda r: r.date)
