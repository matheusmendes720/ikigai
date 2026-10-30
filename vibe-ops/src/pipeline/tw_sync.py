import json
import subprocess
from typing import Any


class TaskwarriorSync:
    """
    Legacy/Basic Taskwarrior sync logic.
    """

    def export_tasks(self) -> list[dict[str, Any]]:
        result = subprocess.run(["task", "export"], capture_output=True, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        return []
