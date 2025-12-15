from abc import ABC, abstractmethod

from course_forge.domain.entities import ContentNode


class OutputWriter(ABC):
    @abstractmethod
    def write(self, node: ContentNode, text: str) -> None:
        pass

    @abstractmethod
    def copy_assets(self, template_dir: str, filters: list[str] | None = None) -> None:
        pass

    @abstractmethod
    def copy_file(self, node: ContentNode) -> None:
        pass

    @abstractmethod
    def write_contents(self, node: ContentNode, text: str) -> None:
        pass

    @abstractmethod
    def write_index(self, text: str) -> None:
        pass
