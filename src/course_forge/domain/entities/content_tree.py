from .content_node import ContentNode


class ContentTree(ContentNode):
    def __init__(self, root: ContentNode):
        self._root = root

    @property
    def root(self) -> ContentNode:
        return self._root

    def __str__(self, level: int = 0) -> str:
        return self._root.__str__(level)
