from typing import Any

from course_forge.application.loaders import MarkdownLoader


class FileSystemMarkdownLoader(MarkdownLoader):
    def load(self, path: str) -> dict[str, Any]:
        with open(path, "r") as file:
            content = file.read()

        metadata = {}
        if content.startswith("---\n"):
            try:
                _, frontmatter, content = content.split("---", 2)
                for line in frontmatter.splitlines():
                    if ":" in line:
                        key, value = line.split(":", 1)
                        metadata[key.strip()] = value.strip()
                content = content.lstrip()
            except ValueError:
                pass  # Malformed frontmatter

        return {"content": content, "metadata": metadata}
