from abc import ABC, abstractmethod

from course_forge.domain.entities import ContentNode


class Processor(ABC):
    @abstractmethod
    def execute(self, node: ContentNode, content: str) -> str: ...
