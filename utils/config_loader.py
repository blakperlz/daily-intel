"""Loads config.yaml and merges with .env secrets."""
import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

load_dotenv()

_CONFIG = None


def get_config() -> dict:
    global _CONFIG
    if _CONFIG is None:
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path) as f:
            _CONFIG = yaml.safe_load(f)
    return _CONFIG


def get_secret(key: str, default: str = "") -> str:
    return os.getenv(key, default)
