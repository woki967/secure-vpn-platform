from scripts.service_loader import (
	load_service
)

def test_service_name():
	service = load_service(
		"tests/data/service.yml"
	)
	
	assert service["name"] == "grafana"

def test_service_vpn_ip():
	service = load_service(
		"tests/data/service.yml"
	)
	
	assert service["vpn_ip"] == "10.8.0.2"
	
def test_service_has_domain():
	service = load_service(
		"tests/data/service.yml"
	)
	
	assert service["has_domain"] is True