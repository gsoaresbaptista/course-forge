from abc import ABC, abstractmethod
from typing import Any

from course_forge.domain.entities import ContentNode


class OutputWriter(ABC):
    @abstractmethod
    def write(self, node: ContentNode, text: str, assets: list[dict[str, Any]]) -> None:
        pass
