import sys
sys.path.insert(0, "src/ikigai/src/agents/v2")
import profile_switch


def test_new_thread_id_is_uuid():
    tid = profile_switch.new_thread_id()
    assert profile_switch.is_valid_thread_id(tid)


def test_invalid_thread_id():
    assert not profile_switch.is_valid_thread_id("")


def test_parse_profile_command_valid():
    assert profile_switch.parse_profile_command("/profile ikigai-critic") == "ikigai-critic"


def test_parse_profile_command_invalid_name():
    assert profile_switch.parse_profile_command("/profile fake") is None


def test_parse_profile_command_not_command():
    assert profile_switch.parse_profile_command("hello") is None
