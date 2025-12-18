import os
from pathlib import Path

from course_forge.domain.entities.content_node import ContentNode
from course_forge.domain.entities.content_tree import ContentTree
from course_forge.domain.repositories import ContentTreeRepository
from course_forge.infrastructure.config.config_loader import ConfigLoader


class FileSystemContentTreeRepository(ContentTreeRepository):
    def __init__(self) -> None:
        self.config_loader = ConfigLoader()

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
            discovery_path = path

            # Check for config.yaml to see if this is a symbolic module
            config_path = os.path.join(path, "config.yaml")
            if os.path.exists(config_path):
                config = self.config_loader.load(config_path)
                if config and config.get("source"):
                    source_rel = config.get("source")
                    discovery_path = os.path.normpath(os.path.join(path, source_rel))

            node.discovery_path = os.path.abspath(discovery_path)

            for entry in sorted(os.listdir(discovery_path)):
                if entry == "config.yaml":
                    continue
                full = os.path.join(discovery_path, entry)
                child = self._build_node(full, is_root=False)
                node.add_child(child)

        return node
