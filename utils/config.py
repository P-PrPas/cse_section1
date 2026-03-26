import json
import os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "camera_index": 0,
    "output_dir": "output",
    "scraper_timeout_sec": 15
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
