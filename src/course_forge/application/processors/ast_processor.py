import html
import uuid

import graphviz  # type: ignore

from course_forge.domain.entities import ContentNode

from .svg_processor_base import SVGProcessorBase


class ASTProcessor(SVGProcessorBase):
    pattern = SVGProcessorBase.create_pattern("ast.plot", r"(?P<ast_data>.+?)")

    def execute(self, node: ContentNode, content: str) -> str:
        matches = list(self.pattern.finditer(content))

        for match in matches:
            ast = match.group("ast_data").strip()
            attrs = self.parse_svg_attributes(match)

            svg_data = self._render_ast(ast)
            svg_html = self.generate_inline_svg(
                svg_data,
                attrs["width"],
                attrs["height"],
                attrs["centered"],
                attrs["sketch"],
                css_class="svg-graph ast-plot-img",
            )

            content = content.replace(match.group(0), svg_html)

        return content

    def _render_ast(self, expr: str) -> bytes:
        g = graphviz.Digraph(
            "G",
            graph_attr={"bgcolor": "transparent", "color": "transparent"},
            node_attr={
                "shape": "plaintext",
                "fontsize": "14",
                "fontname": "Comic Sans MS, sans-serif",
            },
            edge_attr={
                "penwidth": "2",
                "arrowsize": "0.8",
                "class": "ast-edge",
            },
        )

        tokens = expr.replace("(", " ( ").replace(")", " ) ").split()
        self._parse(g, tokens)

        return g.pipe(format="svg")

    def _create_styled_node(self, g: graphviz.Digraph, node_id: str, label: str):
        safe_label = html.escape(label)
        html_label = (
            f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="10">'
            f"<TR><TD>{safe_label}</TD></TR>"
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
        safe_token = html.escape(token)
        html_label = (
            f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="8">'
            f"<TR><TD>{safe_token}</TD></TR>"
            f"</TABLE>>"
        )
        g.node(node_id, label=html_label, shape="plain", **{"class": "ast-leaf"})  # type: ignore

        return node_id
