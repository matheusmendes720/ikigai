import pytest
from src.contracts.common import UEID


@pytest.mark.parametrize("valid_ueid", [
    "tsk:byd-case-review:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
    "tsk:slug:00000000-0000-0000-0000-000000000000:0000000000000000",
    "tsk:a-b-c:11111111-2222-3333-4444-555555555555:ffffffffffffffff",
])
def test_ueid_accepts_valid_5_part_format(valid_ueid):
    """UEID type accepts 5-part format: type:slug:uuid:hash."""
    result = UEID(valid_ueid)
    assert str(result) == valid_ueid


@pytest.mark.parametrize("invalid_ueid", [
    "tsk",                                  # too few parts
    "tsk:slug",                              # missing uuid and hash
    "tsk:slug:abc",                          # missing hash
    "TSK:slug:uuid:hash",                    # uppercase
    "ts:slug:uuid:hash",                     # prefix too short (2 chars min)
    "toolong:slug:uuid:hash",                # prefix too long (5 chars max)
    "tsk:slug:not-a-uuid:hash",              # malformed uuid
    "",                                      # empty
    "tsk:slug:uuid:",                        # empty hash
    "tsk:slug with space:uuid:hash",         # spaces
    "tsk:slug:abc12345-1234-5678-9abc-def012345678:",  # empty hash part
    "tsk:slug::abc12345-1234-5678-9abc-def012345678",  # empty uuid part
    "tsk:slug:abc12345-1234-5678-9abc-def012345678:0123456789abcdef:extra",  # too many parts
    "tsk:slug:ABC12345-1234-5678-9ABC-DEF012345678:0123456789abcdef",  # uppercase in uuid
    "tsk:slug:abc12345-1234-5678-9abc-def012345678:0123456789ABCDEF",  # uppercase in hash
    "-tsk:slug:uuid:hash",                   # leading dash
    "tsk:slug:uuid:hash-",                   # trailing dash
    "tsk:-slug:uuid:hash",                   # leading dash in slug
])
def test_ueid_rejects_invalid_format(invalid_ueid):
    """UEID type rejects malformed input."""
    with pytest.raises(ValueError):
        UEID(invalid_ueid)
