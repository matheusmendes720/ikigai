from __future__ import annotations
import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .orm import Base

class MetadataCatalogORM(Base):
    """
    ORM model for the Data Mesh Metadata Catalog.
    Registers all nodes in the mesh and their associated contracts.
    """
    __tablename__ = "mesh_metadata_catalog"

    node_id: Mapped[str] = mapped_column(String, primary_key=True) # Unified Entity ID (UEID)
    domain: Mapped[str] = mapped_column(String)
    source_path: Mapped[Optional[str]] = mapped_column(String) # Onde o dado original está (ex: path do .md)
    contract_id: Mapped[str] = mapped_column(String)
    contract_version: Mapped[str] = mapped_column(String)
    physical_table: Mapped[str] = mapped_column(String)
    vector_collection: Mapped[str] = mapped_column(String)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

class StateMachineORM(Base):
    """
    ORM model for the Data Mesh State Machine.
    Tracks the lifecycle and transitions of data nodes.
    """
    __tablename__ = "mesh_state_machine"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(String, ForeignKey("mesh_metadata_catalog.node_id"))
    current_state: Mapped[str] = mapped_column(String)
    last_event: Mapped[str] = mapped_column(String)
    event_payload: Mapped[dict] = mapped_column(JSON)
    transitioned_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
