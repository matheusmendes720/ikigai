"""
learning_outcome_processor.py — Feedback Loop: Code → Knowledge
Processes changelogs to update epistemic depth and evidence of learning.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Any

from models.project_entities import ChangelogEntry
from storage.data_mesh_adapter import DataMeshAdapter
from pipeline.contracts import DataMeshContract

logger = logging.getLogger(__name__)

class LearningOutcomeProcessor:
    """
    Orchestrates the feedback loop where code execution (Changelog) 
    updates knowledge depth (StudyTopic) and reduces cognitive debt.
    """

    def __init__(self, adapter: DataMeshAdapter):
        self.adapter = adapter
        self.contract_engine = DataMeshContract(adapter)

    def process_changelog(self, changelog: ChangelogEntry):
        """
        Main entry point for processing learning outcomes from a technical change.
        """
        logger.info(f"Processing learning outcomes for changelog {changelog.id}")
        
        for outcome in changelog.learning_outcomes:
            topic_id = outcome.get("topic_fk")
            if not topic_id:
                continue
                
            self._update_topic_depth(topic_id, outcome.get("depth_increase", 0.1))
            self._reduce_cognitive_debt(topic_id, 0.05)
            self._register_evidence(topic_id, changelog.task_uuid_fk)

    def _update_topic_depth(self, topic_id: str, increment: float):
        self.contract_engine._increment_topic_depth(topic_id, increment)

    def _reduce_cognitive_debt(self, topic_id: str, reduction: float):
        sql = "UPDATE study_topics SET cognitive_debt = json_set(cognitive_debt, '$.interest_rate', MAX(0.0, json_extract(cognitive_debt, '$.interest_rate') - ?)) WHERE id = ?"
        with self.adapter.sqlite._get_connection() as conn:
            conn.execute(sql, (reduction, topic_id))

    def _register_evidence(self, topic_id: str, task_uuid: str):
        sql = "UPDATE study_topics SET evidence_of_learning = json_insert(evidence_of_learning, '$[#]', ?) WHERE id = ?"
        with self.adapter.sqlite._get_connection() as conn:
            conn.execute(sql, (task_uuid, topic_id))
