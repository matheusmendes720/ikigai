from typing import Any


class TaskwarriorSyncAdapter:
    """
    Facade para sincronização entre o Data Mesh e o Taskwarrior.
    """

    def __init__(self):
        pass

    def full_pull(self) -> list[dict[str, Any]]:
        return []

    def full_push(self, entities: list[Any]):
        pass
