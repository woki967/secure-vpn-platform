from scripts.validators import (
    are_domains_unique,
    deployment_mode,
    uses_port_8443,
)

def test_wg_kuma_domains_are_different():
    assert are_domains_unique(
        "vpn.duckdns.org",
        "kuma.duckdns.org"
    )

def test_wg_and_kuma_domains_cannot_be_same():
    assert not are_domains_unique(
        "vpn.duckdns.org",
        "vpn.duckdns.org"
    )

def test_single_mode():
    assert deployment_mode(
        ""
    ) == "single"

def test_dual_mode():
    assert deployment_mode(
        "kuma.duckdns.org"
    ) == "dual"

def test_single_mode_uses_8443():
    assert uses_port_8443(
        "single"
    )

def test_dual_mode_does_not_use_8443():
    assert not uses_port_8443(
        "dual"
    )