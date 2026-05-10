from typing import Tuple

class UEID:
    """
    Gerenciador de Unified Entity ID para o Data Mesh.
    Formato: <CLUSTER>:<ENTITY_TYPE>:<ID>
    """

    @staticmethod
    def create(cluster: str, entity_type: str, entity_id: str) -> str:
        return f"{cluster}:{entity_type}:{entity_id}"

    @staticmethod
    def parse(ueid: str) -> Tuple[str, str, str]:
        parts = ueid.split(":")
        if len(parts) != 3:
            raise ValueError(f"UEID inválido: {ueid}")
        return parts[0], parts[1], parts[2]
