import re
from course_forge.domain.entities import ContentNode
from .svg_processor_base import SVGProcessorBase

try:
    import graphviz
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    GRAPHVIZ_AVAILABLE = False


class ASTProcessor(SVGProcessorBase):
    """Processor for Abstract Syntax Tree diagrams.
    
    Accepts simple Lisp-like notation and renders professional AST diagrams
    using Graphviz with styled operators and leaf nodes.
    
    Syntax: ( operator operand1 operand2 ... )
    Example: ( + 1 ( * 2 3 ) )
    """
    
    pattern = SVGProcessorBase.create_pattern("ast.plot", r"(?P<content>.*?)")
    
    def execute(self, node: ContentNode, content: str) -> str:
        if not GRAPHVIZ_AVAILABLE:
            error_msg = '<div class="error">AST processor requires the graphviz package. Install with: pip install graphviz</div>'
            matches = list(self.pattern.finditer(content))
            for match in matches:
                content = content.replace(match.group(0), error_msg)
            return content
        
        matches = list(self.pattern.finditer(content))
        
        for match in matches:
            ast_notation = match.group("content").strip()
            attrs = self.parse_svg_attributes(match)
            
            try:
                # Parse simple notation and convert to Graphviz DOT
                dot_code = self._convert_to_dot(ast_notation)
                
                # Render using Graphviz
                svg_data = self._render_graphviz(dot_code)
                
                svg_html = self.generate_inline_svg(
                    svg_data,
                    attrs["width"],
                    attrs["height"],
                    attrs["centered"],
                    attrs["sketch"],
                    css_class="svg-graph ast-plot-img",
                )
                svg_html = f'<div class="no-break">{svg_html}</div>'
                content = content.replace(match.group(0), svg_html)
            except Exception as e:
                error_msg = f'<div class="error">AST error: {str(e)}</div>'
                content = content.replace(match.group(0), error_msg)
        
        return content
    
    def _convert_to_dot(self, notation: str) -> str:
        """Convert simple Lisp-like notation to Graphviz DOT."""
        # Parse the notation into a tree structure
        tokens = self._tokenize(notation)
        root, _ = self._parse_tokens(tokens, 0)
        
        # Generate DOT code
        dot_lines = [
            "digraph AST {",
            '    bgcolor="transparent"',
            "    rankdir=TB",
            "    nodesep=0.5",
            "    ranksep=0.4",
            "",
            "    /* Operator nodes */",
            "    node [",
            '        shape=box',
            '        style="rounded,filled"',
            '        color="#8a6cff"',
            '        fillcolor="transparent"',
            '        fontname="JetBrains Mono, Fira Code, Consolas, Helvetica"',
            '        fontcolor="#8a6cff"',
            "        penwidth=2",
            "        fontsize=20",
            "    ]",
            "",
        ]
        
        # Add operator nodes
        operators = []
        self._collect_operators(root, operators)
        for op_id, op_label in operators:
            dot_lines.append(f'    {op_id} [label="{self._escape_label(op_label)}"]')
        
        # Switch to leaf node style
        dot_lines.extend([
            "",
            "    /* Leaf nodes */",
            "    node [",
            "        shape=none",
            '        fillcolor="transparent"',
            '        fontcolor="#333333"',
            "        fontsize=20",
            "    ]",
            "",
        ])
        
        # Add leaf nodes
        leaves = []
        self._collect_leaves(root, leaves)
        for leaf_id, leaf_label in leaves:
            dot_lines.append(f'    {leaf_id} [label="{self._escape_label(leaf_label)}"]')
        
        # Add edges
        dot_lines.extend([
            "",
            '    edge [color="#333333", penwidth=1.5, arrowsize=0.7]',
            "",
        ])
        
        edges = []
        self._collect_edges(root, edges)
        for parent, child in edges:
            dot_lines.append(f"    {parent} -> {child}")
        
        dot_lines.append("}")
        
        return "\n".join(dot_lines)
    
    def _tokenize(self, notation: str) -> list:
        """Tokenize the input notation."""
        # Remove extra whitespace and split by spaces, preserving parentheses
        notation = notation.strip()
        tokens = []
        current_token = ""
        
        for char in notation:
            if char in "()":
                if current_token:
                    tokens.append(current_token)
                    current_token = ""
                tokens.append(char)
            elif char.isspace():
                if current_token:
                    tokens.append(current_token)
                    current_token = ""
            else:
                current_token += char
        
        if current_token:
            tokens.append(current_token)
        
        return tokens
    
    def _parse_tokens(self, tokens: list, index: int) -> tuple:
        """Parse tokens into tree structure. Returns (node, next_index)."""
        if index >= len(tokens):
            raise ValueError("Unexpected end of input")
        
        token = tokens[index]
        
        if token == "(":
            # This is a branch node (operator)
            index += 1
            if index >= len(tokens):
                raise ValueError("Expected operator after '('")
            
            operator = tokens[index]
            index += 1
            
            children = []
            while index < len(tokens) and tokens[index] != ")":
                child, index = self._parse_tokens(tokens, index)
                children.append(child)
            
            if index >= len(tokens):
                raise ValueError("Expected ')' to close expression")
            
            index += 1  # Skip the ')'
            
            return {"type": "operator", "value": operator, "children": children}, index
        elif token == ")":
            raise ValueError("Unexpected ')'")
        else:
            # This is a leaf node
            return {"type": "leaf", "value": token}, index + 1
    
    def _collect_operators(self, node: dict, operators: list, node_id: str = "n0", counter: list = [0]):
        """Collect all operator nodes."""
        if node["type"] == "operator":
            operators.append((node_id, node["value"]))
            for i, child in enumerate(node["children"]):
                counter[0] += 1
                child_id = f"n{counter[0]}"
                self._collect_operators(child, operators, child_id, counter)
    
    def _collect_leaves(self, node: dict, leaves: list, node_id: str = "n0", counter: list = [0]):
        """Collect all leaf nodes."""
        if node["type"] == "leaf":
            leaves.append((node_id, node["value"]))
        else:
            for i, child in enumerate(node["children"]):
                counter[0] += 1
                child_id = f"n{counter[0]}"
                self._collect_leaves(child, leaves, child_id, counter)
    
    def _collect_edges(self, node: dict, edges: list, node_id: str = "n0", counter: list = [0]):
        """Collect all edges."""
        if node["type"] == "operator":
            for child in node["children"]:
                counter[0] += 1
                child_id = f"n{counter[0]}"
                edges.append((node_id, child_id))
                self._collect_edges(child, edges, child_id, counter)
    
    def _escape_label(self, label: str) -> str:
        """Escape special characters in labels."""
        # Replace * with proper multiplication symbol
        if label == "*":
            label = "∗"
        return label.replace('"', '\\"')
    
    def _render_graphviz(self, dot_code: str) -> bytes:
        """Render DOT code to SVG using Graphviz."""
        src = graphviz.Source(dot_code, format='svg')
        svg_str = src.pipe(format='svg').decode('utf-8')
        
        # Extract just the SVG element
        svg_match = re.search(r'(<svg[^>]*>.*?</svg>)', svg_str, re.DOTALL)
        if svg_match:
            svg_content = svg_match.group(1)
            return svg_content.encode('utf-8')
        else:
            raise ValueError("Failed to extract SVG from Graphviz output")
