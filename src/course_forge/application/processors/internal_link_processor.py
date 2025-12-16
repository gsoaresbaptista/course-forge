import re

from course_forge.domain.entities import ContentNode

from .base import Processor


class InternalLinkProcessor(Processor):
    """Convert internal markdown links to HTML links.

    Supports:
    - [text](page) -> [text](page.html)
    - [text](page.md) -> [text](page.html)
    - [text](../other/page.md) -> [text](../other/page.html)
    - [text](/course/module/page) -> [text](/course/module/page.html)
    """

    LINK_PATTERN = re.compile(
        r"\[([^\]]+)\]\(([^)]+)\)",
        re.MULTILINE,
    )

    def execute(self, node: ContentNode, content: str) -> str:
        def replace_link(match: re.Match) -> str:
            text = match.group(1)
            href = match.group(2)

            if self._is_external_link(href):
                return match.group(0)

            if href.startswith("#"):
                return match.group(0)

            if href.endswith(".md"):
                href = href[:-3] + ".html"
            elif not self._has_extension(href) and not href.endswith("/"):
                href = href + ".html"

            return f"[{text}]({href})"

        return self.LINK_PATTERN.sub(replace_link, content)

    def _is_external_link(self, href: str) -> bool:
        return href.startswith(("http://", "https://", "mailto:", "tel:"))

    def _has_extension(self, href: str) -> bool:
        path = href.split("#")[0].split("?")[0]
        last_part = path.split("/")[-1]
        return "." in last_part
