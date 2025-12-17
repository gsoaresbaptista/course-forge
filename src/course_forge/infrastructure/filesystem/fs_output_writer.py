import os
import re
import shutil
from pathlib import Path

import csscompressor
import jsmin

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

        for attach in node.attachments.values():
            node_attachments = os.path.join(out_dir, "static")
            os.makedirs(node_attachments, exist_ok=True)
            attach_path = os.path.join(node_attachments, attach["name"])

            ext = Path(attach["name"]).suffix.lower()
            if ext in [".css", ".js", ".svg"]:
                try:
                    content = attach["data"].decode("utf-8")
                    minified = self._minify_content(content, ext)
                    with open(attach_path, "w", encoding="utf-8") as file:
                        file.write(minified)
                except Exception as e:
                    print(
                        f"Warning: Failed to minify attachment {attach['name']}: {e}. Writing original."
                    )
                    with open(attach_path, "wb") as file:
                        file.write(attach["data"])
            else:
                with open(attach_path, "wb") as file:
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
                shutil.copytree(
                    src_path,
                    dst_path,
                    dirs_exist_ok=True,
                    copy_function=self._smart_copy,
                )
            else:
                self._smart_copy(src_path, dst_path)

        # Copy dark-favicon.svg as fallback favicon.svg at root
        favicon_src = os.path.join(self._root_path, "img", "dark-favicon.svg")
        favicon_dst = os.path.join(self._root_path, "favicon.svg")
        if os.path.exists(favicon_src) and not os.path.exists(favicon_dst):
            shutil.copy2(favicon_src, favicon_dst)

    def _smart_copy(self, src: str, dst: str, **kwargs) -> None:
        ext = Path(src).suffix.lower()
        if ext in [".css", ".js", ".svg"]:
            self._minify_and_copy(src, dst, ext)
        else:
            shutil.copy2(src, dst)

    def _minify_and_copy(self, src_path: str, dst_path: str, ext: str) -> None:
        try:
            with open(src_path, "r", encoding="utf-8") as f:
                content = f.read()

            minified = self._minify_content(content, ext)

            with open(dst_path, "w", encoding="utf-8") as f:
                f.write(minified)
        except Exception as e:
            print(f"Warning: Failed to minify {src_path}: {e}. Copying original.")
            shutil.copy2(src_path, dst_path)

    def _minify_content(self, content: str, ext: str) -> str:
        if ext == ".css":
            return csscompressor.compress(content)
        elif ext == ".js":
            return jsmin.jsmin(content, quote_chars="'\"`")
        elif ext == ".svg":
            # Simple SVG minification: remove newlines and extra spaces
            minified = re.sub(r">\s+<", "><", content)
            minified = re.sub(r"\s+", " ", minified).strip()
            return minified
        return content

    def copy_file(self, node: ContentNode) -> None:
        dst_foler = os.path.join(self._root_path, *node.slugs_path)
        dst_path = os.path.join(dst_foler, node.slug + node.file_extension)
        os.makedirs(dst_foler, exist_ok=True)
        shutil.copy2(node.src_path, dst_path)

    def write_contents(self, node: ContentNode, text: str) -> None:
        """Write contents.html for a course directory."""
        # Use full path including parents (slugs_path) + current node name
        out_dir = os.path.join(self._root_path, *node.slugs_path, node.slug)
        os.makedirs(out_dir, exist_ok=True)
        html_path = os.path.join(out_dir, "contents.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(text)

    def write_index(self, text: str) -> None:
        """Write root index.html."""
        html_path = os.path.join(self._root_path, "index.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(text)
