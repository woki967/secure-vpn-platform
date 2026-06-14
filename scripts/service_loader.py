import yaml

def load_service(path: str):
    with open(path) as f:
        return yaml.safe_load(f)