from datetime import datetime, date
from typing import List, Optional, Dict, Any
from sqlalchemy import String, Integer, Float, Boolean, Date, DateTime, ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class StudyProjectORM(Base):
    __tablename__ = "study_projects"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str] = mapped_column(String, default="professional")
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0)

class StudyTopicORM(Base):
    __tablename__ = "study_topics"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    parent_study_project: Mapped[Optional[str]] = mapped_column(String, ForeignKey("study_projects.id"))
    depth_level: Mapped[float] = mapped_column(Float, default=0.0)
    cognitive_debt: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    evidence_of_learning: Mapped[List[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String, default="active")

class RoadmapItemORM(Base):
    __tablename__ = "roadmap_items"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    goal_id: Mapped[Optional[str]] = mapped_column(String)
    storypoints: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String, default="pending")
