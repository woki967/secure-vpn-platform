from scripts.validators import (
    is_valid_domain
)

def test_valid_domain():
    assert is_valid_domain(
        "grafana.duckdns.org"
    )

def test_invalid_domain_without_tld():
    assert not is_valid_domain(
        "grafana"
    )

def test_invalid_domain_with_spaces():
    assert not is_valid_domain(
        "grafana test.org"
    )