import html
import re
import uuid
from typing import Any

import graphviz  # type: ignore

from course_forge.domain.entities import ContentNode

from .base import Processor


class ASTProcessor(Processor):
    pattern = re.compile(
        r"```ast\.plot"
        r"(?:\s+(?:width=(?P<width>\d+)|height=(?P<height>\d+)|(?P<centered>centered)))*"
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
            centered = match.group("centered")

            svg_data = self._render_ast(ast)
            attach_name = f"{node.name}_{node.number_of_attachments}.svg"

            data: dict[str, Any] = {
                "type": "image",
                "data": svg_data,
                "name": attach_name,
            }

            node.attach(data)
            img_attrs = f"{f'width="{width}"' if width else ''} {f'height="{height}"' if height else ''}"
            img_code = (
                f'<img src="static/{attach_name}" {img_attrs} class="ast-plot-img" />'
            )
            img_code = f'<div class="{"centered" if centered else ""}">{img_code}</div>'
            content = content.replace(match.group(0), img_code)

        return {**markdown, "content": content}

    def _render_ast(self, expr: str) -> bytes:
        g = graphviz.Digraph(
            "G",
            graph_attr={"bgcolor": "transparent", "color": "transparent"},
            node_attr={
                "shape": "plaintext",
                "fontsize": "14",
                "fontname": "Comic Sans MS, sans-serif",
            },
            edge_attr={"penwidth": "2", "arrowsize": "0.8", "class": "ast-edge"},
        )

        tokens = expr.replace("(", " ( ").replace(")", " ) ").split()
        self._parse(g, tokens)

        return g.pipe(format="svg")

    def _create_styled_node(self, g: graphviz.Digraph, node_id: str, label: str):
        safe_label = html.escape(label)
        html_label = (
            f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0">'
            f'<TR><TD BORDER="1" SIDES="LRT" CELLPADDING="10">{safe_label}</TD></TR>'
            f'<TR><TD BORDER="1" SIDES="LRB" BGCOLOR="black" HEIGHT="4"></TD></TR>'
            f"</TABLE>>"
        )
        g.node(node_id, label=html_label, shape="plain", **{"class": "ast-op"})  # type: ignore

    def _parse(self, g: graphviz.Digraph, tokens: list[str]) -> str | None:
        if not tokens:
            return None

        token = tokens.pop(0)

        if token == "(":
            if not tokens:
                return None
            label = tokens.pop(0)
            node_id = str(uuid.uuid4())

            self._create_styled_node(g, node_id, label)

            while tokens and tokens[0] != ")":
                child_id = self._parse(g, tokens)
                if child_id:
                    g.edge(node_id, child_id)  # type: ignore

            if tokens and tokens[0] == ")":
                tokens.pop(0)
            return node_id

        if token == ")":
            return None

        node_id = str(uuid.uuid4())
        g.node(node_id, label=token, shape="plaintext", **{"class": "ast-leaf"})  # type: ignore

        return node_id
