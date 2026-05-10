import subprocess
import json
from typing import List, Dict, Any

class TaskwarriorSync:
    """
    Legacy/Basic Taskwarrior sync logic.
    """
    def export_tasks(self) -> List[Dict[str, Any]]:
        result = subprocess.run(["task", "export"], capture_output=True, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        return []
