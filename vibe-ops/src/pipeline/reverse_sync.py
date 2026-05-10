import subprocess
import json
from datetime import date
from typing import List, Dict, Any
from models import DailyMetrics, ChangelogEntry
from storage.data_mesh_adapter import DataMeshAdapter

class ReverseSync:
    """
    Motor de Sincronização Reversa (Reverse Sync).
    Captura dados de execução (Taskwarrior, Git) e atualiza o Data Mesh.
    """

    def __init__(self, adapter: DataMeshAdapter):
        self.adapter = adapter

    def sync_taskwarrior_completed(self, days: int = 1):
        """Busca tasks completadas no Taskwarrior e atualiza métricas."""
        cmd = ["task", "status:completed", f"completed.after:today-{days}d", "export"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                tasks = json.loads(result.stdout)
                print(f"Sincronizadas {len(tasks)} tasks completadas.")
        except Exception as e:
            print(f"Erro ao sincronizar Taskwarrior: {e}")

    def sync_git_commits(self, repo_path: str, days: int = 1):
        pass

    def consolidate_daily_metrics(self):
        pass
