"""
schema_registry.py — High-Performance Schema Registry for vibe-ops Data Mesh
Acts as a Gatekeeper using JSON Schema and Pydantic v2 Factory.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import jsonschema
import yaml
from pydantic import BaseModel, ValidationError

# Absolute imports from src
from models import (
    BacklogTask,
    ChangelogEntry,
    DailyMetrics,
    Habit,
    RoadmapItem,
    StudyProject,
    StudyTopic,
    Wave,
)

logger = logging.getLogger(__name__)


class ContractStatus(str, Enum):  # noqa: UP042 - keep (str, Enum) member repr for DB payloads
    ACTIVE = "active"
    DRAFT = "draft"
    DEPRECATED = "deprecated"


@dataclass
class ValidationResult:
    valid: bool
    entity: BaseModel | None = None
    errors: list[str] = field(default_factory=list)
    contract_id: str = ""


class SchemaRegistry:
    """
    Registry central que valida contratos antes da persistência.
    Utiliza uma abordagem de Factory para mapear schemas JSON a classes Pydantic.
    """

    def __init__(self, registry_path: Path | None = None) -> None:
        self.root_dir = Path(__file__).resolve().parent.parent.parent  # vibe-ops/
        self.registry_path = registry_path or (self.root_dir / "schema_registry" / "registry.yaml")
        self._registry: dict[str, Any] = {}
        self._schemas: dict[str, dict[str, Any]] = {}

        # Factory Map: (product, version) -> Pydantic Model
        self._factory_map: dict[str, type[BaseModel]] = {
            "study_topics": StudyTopic,
            "study_projects": StudyProject,
            "roadmaps": RoadmapItem,
            "backlogs": BacklogTask,
            "changelogs": ChangelogEntry,
            "daily_metrics": DailyMetrics,
            "habits": Habit,
            "waves": Wave,
        }

        self._load_registry()

    def _load_registry(self) -> None:
        if not self.registry_path.exists():
            logger.error(f"[SchemaRegistry] Registry file not found at {self.registry_path}")
            return

        with open(self.registry_path, encoding="utf-8") as f:
            self._registry = yaml.safe_load(f)

        logger.info(f"[SchemaRegistry] Loaded registry from {self.registry_path}")

    def _get_schema(self, contract_path: str) -> dict[str, Any]:
        if contract_path not in self._schemas:
            full_path = self.root_dir / contract_path
            with open(full_path, encoding="utf-8") as f:
                self._schemas[contract_path] = json.load(f)
        return self._schemas[contract_path]

    def validate_against_contract(
        self, domain: str, entity_type: str, payload: dict[str, Any], version: str = "1.0.0"
    ) -> ValidationResult:
        """
        Valida um payload contra o JSON Schema e então converte para o modelo Pydantic.
        Implementa o Gatekeeper com Fail-Fast.
        """
        # Map entity_type (snake_case) to product name in registry
        product = entity_type + "s" if not entity_type.endswith("s") else entity_type
        # Special cases for mapping
        if entity_type == "study_topic":
            product = "study_topics"
        if entity_type == "study_project":
            product = "study_projects"

        try:
            # 1. Localizar Metadados do Contrato
            domain_cfg = self._registry.get("domains", {}).get(domain)
            if not domain_cfg:
                return ValidationResult(False, errors=[f"Domain '{domain}' unknown"])

            product_cfg = domain_cfg.get("products", {}).get(product)
            if not product_cfg:
                return ValidationResult(
                    False, errors=[f"Product '{product}' unknown in domain '{domain}'"]
                )

            ver_cfg = product_cfg.get("versions", {}).get(version)
            if not ver_cfg:
                # Try fallback version if provided version is not found
                ver_cfg = product_cfg.get("versions", {}).get("1.0.0")
                if not ver_cfg:
                    return ValidationResult(
                        False, errors=[f"Version '{version}' for product '{product}' unknown"]
                    )

            # 2. Validar JSON Schema (Dura)
            schema = self._get_schema(ver_cfg["contract_path"])
            jsonschema.validate(instance=payload, schema=schema)

            # 3. Converter para Pydantic (Factory)
            model_cls = self._factory_map.get(product)
            if not model_cls:
                return ValidationResult(
                    False, errors=[f"No Pydantic model mapped for product '{product}'"]
                )

            entity = model_cls(**payload)

            return ValidationResult(
                valid=True, entity=entity, contract_id=f"{domain}.{product}.{version}"
            )

        except jsonschema.ValidationError as e:
            return ValidationResult(False, errors=[f"JSON Schema Error: {e.message}"])
        except ValidationError as e:
            return ValidationResult(False, errors=[f"Pydantic Error: {e!s}"])
        except Exception as e:
            return ValidationResult(False, errors=[f"Critical Ingestion Error: {e!s}"])
