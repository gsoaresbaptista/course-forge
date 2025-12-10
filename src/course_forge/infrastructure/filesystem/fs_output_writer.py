import os

from course_forge.application.writers import OutputWriter
from course_forge.domain.entities import ContentNode


class FileSystemOutputWriter(OutputWriter):
    def __init__(self, root_path: str) -> None:
        super().__init__()
        self._root_path = root_path

    def write(self, node: ContentNode, text: str) -> None:
        out_dir = os.path.join(self._root_path, *node.slugs_path)
        os.makedirs(out_dir, exist_ok=True)
        html_path = os.path.join(out_dir, node.slug + ".html")
        html = f"<html><head><title>BATATA</title></head><body>{text}</body></html>"

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
