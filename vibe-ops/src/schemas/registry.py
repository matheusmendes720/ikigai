import semver
from pydantic import BaseModel


class SchemaRegistry:
    def __init__(self):
        self._schemas: dict[str, dict[str, type[BaseModel]]] = {}

    def register(self, name: str, version: str, schema: type[BaseModel]):
        if not semver.VersionInfo.is_valid(version):
            raise ValueError(f"Invalid SemVer version: {version}")

        if name not in self._schemas:
            self._schemas[name] = {}

        self._schemas[name][version] = schema

    def validate(self, name: str, version: str, data: dict) -> BaseModel:
        if name not in self._schemas or version not in self._schemas[name]:
            # Fallback para a versão mais próxima se necessário, ou erro estrito
            raise ValueError(f"Schema {name} v{version} not found in registry")

        schema_cls = self._schemas[name][version]
        return schema_cls(**data)

    def get_latest_version(self, name: str) -> str | None:
        if name not in self._schemas:
            return None
        versions = list(self._schemas[name].keys())
        return max(versions, key=lambda v: semver.VersionInfo.parse(v))


# Exemplo de Contrato V2
class TaskContractV2(BaseModel):
    id: str
    description: str
    status: str
    project_hierarchy: str  # S1.O2.M3
    cognitive_load: int = 1  # 1-5
    tags: list[str] = []


registry = SchemaRegistry()
registry.register("task", "2.0.0", TaskContractV2)
