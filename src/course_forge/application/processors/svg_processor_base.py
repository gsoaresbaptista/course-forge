import re
import os
import hashlib
import threading
import xml.etree.ElementTree as ET
from abc import abstractmethod
from typing import Any, Callable

from course_forge.domain.entities import ContentNode

from .base import Processor


class SVGProcessorBase(Processor):
    """Base class for processors that generate SVG graphics with common metadata extraction."""

    _XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
    _MATPLOTLIB_RENDER_LOCK = threading.RLock()

    def build_svg_id_prefix(
        self,
        processor_name: str,
        content: str,
        node: ContentNode | None = None,
    ) -> str:
        """Build a stable, processor-scoped prefix for inline SVG ids."""
        hash_input = f"{processor_name}:{content}"
        if node and node.src_path:
            hash_input = f"{processor_name}:{node.src_path}:{content}"
        content_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:12]
        return f"svg-{processor_name}-{content_hash}"

    def get_cached_svg_or_render(
        self,
        processor_name: str,
        code_to_hash: str,
        render_func: Callable,
        *args,
        node: ContentNode | None = None,
        **kwargs,
    ) -> bytes:
        """Cache mechanism to avoid recompiling heavy SVG graphics if the markdown block hasn't changed.

        Args:
            processor_name: A unique name for the processor (e.g. 'schemdraw', 'graphviz')
            code_to_hash: The full code block to compute the hash from (helps distinguish configs).
            render_func: Callable that generates the SVG bytes.
            node: The content node being processed (used to isolate cache per file).
            *args, **kwargs: Passed to render_func.
        """
        cache_dir = os.path.join(os.getcwd(), ".course_forge_cache", processor_name)
        os.makedirs(cache_dir, exist_ok=True)

        # Scope the hash by processor and source path to make cross-processor
        # cache collisions impossible even when block contents are identical.
        hash_input = f"{processor_name}:{code_to_hash}"
        if node and node.src_path:
            hash_input = f"{processor_name}:{node.src_path}:{code_to_hash}"

        content_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
        cache_file = os.path.join(cache_dir, f"{content_hash}.svg")

        if os.path.exists(cache_file):
            try:
                with open(cache_file, "rb") as f:
                    return f.read()
            except IOError:
                pass

        svg_data = render_func(*args, **kwargs)

        try:
            with open(cache_file, "wb") as f:
                f.write(svg_data)
        except IOError:
            pass

        return svg_data

    @staticmethod
    def create_pattern(block_type: str, _unused: str = "") -> re.Pattern:
        """Create a regex pattern for SVG code blocks with common attributes.

        Args:
            block_type: The code block type (e.g., "ast.plot", "digital-circuit.plot")
            _unused: Legacy parameter, no longer used.

        Returns:
            Compiled regex pattern with width, height, centered, and sketch groups
        """
        pattern_str = (
            r"(?P<indent>[ \t]*)"
            rf"```{re.escape(block_type)}"
            r"(?:\s+(?:width=(?P<width>\d+)|height=(?P<height>\d+)|(?P<centered>centered)|(?P<sketch>sketch)|(?P<leftmost>leftmost)|(?P<rightmost>rightmost)))*"
            r"[ \t]*\r?\n(?P<content>.*?)```"
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
                - leftmost: Boolean indicating leftmost-derivation highlight
                - rightmost: Boolean indicating rightmost-derivation highlight
        """
        return {
            "width": match.group("width"),
            "height": match.group("height"),
            "centered": match.group("centered") is not None,
            "sketch": match.group("sketch") is not None,
            "leftmost": match.group("leftmost") is not None,
            "rightmost": match.group("rightmost") is not None,
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
        id_prefix: str | None = None,
    ) -> str:
        """Generate inline SVG HTML with proper classes and attributes.

        Args:
            svg_bytes: Raw SVG data as bytes
            width: Optional width override
            height: Optional height override
            centered: Whether to center the SVG
            sketch: Whether to apply rough.js sketch effect
            css_class: CSS class to apply to the SVG element
            id_prefix: Optional prefix to namespace internal SVG ids

        Returns:
            HTML string with inline SVG wrapped in appropriate div
        """
        root = ET.fromstring(svg_bytes)

        if id_prefix:
            self._prefix_svg_ids(root, id_prefix)

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
        svg_html = svg_html.replace("\n", "").replace("\r", "")

        wrapper_class = "centered" if centered else ""

        return f'<div class="{wrapper_class}">{svg_html}</div>'

    def _prefix_svg_ids(self, root: ET.Element, prefix: str) -> None:
        """Namespace SVG ids and references so multiple inline SVGs do not collide."""
        id_map: dict[str, str] = {}

        for element in root.iter():
            element_id = element.get("id")
            if element_id:
                namespaced_id = f"{prefix}-{element_id}"
                id_map[element_id] = namespaced_id
                element.set("id", namespaced_id)

        if not id_map:
            return

        ref_attrs = {
            "href",
            self._XLINK_HREF,
            "clip-path",
            "filter",
            "mask",
            "fill",
            "stroke",
            "marker-start",
            "marker-mid",
            "marker-end",
            "begin",
            "end",
        }

        for element in root.iter():
            for attr_name, attr_value in list(element.attrib.items()):
                if attr_name in ref_attrs or attr_name == "style":
                    updated_value = self._replace_svg_refs(attr_value, id_map)
                    if updated_value != attr_value:
                        element.set(attr_name, updated_value)

    def _replace_svg_refs(self, value: str, id_map: dict[str, str]) -> str:
        """Rewrite internal SVG references to use namespaced ids."""

        def replace_url_ref(match: re.Match) -> str:
            ref_id = match.group(1)
            return f"url(#{id_map.get(ref_id, ref_id)})"

        def replace_hash_ref(match: re.Match) -> str:
            prefix, ref_id = match.groups()
            return f"{prefix}#{id_map.get(ref_id, ref_id)}"

        value = re.sub(r"url\(#([^)]+)\)", replace_url_ref, value)
        value = re.sub(
            r'((?:^|[\s;(,:=\'"]))#([A-Za-z_][\w.:-]*)', replace_hash_ref, value
        )
        return value

    @abstractmethod
    def execute(self, node: ContentNode, content: str) -> str:
        """Process content and generate inline SVG graphics."""
        ...
