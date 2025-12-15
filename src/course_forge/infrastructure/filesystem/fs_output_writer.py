import os
import shutil

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

        for attach in node.attachments.values():
            node_attachments = os.path.join(out_dir, "static")
            os.makedirs(node_attachments, exist_ok=True)
            with open(os.path.join(node_attachments, attach["name"]), "wb") as file:
                file.write(attach["data"])

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(text)

    def copy_assets(self, template_dir: str, filters: list[str] | None = None) -> None:
        if filters is None:
            filters = [".html", ".md"]

        for item in os.listdir(template_dir):
            if any([item.endswith(ext) for ext in filters]):
                continue

            src_path = os.path.join(template_dir, item)
            dst_path = os.path.join(self._root_path, item)

            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            else:
                shutil.copy2(src_path, dst_path)

    def copy_file(self, node: ContentNode) -> None:
        dst_foler = os.path.join(self._root_path, *node.slugs_path)
        dst_path = os.path.join(dst_foler, node.name + node.file_extension)
        os.makedirs(dst_foler, exist_ok=True)
        shutil.copy2(node.src_path, dst_path)

    def write_contents(self, node: ContentNode, text: str) -> None:
        """Write contents.html for a course directory."""
        # Use full path including parents (slugs_path) + current node name
        out_dir = os.path.join(self._root_path, *node.slugs_path, node.name)
        os.makedirs(out_dir, exist_ok=True)
        html_path = os.path.join(out_dir, "contents.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(text)

    def write_index(self, text: str) -> None:
        """Write root index.html."""
        html_path = os.path.join(self._root_path, "index.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(text)
