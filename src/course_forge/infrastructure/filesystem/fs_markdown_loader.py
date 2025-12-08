from typing import Any


class FileSystemMarkdownLoader:
    def load(self, path: str) -> dict[str, Any]:
        with open(path, "r") as file:
            data = file.read()
        return {"content": data, "metadata": {}}
