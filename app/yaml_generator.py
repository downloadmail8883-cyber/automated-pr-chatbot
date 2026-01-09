"""
Generate YAML from intake dictionary.
"""
import yaml

def generate_yaml(database_name_dict: dict) -> str:
    """Generate YAML string from intake dictionary."""
    return yaml.dump(database_name_dict, sort_keys=False)
