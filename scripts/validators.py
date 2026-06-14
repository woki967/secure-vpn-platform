import re

RESERVED_PORTS = {80, 443, 8443, 51820}


def is_valid_domain(domain: str) -> bool:
    pattern = re.compile(
        r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$"
    )
    return bool(pattern.match(domain))


def is_valid_service_name(name: str) -> bool:
    return bool(
        re.fullmatch(
            r"[a-z0-9]+(?:-[a-z0-9]+)*",
            name
        )
    )


def is_port_allowed(port: int) -> bool:
    return port not in RESERVED_PORTS


def are_domains_unique(wg_domain: str, kuma_domain: str) -> bool:
    return wg_domain != kuma_domain


def deployment_mode(kuma_domain: str) -> str:
    return "dual" if kuma_domain else "single"


def uses_port_8443(mode: str) -> bool:
    return mode == "single"