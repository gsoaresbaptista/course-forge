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
        html_path = os.path.join(out_dir, node.name + ".html")
        html = f"<html><head><title>Temp. Template</title></head><body>{text}</body></html>"

        for attach in node.attachments.values():
            node_attachments = os.path.join(out_dir, "static")
            os.makedirs(node_attachments, exist_ok=True)
            with open(os.path.join(node_attachments, attach["name"]), "wb") as file:
                file.write(attach["data"])

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
