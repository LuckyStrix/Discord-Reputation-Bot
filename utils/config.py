"""Reads and writes the bot's YAML configuration (data/config.yaml)."""
import yaml

CONFIG_PATH = 'data/config.yaml'


def load_config() -> dict:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(config, f)
