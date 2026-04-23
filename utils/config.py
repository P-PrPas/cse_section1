import json
import sys
from pathlib import Path

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "camera_index": 0,
    "camera_name": "",
    "output_dir": "output",
    "scraper_timeout_sec": 15
}


def get_app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def get_config_path() -> Path:
    return get_app_root() / CONFIG_FILE

def load_config():
    config_path = get_config_path()
    if not config_path.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            merged = {**DEFAULT_CONFIG, **loaded}
            return merged
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(config):
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
