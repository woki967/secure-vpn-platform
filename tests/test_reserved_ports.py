from scripts.validators import (
    is_port_allowed
)

def test_reserved_https():
    assert not is_port_allowed(
        443
    )

def test_reserved_wireguard():
    assert not is_port_allowed(
        51820
    )

def test_allowed_port():
    assert is_port_allowed(
        9000
    )

