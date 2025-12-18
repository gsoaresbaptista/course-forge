from __future__ import annotations

import re
import unicodedata
from typing import Any


class ContentNode:
    def __init__(
        self,
        src_path: str,
        name: str,
        file_extension: str,
        is_file: bool = False,
        children: list[ContentNode] | None = None,
        parent: ContentNode | None = None,
        metadata: dict | None = None,
    ) -> None:
        self._src_path: str = src_path
        self._is_file = is_file
        self.name = name
        self.children = children or []
        self._number_of_attachments: int = 0
        self._attachments: dict[int, Any] = {}
        self._file_extension: str = file_extension
        self._parent: ContentNode | None = parent
        self._metadata: dict = metadata or {}
        self._discovery_path: str | None = None
        self._alias_to: ContentNode | None = None

    @property
    def file_extension(self) -> str:
        return self._file_extension

    @property
    def number_of_attachments(self) -> int:
        return self._number_of_attachments

    @property
    def attachments(self) -> dict[int, Any]:
        return self._attachments

    @property
    def src_path(self) -> str:
        return self._src_path

    @src_path.setter
    def src_path(self, path: str) -> None:
        self._src_path = path

    @property
    def slug(self) -> str:
        """Generate URL-friendly slug from name."""
        text = self.name
        text = unicodedata.normalize("NFKD", text)
        text = text.encode("ascii", "ignore").decode("ascii")
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[-\s]+", "-", text)
        text = text.strip("-")
        return text if text else self.name

    @property
    def slugs_path(self) -> list[str]:
        """Compute path from parent chain dynamically using slugs."""
        path = []
        node = self._parent
        while node is not None and node._parent is not None:
            path.insert(0, node.slug)
            node = node._parent
        return path

    @property
    def is_file(self) -> bool:
        return self._is_file

    @property
    def is_dir(self) -> bool:
        return not self._is_file

    @property
    def parent(self) -> ContentNode | None:
        return self._parent

    @property
    def metadata(self) -> dict:
        return self._metadata

    @metadata.setter
    def metadata(self, value: dict) -> None:
        self._metadata = value

    @property
    def siblings(self) -> list[ContentNode]:
        if self._parent is None:
            return []
        return [
            c for c in self._parent.children if c.is_file and c.file_extension == ".md"
        ]

    def add_child(self, child: ContentNode) -> None:
        child._parent = self
        self.children.append(child)

    def __str__(self, level: int = 0) -> str:
        base = f"{'    ' * level}<{'File' if self.is_file else 'Directory'} path={self.name}>"

        for entry in self.children:
            base += f"\n{entry.__str__(level + 1)}"

        return base

    @property
    def discovery_path(self) -> str | None:
        return self._discovery_path

    @discovery_path.setter
    def discovery_path(self, path: str) -> None:
        self._discovery_path = path

    @property
    def alias_to(self) -> ContentNode | None:
        return self._alias_to

    @alias_to.setter
    def alias_to(self, node: ContentNode) -> None:
        self._alias_to = node

    def attach(self, data: Any) -> int:
        self._attachments[self._number_of_attachments] = data
        self._number_of_attachments += 1
        return self._number_of_attachments - 1
