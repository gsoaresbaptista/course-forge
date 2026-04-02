from typing import Optional
import re
from schemdraw.parsing.logic_parser import logicparse

from course_forge.domain.entities import ContentNode

from .svg_processor_base import SVGProcessorBase


class DigitalCircuitProcessor(SVGProcessorBase):
    pattern = SVGProcessorBase.create_pattern("digital-circuit.plot", "")

    def execute(self, node: ContentNode, content: str) -> str:
        matches = list(self.pattern.finditer(content))

        for match in matches:
            full_content = match.group("content").strip()
            attrs = self.parse_svg_attributes(match)
            svg_htmls = []

            for line in full_content.split('\n'):
                line = line.strip()
                if not line:
                    continue

                # Re-parse the internal content to get left and right
                sub_match = re.match(r"(?P<left>.+?)(?:=(?P<right>.+?))?$", line)
                if not sub_match:
                    continue

                left = sub_match.group("left").strip()
                right = sub_match.group("right").strip() if sub_match.group("right") else None

                # Detect which side is the expression and which is the output label.
                # Usually the label is a single word, while the expression contains operators.
                # We support both "S = A and B" and "A and B = S".
                if right:
                    # Heuristic: if left is a single identifier and right is more complex, left is outlabel.
                    # If right is a single identifier and left is more complex, right is outlabel.
                    left_is_simple = bool(re.fullmatch(r"[\w\.\$]+", left))
                    right_is_simple = bool(re.fullmatch(r"[\w\.\$]+", right))
                    
                    if left_is_simple and not right_is_simple:
                        expr = right
                        outlabel = left
                    elif right_is_simple and not left_is_simple:
                        expr = left
                        outlabel = right
                    else:
                        # Identity case S = A or both complex (unlikely)
                        # Use documentation default: OutputLabel = Expression
                        expr = right
                        outlabel = left
                else:
                    expr = left
                    outlabel = None

                # If the expression is just a single identifier, we handle it as a simple wire.
                is_identity = bool(re.fullmatch(r"[\w\.\$]+", expr))

                # If expression is a python string literal (e.g. r'...' or "..."),
                # extract the inner string content to allow LaTeX usage without quotes being rendered.
                if expr:
                    # Check for r'...' or r"..."
                    if (expr.startswith("r'") and expr.endswith("'")) or \
                       (expr.startswith('r"') and expr.endswith('"')):
                        expr = expr[2:-1]
                    # Check for '...' or "..."
                    elif (expr.startswith("'") and expr.endswith("'")) or \
                         (expr.startswith('"') and expr.endswith('"')):
                        expr = expr[1:-1]
                    
                    # Check for LaTeX syntax (backslashes) and wrap in $ if needed
                    if "\\" in expr and not (expr.startswith("$") and expr.endswith("$")):
                        expr = f"${expr}$"

                def render_circuit(expr_copy=expr, outlabel_copy=outlabel, is_identity_copy=is_identity):
                    def inner():
                        return self._render_circuit(expr_copy, outlabel_copy, is_identity=is_identity_copy)
                    return inner

                svg_data = self.get_cached_svg_or_render(
                    "digital_circuit",
                    line,
                    render_circuit()
                )
                svg_html = self.generate_inline_svg(
                    svg_data,
                    attrs["width"],
                    attrs["height"],
                    attrs["centered"],
                    attrs["sketch"],
                    css_class="svg-graph",
                )

                # Wrap in no-break div for print layout
                svg_htmls.append(f'<div class="no-break">{svg_html}</div>')

            content = content.replace(match.group(0), "\n".join(svg_htmls))

        return content

    def _render_circuit(self, expr: str, outlabel: Optional[str], is_identity: bool = False) -> bytes:
        # Configure matplotlib for SVG output (similar to schemdraw processor)
        try:
            import schemdraw
            schemdraw.use("matplotlib")
            import matplotlib.pyplot as plt
            plt.rcParams['savefig.transparent'] = True
            plt.rcParams['svg.fonttype'] = 'none'
        except ImportError:
            pass

        if is_identity:
            import schemdraw.elements as elm
            d = schemdraw.Drawing()
            d += elm.Line().length(1.5).label(expr, 'left').label(outlabel, 'right')
        else:
            d = logicparse(expr, outlabel=outlabel)
        
        svg_data = d.get_imagedata("svg")
        
        # Explicitly close all figures to prevent "More than 20 figures have been opened" warning
        try:
            import matplotlib.pyplot as plt
            plt.close('all')
        except Exception:
            pass

        return svg_data
