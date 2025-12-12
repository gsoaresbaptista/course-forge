from abc import ABC, abstractmethod

from course_forge.domain.entities import ContentNode


class HTMLTemplateRenderer(ABC):
    def __init__(self, template_dir: str | None = None) -> None:
        super().__init__()

        if template_dir is None:
            import os

            self.template_dir = os.path.join(
                os.path.dirname(__file__), "..", "..", "templates"
            )
        else:
            self.template_dir = template_dir

    @abstractmethod
    def render(self, content: str, node: ContentNode) -> str:
        pass
