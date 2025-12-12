import minify_html  # type: ignore

from course_forge.domain.entities import ContentNode

from .base import Processor


class HTMLMinifyProcessor(Processor):
    def execute(self, node: ContentNode, content: str) -> str:
        minified = minify_html.minify(
            content,
            minify_js=True,
            minify_css=True,
            remove_processing_instructions=True,
        )
        return minified
