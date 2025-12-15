import os


class ConfigLoader:
    def load(self, path: str) -> dict:
        config = {"site_name": "Course Forge", "courses_title": "Disciplinas"}

        if not os.path.exists(path):
            return config

        try:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    if ":" in line:
                        key, value = line.split(":", 1)
                        config[key.strip()] = value.strip()
        except Exception:
            pass

        return config
