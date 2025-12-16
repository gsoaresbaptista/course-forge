import re

from course_forge.domain.entities import ContentNode

from .base import Processor


class DownloadLinkProcessor(Processor):
    """Convert download link markers to proper HTML classes.

    This is a POST-processor that runs after HTML generation.
    It finds links ending with {.download-link} marker and converts
    them to proper anchor tags with class="download-link".
    """

    # Match the marker pattern that was added to links
    MARKER_PATTERN = re.compile(
        r'<a\s+href="([^"]+)"[^>]*>([^<]+)</a>\{\.download-link\}',
        re.IGNORECASE,
    )

    def execute(self, node: ContentNode, content: str) -> str:
        def replace_with_class(match: re.Match) -> str:
            href = match.group(1)
            text = match.group(2)
            return f'<a href="{href}" class="download-link">{text}</a>'

        return self.MARKER_PATTERN.sub(replace_with_class, content)
