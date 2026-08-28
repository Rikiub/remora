from typing import get_args

from remora.models.protocol import Protocol, _ProtocolLiteral


def test_protocol_matches_enum():
    """`ProtocolStr` must stay in sync with the `Protocol` members."""
    assert set(get_args(_ProtocolLiteral)) == {e for e in Protocol}
