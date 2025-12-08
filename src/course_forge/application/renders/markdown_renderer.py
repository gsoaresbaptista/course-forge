from abc import ABC, abstractmethod


class MarkdownRenderer(ABC):
    @abstractmethod
    def render(self, text: str) -> str:
        pass
