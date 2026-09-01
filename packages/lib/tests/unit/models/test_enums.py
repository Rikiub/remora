from typing import get_args

from remora.models.protocol import Protocol, _ProtocolLiteral


def test_protocol_matches_enum():
    """`_ProtocolLiteral` must stay in sync with the `Protocol` members."""
    assert {item.upper() for item in get_args(_ProtocolLiteral)} == {
        e for e in Protocol
    }
