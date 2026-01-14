import yaml

def generate_yaml(data: dict) -> str:
    return yaml.dump(data, sort_keys=False)
