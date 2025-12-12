from abc import ABC, abstractmethod
from typing import Any


class MarkdownLoader(ABC):
    @abstractmethod
    def load(self, path: str) -> dict[str, Any]:
        raise NotImplementedError
