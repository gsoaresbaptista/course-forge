import os
from pathlib import Path

from course_forge.domain.entities.content_node import ContentNode
from course_forge.domain.entities.content_tree import ContentTree
from course_forge.domain.repositories import (
    ContentTreeRepository,
)


class FileSystemContentTreeRepository(ContentTreeRepository):
    def load(self, path: str) -> ContentTree:
        root = self._build_node(path, parent_slugs=[], is_root=True)
        return ContentTree(root)

    def _build_node(
        self, path: str, parent_slugs: list[str], is_root: bool = False
    ) -> ContentNode:
        slug = Path(path).stem

        node = ContentNode(
            path=path,
            slug=slug,
            is_file=os.path.isfile(path),
            slugs_path=parent_slugs,
        )

        if node.is_dir:
            for entry in sorted(os.listdir(path)):
                full = os.path.join(path, entry)
                child_parent_slugs = parent_slugs if is_root else [*parent_slugs, slug]
                child = self._build_node(full, child_parent_slugs, is_root=False)
                node.add_child(child)

        return node
