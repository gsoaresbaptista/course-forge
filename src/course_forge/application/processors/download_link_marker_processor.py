import os
import re

from course_forge.domain.entities import ContentNode

from .base import Processor


class DownloadLinkMarkerProcessor(Processor):
    """Pre-processor that adds {.download-link} marker to download links.

    Detects links to common binary file extensions and adds the marker
    so the post-processor can convert them to proper HTML classes.
    """

    DOWNLOAD_EXTENSIONS = {
        ".zip",
        ".rar",
        ".tar",
        ".gz",
        ".7z",
        ".pdf",
        ".exe",
        ".dmg",
        ".bin",
        ".deb",
        ".rpm",
        ".appimage",
    }

    LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    def execute(self, node: ContentNode, content: str) -> str:
        def add_marker(match: re.Match) -> str:
            text = match.group(1)
            href = match.group(2)

            # Check if href ends with a download extension
            ext = os.path.splitext(href)[1].lower()
            if ext in self.DOWNLOAD_EXTENSIONS:
                return f"[{text}]({href}){{.download-link}}"

            return match.group(0)

        return self.LINK_PATTERN.sub(add_marker, content)
