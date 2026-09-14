import sys
sys.path.insert(0, "src/ikigai/src/agents/v2")
from sse_publisher import AgentSSEPublisher, EVENT_TAXONOMY


class FakeGateway:
    def __init__(self):
        self.events = []
    def publish_event(self, event, payload):
        self.events.append((event, payload))


def test_publisher_has_9_methods():
    pub = AgentSSEPublisher()
    for ev in EVENT_TAXONOMY:
        method_name = "publish_" + ev.replace(".", "_")
        assert hasattr(pub, method_name)


def test_publisher_emits_9_events():
    gw = FakeGateway()
    pub = AgentSSEPublisher(gw)
    pub.publish_thread_created("t1", "p", "s")
    pub.publish_profile_switched("p", "c")
    pub.publish_entry_message("e1", "u", "n", "hi")
    pub.publish_entry_proposal("e2", "p1", "draft")
    pub.publish_proposal_status_changed("p1", "draft", "ready")
    pub.publish_proposal_approved("p1", "n", "u")
    pub.publish_proposal_rejected("p2", "n", "no")
    pub.publish_thread_closed("t1", "n", "s.md")
    pub.publish_handoff_visible("c", "s", "ctx")
    assert len(gw.events) == 9


def test_publisher_no_op_when_no_gateway():
    pub = AgentSSEPublisher()
    pub.publish_thread_created("t1", "p", "s")
