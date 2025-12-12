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

    def copy_assets(self, template_dir: str) -> None:
        css_src = os.path.join(template_dir, "css")
        js_src = os.path.join(template_dir, "js")
        css_dst = os.path.join(self._root_path, "css")
        js_dst = os.path.join(self._root_path, "js")

        if os.path.exists(css_src):
            shutil.copytree(css_src, css_dst, dirs_exist_ok=True)
        if os.path.exists(js_src):
            shutil.copytree(js_src, js_dst, dirs_exist_ok=True)
