import re
import xml.etree.ElementTree as ET
from abc import abstractmethod
from typing import Any

from course_forge.domain.entities import ContentNode

from .base import Processor


class SVGProcessorBase(Processor):
    """Base class for processors that generate SVG graphics with common metadata extraction."""

    @staticmethod
    def create_pattern(block_type: str, content_pattern: str) -> re.Pattern:
        """Create a regex pattern for SVG code blocks with common attributes.

        Args:
            block_type: The code block type (e.g., "ast.plot", "digital-circuit.plot")
            content_pattern: The regex pattern for the block's specific content

        Returns:
            Compiled regex pattern with width, height, centered, and sketch groups
        """
        pattern_str = (
            r"(?P<indent>[ \t]*)"
            rf"```{re.escape(block_type)}"
            r"(?:\s+(?:width=(?P<width>\d+)|height=(?P<height>\d+)|(?P<centered>centered)|(?P<sketch>sketch)))*"
            rf"\s+{content_pattern}```"
        )
        return re.compile(pattern_str, re.DOTALL)

    @staticmethod
    def parse_svg_attributes(match: re.Match) -> dict[str, Any]:
        """Parse common SVG attributes (width, height, centered, sketch) from regex match.

        Args:
            match: Regex match object containing width, height, centered, and sketch groups

        Returns:
            Dictionary with parsed attributes:
                - width: Width value as string or None
                - height: Height value as string or None
                - centered: Boolean indicating if centered attribute is present
                - sketch: Boolean indicating if sketch attribute is present
        """
        return {
            "width": match.group("width"),
            "height": match.group("height"),
            "centered": match.group("centered") is not None,
            "sketch": match.group("sketch") is not None,
        }

    def extract_svg_metadata(self, svg_bytes: bytes) -> dict[str, any]:
        """Extract width, height, viewBox, and center coordinates from SVG.

        Args:
            svg_bytes: Raw SVG data as bytes

        Returns:
            Dictionary containing:
                - width: Original width attribute (if present)
                - height: Original height attribute (if present)
                - viewBox: ViewBox attribute (if present)
                - center_x: Calculated center X coordinate
                - center_y: Calculated center Y coordinate
        """
        root = ET.fromstring(svg_bytes)

        metadata = {
            "width": root.get("width"),
            "height": root.get("height"),
            "viewBox": root.get("viewBox"),
            "center_x": 0.0,
            "center_y": 0.0,
        }

        if metadata["viewBox"]:
            center_x, center_y = self.calculate_center(metadata["viewBox"])
            metadata["center_x"] = center_x
            metadata["center_y"] = center_y

        return metadata

    def calculate_center(self, viewbox: str) -> tuple[float, float]:
        """Calculate center coordinates from SVG viewBox attribute.

        Args:
            viewbox: ViewBox string in format "min-x min-y width height"

        Returns:
            Tuple of (center_x, center_y)
        """
        parts = viewbox.split()
        if len(parts) == 4:
            min_x, min_y, width, height = map(float, parts)
            center_x = min_x + width / 2
            center_y = min_y + height / 2
            return center_x, center_y
        return 0.0, 0.0

    def generate_inline_svg(
        self,
        svg_bytes: bytes,
        width: str | None,
        height: str | None,
        centered: bool,
        sketch: bool = False,
        css_class: str = "svg-graph",
    ) -> str:
        """Generate inline SVG HTML with proper classes and attributes.

        Args:
            svg_bytes: Raw SVG data as bytes
            width: Optional width override
            height: Optional height override
            centered: Whether to center the SVG
            sketch: Whether to apply rough.js sketch effect
            css_class: CSS class to apply to the SVG element

        Returns:
            HTML string with inline SVG wrapped in appropriate div
        """
        root = ET.fromstring(svg_bytes)
        root.set("class", css_class)

        # Add data-sketch attribute for rough.js processing
        if sketch:
            root.set("data-sketch", "true")

        # Apply width/height overrides or remove default dimensions
        if width is not None:
            root.set("width", str(width))
        elif "width" in root.attrib:
            del root.attrib["width"]

        if height is not None:
            root.set("height", str(height))
        elif "height" in root.attrib:
            del root.attrib["height"]

        svg_html = ET.tostring(root, encoding="unicode")
        
        # Flatten the SVG to a single line to prevent Markdown parsers 
        # from interpreting indented lines as code blocks
        svg_html = svg_html.replace('\n', '').replace('\r', '')
        
        wrapper_class = "centered" if centered else ""

        return f'<div class="{wrapper_class}">{svg_html}</div>'

    @abstractmethod
    def execute(self, node: ContentNode, content: str) -> str:
        """Process content and generate inline SVG graphics."""
        ...
