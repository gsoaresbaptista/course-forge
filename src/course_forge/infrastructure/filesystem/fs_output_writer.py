import hashlib
import json
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

    def get_cache_dir(self) -> Path:
        """Returns the global cache directory for the application."""
        # Linux: ~/.local/share/course-forge/cache
        base_dir = Path(os.path.expanduser("~/.local/share/course-forge"))
        cache_dir = base_dir / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def get_checksum_file(self, source_path: str) -> Path:
        """Returns the path to the checksum file for a specific project source."""
        # Create a unique hash for the project path to avoid collisions
        project_hash = hashlib.md5(str(Path(source_path).resolve()).encode()).hexdigest()
        return self.get_cache_dir() / f"{project_hash}.json"

    def load_checksums(self, source_path: str) -> dict[str, str]:
        """Loads checksums for the given project source path."""
        checksum_file = self.get_checksum_file(source_path)
        if checksum_file.exists():
            try:
                with open(checksum_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load checksums from {checksum_file}: {e}")
        return {}

    def save_checksums(self, source_path: str, checksums: dict[str, str]) -> None:
        """Saves checksums for the given project source path."""
        checksum_file = self.get_checksum_file(source_path)
        try:
            with open(checksum_file, "w", encoding="utf-8") as f:
                json.dump(checksums, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save checksums to {checksum_file}: {e}")

    def exists(self, node: ContentNode) -> bool:
        """Check if the output file for a given node already exists."""
        if node.is_file:
            path = self._get_node_output_path(node)
            return os.path.exists(path)
        return False

    def _get_node_output_path(self, node: ContentNode) -> str:
        dst_folder = os.path.join(self._root_path, *node.slugs_path)
        if node.file_extension == ".md":
            # For markdown, it's usually slug.html, but let's be consistent with write()
            out_dir = os.path.join(self._root_path, *node.slugs_path)
            return os.path.join(out_dir, node.slug + ".html")
        else:
            return os.path.join(dst_folder, node.slug + node.file_extension)

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
