"""
cognitive_debt_tracker.py — Epistemic Debt Monitoring & Prioritization
Tracks the interest of cognitive debt and identifies due tasks for the cybernetic loop.
"""
from __future__ import annotations

import logging
import json
from datetime import date, timedelta
from typing import Dict, List, Optional, Any

from models.study_entities import StudyTopic, CognitiveDebt
from storage.data_mesh_adapter import DataMeshAdapter

logger = logging.getLogger(__name__)

class CognitiveDebtTracker:
    """
    Tracks and manages cognitive debt across study topics and development tasks.
    Serves as the 'Sensor' for epistemic drift.
    """

    def __init__(self, adapter: DataMeshAdapter):
        self.adapter = adapter

    def calculate_interest(self, topic: StudyTopic) -> float:
        """
        Calculates the current interest rate for a topic's cognitive debt.
        """
        base_interest = topic.cognitive_debt.interest_rate
        
        importance_multiplier = {
            "primary": 1.5,
            "secondary": 1.0,
            "tertiary": 0.5
        }
        multiplier = importance_multiplier.get(topic.importance_level, 1.0)
        
        interest = base_interest * multiplier
        return round(min(interest, 1.0), 3)

    def identify_critical_debt(self, threshold: float = 0.25) -> List[Dict[str, Any]]:
        """Returns topics where cognitive debt interest exceeds the threshold."""
        critical_topics = []
        
        sql = "SELECT * FROM study_topics"
        with self.adapter.sqlite._get_connection() as conn:
            conn.row_factory = lambda cursor, row: {col[0]: row[i] for i, col in enumerate(cursor.description)}
            rows = conn.execute(sql).fetchall()
            
            for row in rows:
                debt = row.get("cognitive_debt")
                if isinstance(debt, str):
                    debt = json.loads(debt)
                
                interest = debt.get("interest_rate", 0.0) if debt else 0.0
                if interest > threshold:
                    critical_topics.append({
                        "id": row["id"],
                        "title": row.get("title") or row.get("name"),
                        "interest": interest,
                        "importance": row.get("importance_level", "secondary")
                    })
                    
        return critical_topics

    def generate_debt_repayment_plan(self, topic_id: str) -> Dict[str, Any]:
        """Creates a proposed study task to 'pay' the cognitive debt."""
        return {
            "action": "review_concept",
            "reason": "High cognitive debt interest",
            "suggested_duration": 60 
        }
