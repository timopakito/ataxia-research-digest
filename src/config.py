from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "sources.yaml"


def load_sources():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)
