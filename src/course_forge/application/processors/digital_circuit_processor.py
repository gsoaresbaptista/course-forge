from schemdraw.parsing.logic_parser import logicparse

from course_forge.domain.entities import ContentNode

from .svg_processor_base import SVGProcessorBase


class DigitalCircuitProcessor(SVGProcessorBase):
    pattern = SVGProcessorBase.create_pattern(
        "digital-circuit.plot", r"(?P<left>.+?)(?:=(?P<right>.+?))?"
    )

    def execute(self, node: ContentNode, content: str) -> str:
        matches = list(self.pattern.finditer(content))

        for match in matches:
            left = match.group("left").strip()
            right = match.group("right").strip() if match.group("right") else ""
            
            # If right-hand side logic is a python string literal (e.g. r'...' or "..."),
            # extract the inner string content to allow LaTeX usage without quotes being rendered.
            if right:
                # Check for r'...' or r"..."
                if (right.startswith("r'") and right.endswith("'")) or \
                   (right.startswith('r"') and right.endswith('"')):
                    right = right[2:-1]
                # Check for '...' or "..."
                elif (right.startswith("'") and right.endswith("'")) or \
                     (right.startswith('"') and right.endswith('"')):
                    right = right[1:-1]
                
                # Check for LaTeX syntax (backslashes) and wrap in $ if needed
                if "\\" in right and not (right.startswith("$") and right.endswith("$")):
                    right = f"${right}$"

            attrs = self.parse_svg_attributes(match)

            svg_data = self._render_circuit(left, right)
            svg_html = self.generate_inline_svg(
                svg_data,
                attrs["width"],
                attrs["height"],
                attrs["centered"],
                attrs["sketch"],
                css_class="svg-graph",
            )

            # Wrap in no-break div for print layout
            svg_html = f'<div class="no-break">{svg_html}</div>'

            content = content.replace(match.group(0), svg_html)

        return content

    def _render_circuit(self, expr: str, outlabel: str) -> bytes:
        # Configure matplotlib for SVG output (similar to schemdraw processor)
        try:
            import schemdraw
            schemdraw.use("matplotlib")
            import matplotlib.pyplot as plt
            plt.rcParams['savefig.transparent'] = True
            plt.rcParams['svg.fonttype'] = 'none'
        except ImportError:
            pass

        d = logicparse(expr, outlabel=outlabel)
        svg_data = d.get_imagedata("svg")
        
        # Explicitly close all figures to prevent "More than 20 figures have been opened" warning
        try:
            import matplotlib.pyplot as plt
            plt.close('all')
        except Exception:
            pass

        return svg_data
