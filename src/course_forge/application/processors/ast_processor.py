import re
import uuid
from typing import Any

import graphviz  # type: ignore

from course_forge.domain.entities import ContentNode

from .base import Processor


class ASTProcessor(Processor):
    pattern = re.compile(
        r"```ast\.plot"
        r"(?:\s+width=(?P<width>\d+))?"
        r"(?:\s+height=(?P<height>\d+))?"
        r"\s+(?P<ast_data>.+?)```",
        re.DOTALL,
    )

    def execute(self, node: ContentNode, markdown: dict[str, Any]) -> dict[str, Any]:
        content = markdown.get("content", "")
        matches = list(self.pattern.finditer(content))

        for match in matches:
            ast = match.group("ast_data").strip()
            width = match.group("width")
            height = match.group("height")
            svg_data, attach_name = self._render_ast(node, ast)

            data: dict[str, Any] = {
                "type": "image",
                "data": svg_data,
                "name": attach_name,
            }

            node.attach(data)
            img_attrs = f"{f'width="{width}"' if width else ''} {f'height="{height}"' if height else ''}"
            img_code = f'<img src="static/{attach_name}" {img_attrs} />'
            content = content.replace(match.group(0), img_code)

        return {**markdown, "content": content}

    def _render_ast(
        self,
        node: ContentNode,
        expr: str,
    ) -> tuple[bytes, str]:
        g = graphviz.Digraph(
            "G",
            graph_attr={"bgcolor": "transparent", "color": "transparent"},
            node_attr={
                "shape": "plaintext",
                "fontsize": "14",
                "fontname": "Comic Sans MS, sans-serif",
            },
        )

        tokens = expr.replace("(", " ( ").replace(")", " ) ").split()
        self._parse(g, tokens)

        attach_name = f"{node.name}_{node.number_of_attachments}.svg"
        svg_data = g.pipe(format="svg")

        return svg_data, attach_name

    def _parse(self, g: graphviz.Digraph, tokens: list[str]) -> str | None:
        token = tokens.pop(0)

        if token == "(":
            label = tokens.pop(0)
            node_id = str(uuid.uuid4())
            g.node(node_id, label, **{"class": "internal-node"})  # type: ignore

            while tokens[0] != ")":
                child_id = self._parse(g, tokens)
                if child_id:
                    g.edge(node_id, child_id, **{"class": "edge-path"})  # type: ignore

            tokens.pop(0)
            return node_id

        if token == ")":
            return None

        else:
            node_id = str(uuid.uuid4())
            g.node(node_id, token, **{"class": "terminal-node"})  # type: ignore
            return node_id
