import os
from typing import Any

from css_html_js_minify import html_minify  # type: ignore

from course_forge.application.services import AssetHandler
from course_forge.application.writers import OutputWriter
from course_forge.domain.entities import ContentNode


class FileSystemOutputWriter(OutputWriter):
    def __init__(self, root_path: str) -> None:
        super().__init__()
        self._root_path = root_path

    def write(self, node: ContentNode, text: str, assets: list[dict[str, Any]]) -> None:
        out_dir = os.path.join(self._root_path, *node.slugs_path)
        os.makedirs(out_dir, exist_ok=True)

        for i, asset in enumerate(assets):
            token, replacement = AssetHandler.process_asset(
                asset, node.slug, i, out_dir
            )
            text = text.replace(token, replacement)

        html_path = os.path.join(out_dir, node.slug + ".html")
        minified = html_minify(text)

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(minified)
