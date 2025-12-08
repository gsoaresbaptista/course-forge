from abc import ABC, abstractmethod

from course_forge.domain.entities.content_tree import ContentTree


class ContentTreeRepository(ABC):
    @abstractmethod
    def load(self, path: str) -> ContentTree:
        pass
