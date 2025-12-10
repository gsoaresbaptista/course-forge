from __future__ import annotations


class ContentNode:
    def __init__(
        self,
        src_path: str,
        name: str,
        is_file: bool = False,
        children: list[ContentNode] | None = None,
        slugs_path: list[str] | None = None,
    ) -> None:
        self._src_path: str = src_path
        self._is_file = is_file
        self.name = name
        self.children = children or []
        self._slugs_path: list[str] = [] if slugs_path is None else slugs_path

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
