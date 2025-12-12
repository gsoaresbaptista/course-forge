from typing import Any

from course_forge.application.loaders import MarkdownLoader


class FileSystemMarkdownLoader(MarkdownLoader):
    def load(self, path: str) -> dict[str, Any]:
        with open(path, "r") as file:
            data = file.read()
        return {"content": data, "metadata": {}}
