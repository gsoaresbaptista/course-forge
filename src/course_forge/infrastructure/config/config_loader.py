import os

import yaml


class ConfigLoader:
    def load(self, path: str) -> dict:
        config = {"site_name": "Course Forge", "courses_title": "Disciplinas"}

        if not os.path.exists(path):
            return config

        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if loaded and isinstance(loaded, dict):
                    config.update(loaded)
        except Exception as e:
            print(f"Error loading config {path}: {e}")

        return config
