import minify_html  # type: ignore

from course_forge.domain.entities import ContentNode

from .base import Processor

_MINIFY_STRATEGIES = [
    {"minify_js": True, "minify_css": True},
    {"minify_js": False, "minify_css": True},
    {"minify_js": False, "minify_css": False},
]


def _is_valid_minification(original: str, minified: str) -> bool:
    """Check that minification did not truncate the HTML structure."""
    if "</html>" in original and "</html>" not in minified:
        return False
    if "</body>" in original and "</body>" not in minified:
        return False
    if len(original) > 0 and len(minified) < len(original) * 0.01:
        return False
    return True


class HTMLMinifyProcessor(Processor):
    def execute(self, node: ContentNode, content: str) -> str:
        for strategy in _MINIFY_STRATEGIES:
            try:
                minified = minify_html.minify(
                    content,
                    remove_processing_instructions=True,
                    keep_closing_tags=True,
                    **strategy,
                )
                if _is_valid_minification(content, minified):
                    return minified
            except Exception:
                pass

        return content
