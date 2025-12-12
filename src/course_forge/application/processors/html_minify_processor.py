from css_html_js_minify import html_minify  # type: ignore

from course_forge.domain.entities import ContentNode

from .base import Processor


class HTMLMinifyProcessor(Processor):
    def execute(self, node: ContentNode, content: str) -> str:
        minified = html_minify(content)
        return minified
