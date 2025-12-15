from abc import ABC, abstractmethod


class MarkdownRenderer(ABC):
    @abstractmethod
    def render(self, text: str, chapter: int | None = None) -> str:
        pass
