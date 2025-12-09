import re
from typing import Any

from schemdraw.parsing.logic_parser import logicparse

from course_forge.domain.entities import ContentNode

from .base import Processor


class DigitalCircuitProcessor(Processor):
    pattern = re.compile(
        r"```digital-circuit\.plot\s+(?P<left>.+?)(?:=(?P<right>.+?))?```", re.DOTALL
    )

    def execute(self, node: ContentNode, markdown: dict[str, Any]) -> dict[str, Any]:
        content = markdown.get("content", "")
        assets = markdown.get("assets", [])
        matches = list(self.pattern.finditer(content))

        for match in matches:
            left = match.group("left").strip()
            right = match.group("right").strip() if match.group("right") else ""
            svg_bytes = self._render_circuit(left, right)
            asset_index = len(assets)
            token = f"{{{{asset:digital_circuit:{asset_index}}}}}"
            assets.append(
                {
                    "type": "digital_circuit",
                    "data": svg_bytes,
                    "extension": "svg",
                }
            )

            content = content.replace(match.group(0), token)

        return {**markdown, "content": content, "assets": assets}

    def _render_circuit(self, expr: str, outlabel: str) -> bytes:
        d = logicparse(expr, outlabel=outlabel)
        return d.get_imagedata("svg")
