import enum
import json
from datetime import datetime
from src.storage.metadata_orm import StateMachineLog

class PipelineState(str, enum.Enum):
    RAW = "RAW"
    VALIDATED = "VALIDATED"
    INDEXED = "INDEXED"
    ENRICHED = "ENRICHED"
    FAILED = "FAILED"

class PipelineStateMachine:
    def __init__(self, session):
        self.session = session

    def transition(self, node_id: str, new_state: PipelineState, event: str, payload: dict = None):
        payload_str = json.dumps(payload) if payload else None
        log = StateMachineLog(
            node_id=node_id,
            current_state=new_state.value,
            last_event=event,
            event_payload=payload_str,
            transitioned_at=datetime.utcnow()
        )
        self.session.add(log)
        self.session.commit()

    def get_trace(self, node_id: str):
        return self.session.query(StateMachineLog).filter_by(node_id=node_id).order_by(StateMachineLog.transitioned_at).all()
