from __future__ import annotations

from typing import Any


class ContentNode:
    def __init__(
        self,
        src_path: str,
        name: str,
        file_extension: str,
        is_file: bool = False,
        children: list[ContentNode] | None = None,
        slugs_path: list[str] | None = None,
    ) -> None:
        self._src_path: str = src_path
        self._is_file = is_file
        self.name = name
        self.children = children or []
        self._slugs_path: list[str] = [] if slugs_path is None else slugs_path
        self._number_of_attachments: int = 0
        self._attachments: dict[int, Any] = {}
        self._file_extension: str = file_extension

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
    def slugs_path(self) -> list[str]:
        return self._slugs_path

    @property
    def is_file(self) -> bool:
        return self._is_file

    @property
    def is_dir(self) -> bool:
        return not self._is_file

    def add_child(self, child: ContentNode) -> None:
        self.children.append(child)

    def __str__(self, level: int = 0) -> str:
        base = f"{'    ' * level}<{'File' if self.is_file else 'Directory'} path={self.name}>"

        for entry in self.children:
            base += f"\n{entry.__str__(level + 1)}"

        return base

    def attach(self, data: Any) -> int:
        self._attachments[self._number_of_attachments] = data
        self._number_of_attachments += 1
        return self._number_of_attachments - 1
