"""Application state and settings manager."""

import json
import os

SETTINGS_FILE = "app_settings.json"

DEFAULT_JSON = """{
  "id": 1,
  "name": "Alex Smith",
  "is_admin": true,
  "scores": [95.5, 88.0],
  "profile": {
    "bio": "Flutter Developer",
    "github": "alexsmith"
  }
}"""


class AppStateManager:

    @staticmethod
    def save_state(state: dict):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    @staticmethod
    def load_state() -> dict:
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to load settings: {e}")
        return {}