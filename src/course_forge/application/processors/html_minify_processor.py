from typing import Any

from css_html_js_minify import html_minify  # type: ignore

from course_forge.domain.entities import ContentNode

from .base import Processor


class HTMLMinifyProcessor(Processor):
    def execute(self, node: ContentNode, markdown: dict[str, Any]) -> dict[str, Any]:
        content = markdown.get("content", "")
        markdown["content"] = html_minify(content)
        return markdown
