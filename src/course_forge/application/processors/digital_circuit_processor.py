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
        d = logicparse(expr, outlabel=outlabel)
        return d.get_imagedata("svg")
