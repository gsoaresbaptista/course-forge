import re
from course_forge.domain.entities import ContentNode
from .svg_processor_base import SVGProcessorBase

try:
    import graphviz
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    GRAPHVIZ_AVAILABLE = False


class GraphvizProcessor(SVGProcessorBase):
    """Processor for Graphviz diagrams using DOT notation.
    
    Supports native Graphviz DOT syntax for creating diagrams with
    automatic layout, clustering, and professional styling.
    """
    
    pattern = SVGProcessorBase.create_pattern("graphviz.plot", r"(?P<content>.*?)")
    
    def execute(self, node: ContentNode, content: str) -> str:
        if not GRAPHVIZ_AVAILABLE:
            error_msg = '<div class="error">Graphviz processor requires the graphviz package. Install with: pip install graphviz</div>'
            return content.replace(
                self.pattern.search(content).group(0) if self.pattern.search(content) else "",
                error_msg
            )
        
        matches = list(self.pattern.finditer(content))
        
        for match in matches:
            dot_code = match.group("content").strip()
            attrs = self.parse_svg_attributes(match)
            
            try:
                # Render the DOT code to SVG
                svg_data = self._render_graphviz(dot_code, attrs)
                
                svg_html = self.generate_inline_svg(
                    svg_data,
                    attrs["width"],
                    attrs["height"],
                    attrs["centered"],
                    attrs["sketch"],
                    css_class="svg-graph graphviz-img",
                )
                svg_html = f'<div class="no-break">{svg_html}</div>'
                content = content.replace(match.group(0), svg_html)
            except Exception as e:
                error_msg = f'<div class="error">Graphviz error: {str(e)}</div>'
                content = content.replace(match.group(0), error_msg)
        
        return content
    
    def _render_graphviz(self, dot_code: str, attrs: dict) -> bytes:
        """Render DOT notation to SVG using Graphviz."""
        # Determine graph type from DOT code
        dot_code_lower = dot_code.lower().strip()
        
        if dot_code_lower.startswith('digraph'):
            src = graphviz.Source(dot_code, format='svg')
        elif dot_code_lower.startswith('graph'):
            src = graphviz.Source(dot_code, format='svg')
        else:
            # Default to digraph if not specified
            src = graphviz.Source(f'digraph {{\n{dot_code}\n}}', format='svg')
        
        # Render to SVG
        svg_str = src.pipe(format='svg').decode('utf-8')
        
        # Extract just the SVG element (remove XML declaration and DOCTYPE)
        svg_match = re.search(r'(<svg[^>]*>.*?</svg>)', svg_str, re.DOTALL)
        if svg_match:
            svg_content = svg_match.group(1)
            return svg_content.encode('utf-8')
        else:
            raise ValueError("Failed to extract SVG from Graphviz output")
