from abc import ABC, abstractmethod

from course_forge.domain.entities import ContentNode


class HTMLTemplateRenderer(ABC):
    @abstractmethod
    def render(self, content: str, node: ContentNode) -> str:
        pass
