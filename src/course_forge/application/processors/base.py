from abc import ABC, abstractmethod
from typing import Any

from course_forge.domain.entities import ContentNode


class Processor(ABC):
    @abstractmethod
    def execute(
        self, node: ContentNode, markdown: dict[str, Any]
    ) -> dict[str, Any]: ...
