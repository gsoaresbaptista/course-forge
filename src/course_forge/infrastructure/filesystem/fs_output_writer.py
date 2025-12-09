import os
from typing import Any

from css_html_js_minify import html_minify

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
            token = f"{{{{asset:{asset['type']}:{i}}}}}"

            if asset["extension"] == "svg":
                svg = asset["data"].decode("utf-8")
                text = text.replace(token, f'<figure class="asset-svg">{svg}</figure>')
                continue

            static_dir = os.path.join(out_dir, "static")
            os.makedirs(static_dir, exist_ok=True)

            filename = f"{node.slug}_{i}.{asset['extension']}"
            file_path = os.path.join(static_dir, filename)

            with open(file_path, "wb") as f:
                f.write(asset["data"])

            public_path = f"static/{filename}"

            text = text.replace(
                token, f'<figure class="asset-img"><img src="{public_path}" /></figure>'
            )

        html_path = os.path.join(out_dir, node.slug + ".html")
        minified = html_minify(text)

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(minified)
