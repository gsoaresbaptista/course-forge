import re
from typing import Any

from schemdraw.parsing.logic_parser import logicparse

from course_forge.domain.entities import ContentNode

from .base import Processor


class DigitalCircuitProcessor(Processor):
    pattern = re.compile(
        r"```digital-circuit\.plot"
        r"(?:\s+(?:width=(?P<width>\d+)|height=(?P<height>\d+)|(?P<centered>centered)))*"
        r"\s+(?P<left>.+?)(?:=(?P<right>.+?))?```",
        re.DOTALL,
    )

    def execute(self, node: ContentNode, content: str) -> str:
        matches = list(self.pattern.finditer(content))

        for match in matches:
            left = match.group("left").strip()
            right = match.group("right").strip() if match.group("right") else ""
            width = match.group("width")
            height = match.group("height")
            centered = match.group("centered")

            svg_data = self._render_circuit(left, right)
            attach_name = f"{node.name}_{node.number_of_attachments}.svg"

            data: dict[str, Any] = {
                "type": "image",
                "data": svg_data,
                "name": attach_name,
            }

            node.attach(data)
            img_attrs = f"{f'width="{width}"' if width else ''} {f'height="{height}"' if height else ''}"
            img_code = f'<img src="static/{attach_name}" {img_attrs} />'
            img_code = f'<div class="no-break {"centered" if centered else ""}">{img_code}</div>'
            content = content.replace(match.group(0), img_code)

        return content

    def _render_circuit(self, expr: str, outlabel: str) -> bytes:
        d = logicparse(expr, outlabel=outlabel)
        return d.get_imagedata("svg")
