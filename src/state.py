import json
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "seen_ids.json"


def load_state():
    with open(STATE_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


def filter_new(items, seen_ids):
    return [item for item in items if item["id"] not in seen_ids]


def mark_seen(seen_ids, items):
    seen_ids.extend(item["id"] for item in items)
