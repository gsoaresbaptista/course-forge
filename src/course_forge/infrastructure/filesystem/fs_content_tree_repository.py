import os
from pathlib import Path

from course_forge.domain.entities.content_node import ContentNode
from course_forge.domain.entities.content_tree import ContentTree
from course_forge.domain.repositories import ContentTreeRepository


class FileSystemContentTreeRepository(ContentTreeRepository):
    def load(self, path: str) -> ContentTree:
        root = self._build_node(path, is_root=True)
        return ContentTree(root)

    def _build_node(self, path: str, is_root: bool = False) -> ContentNode:
        slug = Path(path).stem

        node = ContentNode(
            src_path=path,
            name=slug,
            file_extension=Path(path).suffix,
            is_file=os.path.isfile(path),
        )

        if node.is_dir:
            for entry in sorted(os.listdir(path)):
                if entry == "config.yaml":
                    continue
                full = os.path.join(path, entry)
                child = self._build_node(full, is_root=False)
                node.add_child(child)

        return node
