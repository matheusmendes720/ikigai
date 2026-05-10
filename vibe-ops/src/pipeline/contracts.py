import logging
from typing import List, Dict, Any, Optional
from storage.data_mesh_adapter import DataMeshAdapter
from models.study_entities import StudyTopic
from models.project_entities import BacklogTask
from storage.ueid import UEID

logger = logging.getLogger(__name__)

class DataMeshContract:
    """
    DataMeshContract: Encapsulates the rules of the mesh for the Cybernetic Feedback Loop.
    Manages the Target-Sensor-Adjuster orchestration.
    """

    def __init__(self, adapter: DataMeshAdapter):
        self.adapter = adapter

    def rule_update_topic_depth(self, task_id: str, status: str):
        """
        Triggers when a development task is marked as 'done' to increment 
        the associated study_topic.depth_level by 0.1 (Evidence of Learning).
        """
        if status.lower() != "done":
            return

        logger.info(f"Triggering rule_update_topic_depth for task {task_id}")

        backlogs = self._find_backlogs_by_task_id(task_id)
        
        for backlog_data in backlogs:
            tasks = backlog_data.get("tasks", [])
            if isinstance(tasks, str):
                import json
                tasks = json.loads(tasks)
            
            for task in tasks:
                if task.get("task_uuid") == task_id or task.get("title") == task_id:
                    prereqs = task.get("knowledge_prerequisites", [])
                    for prereq in prereqs:
                        topic_id = prereq.get("topic_fk")
                        if topic_id:
                            self._increment_topic_depth(topic_id, 0.1)

    def rule_cognitive_debt_alert(self) -> List[Dict[str, Any]]:
        """
        Monitors interest_rate on cognitive debt; if > 0.25, 
        defines a 'Debt Payment' task payload for TW.
        """
        logger.info("Checking cognitive debt alerts")
        alerts = []
        
        topics_data = self._get_all_entities("study_topics")
        
        for topic_data in topics_data:
            cog_debt = topic_data.get("cognitive_debt")
            if isinstance(cog_debt, str):
                import json
                cog_debt = json.loads(cog_debt)
            
            if cog_debt and cog_debt.get("interest_rate", 0) > 0.25:
                topic_id = topic_data.get("id")
                topic_title = topic_data.get("title") or topic_data.get("name")
                
                alert = {
                    "task": f"Debt Payment: Refine mental model for {topic_title}",
                    "project": topic_data.get("parent_study_project"),
                    "priority": "H",
                    "tags": ["cognitive_debt", "vibe-ops"],
                    "ueid": UEID.create("study", "topic", topic_id),
                    "reason": f"Interest rate {cog_debt.get('interest_rate')} exceeds 0.25"
                }
                alerts.append(alert)
                logger.warning(f"Cognitive debt alert for {topic_id}: {alert['reason']}")
        
        return alerts

    def integrity_check_orphans(self) -> List[str]:
        """
        Identify study topics without a parent project.
        """
        logger.info("Running integrity check for orphans")
        orphans = []
        
        topics = self._get_all_entities("study_topics")
        projects = self._get_all_entities("study_projects")
        project_ids = {p.get("id") for p in projects}
        
        for topic in topics:
            parent_id = topic.get("parent_study_project")
            if not parent_id or parent_id not in project_ids:
                orphans.append(topic.get("id"))
                logger.error(f"Orphan topic found: {topic.get('id')} (parent: {parent_id})")
        
        return orphans

    def _get_all_entities(self, table_name: str) -> List[Dict[str, Any]]:
        sql = f"SELECT * FROM {table_name}"
        with self.adapter.sqlite._get_connection() as conn:
            conn.row_factory = lambda cursor, row: {col[0]: row[i] for i, col in enumerate(cursor.description)}
            return conn.execute(sql).fetchall()

    def _find_backlogs_by_task_id(self, task_id: str) -> List[Dict[str, Any]]:
        all_backlogs = self._get_all_entities("dev_backlogs")
        matching = []
        for bl in all_backlogs:
            tasks = bl.get("tasks", [])
            if isinstance(tasks, str):
                import json
                tasks = json.loads(tasks)
            for t in tasks:
                if t.get("task_uuid") == task_id:
                    matching.append(bl)
                    break
        return matching

    def _increment_topic_depth(self, topic_id: str, increment: float):
        topic_data = self.adapter.sqlite.get_entity("study_topics", topic_id)
        if topic_data:
            current_depth = topic_data.get("depth_level", 0.0)
            new_depth = min(current_depth + increment, 5.0)
            
            with self.adapter.sqlite._get_connection() as conn:
                conn.execute(
                    "UPDATE study_topics SET depth_level = ? WHERE id = ?",
                    (new_depth, topic_id)
                )
            logger.info(f"Updated topic {topic_id} depth from {current_depth} to {new_depth}")
