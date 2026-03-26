import io
import re
import matplotlib
import matplotlib.pyplot as plt
from typing import Any

from course_forge.domain.entities import ContentNode
from .svg_processor_base import SVGProcessorBase

# Force non-interactive backend
matplotlib.use('Agg')

# Silence matplotlib show and other interactive calls
plt.show = lambda *args, **kwargs: None

class MatplotlibProcessor(SVGProcessorBase):
    """Processor for matplotlib code blocks."""

    matplotlib_pattern = SVGProcessorBase.create_pattern("matplotlib.plot", "")
    matplot_pattern = SVGProcessorBase.create_pattern("matplot.plot", "")

    def execute(self, node: ContentNode, content: str) -> str:
        content = self._process_pattern(node, content, self.matplotlib_pattern)
        content = self._process_pattern(node, content, self.matplot_pattern)
        return content

    def _process_pattern(self, node: ContentNode, content: str, pattern: re.Pattern) -> str:
        matches = list(pattern.finditer(content))

        for match in matches:
            code = match.group("content").strip()
            attrs = self.parse_svg_attributes(match)

            try:
                svg_data = self._render_plot(code)
                svg_html = self.generate_inline_svg(
                    svg_data,
                    attrs["width"],
                    attrs["height"],
                    attrs["centered"],
                    attrs["sketch"],
                    css_class="svg-graph matplotlib-plot-img",
                )

                # Wrap in no-break div for print layout
                svg_html = f'<div class="no-break">{svg_html}</div>'

                content = content.replace(match.group(0), svg_html)
            except Exception as e:
                error_msg = f'<div class="error">Matplotlib error: {str(e)}</div>'
                content = content.replace(match.group(0), error_msg)

        return content

    def _render_plot(self, code: str) -> bytes:
        """Execute matplotlib code and return SVG bytes."""
        # Configure matplotlib for SVG output
        plt.rcParams['savefig.transparent'] = True
        plt.rcParams['svg.fonttype'] = 'none'
        
        # Clear any existing plots to prevent carry-over
        plt.close('all')
        plt.clf()

        # Setup context with common imports
        context = {
            "plt": plt,
            "matplotlib": matplotlib,
        }
        
        # Try to import numpy as it's very common
        try:
            import numpy as np
            context["np"] = np
        except ImportError:
            pass

        # Execute the code block
        exec(code, context)

        # Capture the current figure
        buf = io.BytesIO()
        plt.savefig(buf, format='svg', bbox_inches='tight')
        plt.close('all')
        
        svg_data = buf.getvalue()
        
        return self._sanitize_svg(svg_data)

    def _sanitize_svg(self, svg_bytes: bytes) -> bytes:
        """Prepare SVG for inline embedding."""
        svg_str = svg_bytes.decode('utf-8')
        
        # Strip all newlines to prevent Markdown parser from interpreting indented lines as code blocks
        svg_str = svg_str.replace('\n', '').replace('\r', '')
        
        return svg_str.encode('utf-8')
