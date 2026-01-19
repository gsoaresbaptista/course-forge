from course_forge.domain.entities import ContentNode

from .svg_processor_base import SVGProcessorBase


class SchemdrawProcessor(SVGProcessorBase):
    pattern = SVGProcessorBase.create_pattern("schemdraw.plot", r"(?P<code>.+?)")

    def execute(self, node: ContentNode, content: str) -> str:
        matches = list(self.pattern.finditer(content))

        for match in matches:
            code = match.group("code").strip()
            attrs = self.parse_svg_attributes(match)

            svg_data = self._render_diagram(code)
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

    def _render_diagram(self, code: str) -> bytes:
        """Execute schemdraw code and return SVG bytes.
        
        Args:
            code: Python code that creates a schemdraw drawing
            
        Returns:
            SVG data as bytes
        """
        import schemdraw
        import schemdraw.elements as elm
        
        # Create a drawing object with show=False to prevent auto-display
        d = schemdraw.Drawing(show=False)
        
        # Create a local namespace with schemdraw imports and the drawing object
        # Provide common schemdraw classes so users don't need to import
        local_namespace = {
            "schemdraw": schemdraw,
            "Drawing": schemdraw.Drawing,
            "elm": elm,
            "d": d,
        }
        
        # Remove import lines and 'with schemdraw.Drawing() as d:' pattern, then unindent
        lines = code.strip().split('\n')
        processed_lines = []
        skip_with = False
        indent_to_remove = 0
        
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            
            # Skip import statements
            if stripped.startswith('import schemdraw') or stripped.startswith('import '):
                if 'schemdraw' in stripped or 'elm' in stripped:
                    continue
            
            # Skip 'with schemdraw.Drawing()' or 'with Drawing()' lines
            if 'with schemdraw.Drawing()' in stripped or 'with Drawing()' in stripped:
                skip_with = True
                # Calculate indentation of the with block content
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    indent_to_remove = len(next_line) - len(next_line.lstrip())
                continue
            
            if skip_with and stripped and not stripped.startswith('#'):
                # Remove the with-block indentation
                current_indent = len(line) - len(line.lstrip())
                new_indent = max(0, current_indent - indent_to_remove)
                processed_lines.append(' ' * new_indent + stripped)
            elif not skip_with:
                processed_lines.append(line)
        
        processed_code = '\n'.join(processed_lines)
        
        # Execute the processed code
        exec(processed_code, local_namespace)
        
        # Get SVG from the drawing without displaying it
        return d.get_imagedata('svg')
