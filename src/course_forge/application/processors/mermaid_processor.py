import html

from course_forge.domain.entities import ContentNode

from .svg_processor_base import SVGProcessorBase


class MermaidProcessor(SVGProcessorBase):
    pattern = SVGProcessorBase.create_pattern("mermaid.plot", r"(?P<content>.*?)")

    def execute(self, node: ContentNode, content: str) -> str:
        matches = list(self.pattern.finditer(content))

        for match in matches:
            diagram_code = match.group("content").strip()
            attrs = self.parse_svg_attributes(match)

            style_parts = []
            if attrs["width"]:
                val = attrs["width"]
                if val.isdigit():
                    val += "px"
                style_parts.append(f"max-width: {val}")

            if attrs["height"]:
                val = attrs["height"]
                if val.isdigit():
                    val += "px"
                style_parts.append(f"height: {val}")

            style_attr = f' style="{"; ".join(style_parts)}"' if style_parts else ""

            escaped_code = html.escape(diagram_code)
            mermaid_html = f'<pre class="mermaid"{style_attr}>{escaped_code}</pre>'
            content = content.replace(match.group(0), mermaid_html)

        return content
