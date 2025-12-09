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
        assets = markdown.get("assets", [])
        matches = list(self.pattern.finditer(content))

        for match in matches:
            left = match.group("ast_data").strip()
            width = match.group("width")
            height = match.group("height")

            svg_bytes = self._render_ast(left)
            asset_index = len(assets)
            token = f"{{{{asset:ast_plot:{asset_index}}}}}"
            attributes: dict[str, Any] = {
                "type": "ast_plot",
                "data": svg_bytes,
                "extension": "svg",
            }

            if width:
                attributes.update({"width": width})
            if height:
                attributes.update({"height": height})

            assets.append(attributes)

            content = content.replace(match.group(0), token)

        return {**markdown, "content": content, "assets": assets}

    def _render_ast(self, expr: str) -> bytes:
        g = graphviz.Digraph(
            "G",
            graph_attr={
                "bgcolor": "transparent",
                "color": "transparent",
            },
            node_attr={
                "shape": "plaintext",
                "fontsize": "14",
                "fontname": "Comic Sans MS, sans-serif",
            },
        )
        tokens = self._tokenize(expr)
        self._parse(g, tokens)
        return g.pipe(format="svg")

    def _tokenize(self, text: str) -> list[str]:
        return text.replace("(", " ( ").replace(")", " ) ").split()

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

        elif token == ")":
            return None

        else:
            node_id = str(uuid.uuid4())
            g.node(node_id, token, **{"class": "terminal-node"})  # type: ignore
            return node_id
