from scripts.validators import (
    is_valid_service_name
)

from scripts.validators import is_valid_service_name


def test_valid_service_name():
    assert is_valid_service_name("grafana-prod")


def test_invalid_uppercase():
    assert not is_valid_service_name("Grafana")


def test_invalid_special_char():
    assert not is_valid_service_name("grafana!")

def test_invalid_underscore():
    assert not is_valid_service_name("grafana_prod")

def test_invalid_space():
    assert not is_valid_service_name("grafana prod")

def test_invalid_empty():
    assert not is_valid_service_name("")

def test_valid_numbers():
    assert is_valid_service_name("grafana-prod-01")

def test_invalid_starts_with_hyphen():
    assert not is_valid_service_name("-grafana")

def test_invalid_ends_with_hyphen():
    assert not is_valid_service_name("grafana-")