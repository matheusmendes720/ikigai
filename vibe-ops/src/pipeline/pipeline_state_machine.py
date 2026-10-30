import enum
from datetime import datetime

from storage.metadata_orm import StateMachineORM


class PipelineState(str, enum.Enum):  # noqa: UP042 - keep (str, Enum) member repr for DB payloads
    RAW = "RAW"
    VALIDATED = "VALIDATED"
    INDEXED = "INDEXED"
    ENRICHED = "ENRICHED"
    FAILED = "FAILED"


class PipelineStateMachine:
    def __init__(self, session):
        self.session = session

    def transition(
        self,
        node_id: str,
        new_state: PipelineState,
        event: str,
        payload: dict | None = None,
    ):
        log = StateMachineORM(
            node_id=node_id,
            current_state=new_state.value,
            last_event=event,
            event_payload=payload,
            transitioned_at=datetime.utcnow(),
        )
        self.session.add(log)
        self.session.commit()

    def get_trace(self, node_id: str):
        return (
            self.session.query(StateMachineORM)
            .filter_by(node_id=node_id)
            .order_by(StateMachineORM.transitioned_at)
            .all()
        )
