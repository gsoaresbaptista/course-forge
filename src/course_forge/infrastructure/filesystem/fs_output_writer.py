import os
from typing import Any

from course_forge.application.writers import OutputWriter
from course_forge.domain.entities import ContentNode


class FileSystemOutputWriter(OutputWriter):
    def __init__(self, root_path: str) -> None:
        super().__init__()
        self._root_path = root_path

    def write(self, node: ContentNode, text: str, assets: list[dict[str, Any]]) -> None:
        for i, asset in enumerate(assets):
            out_dir = os.path.join(self._root_path, *node.slugs_path)
            os.makedirs(out_dir, exist_ok=True)

            filename = f"static/{node.slug}_{i}.{asset['extension']}"
            os.makedirs(os.path.join(out_dir, 'static'), exist_ok=True)
            file_path = os.path.join(out_dir, filename)

            with open(file_path, "wb") as f:
                f.write(asset["data"])

            token = f"{{{{asset:{asset['type']}:{i}}}}}"
            # print(text)
            text = text.replace(token, f'<img src="{file_path}" alt="digital circuit">')
            # print(text)
            # exit(0)

        out_path = os.path.join(self._root_path, *node.slugs_path)
        os.makedirs(out_path, exist_ok=True)
        file_path = os.path.join(out_path, node.slug + ".html")

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(text)

