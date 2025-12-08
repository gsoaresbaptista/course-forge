from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MarkdownLoader(Protocol):
    def load(self, path: str) -> dict[str, Any]:
        raise NotImplementedError
