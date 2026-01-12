
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

            # Encode diagram code in base64 to ensure safe transport to frontend
            import base64

            encoded_source = base64.b64encode(diagram_code.encode("utf-8")).decode(
                "utf-8"
            )

            # Add data-source attribute and use a temporary class to prevent premature rendering
            # We use a placeholder text to prevent the markdown renderer (Mistune) from
            # parsing the indented mermaid code as a nested code block.
            # The client-side script will restore the full diagram from data-source.
            mermaid_html = f'<pre class="mermaid-hidden" data-source="{encoded_source}"{style_attr}>Loading diagram...</pre>'

            if attrs["sketch"]:
                # Wrapped with explicit newlines
                mermaid_html = f'<div class="mermaid-sketch-container" data-sketch="true">\n{mermaid_html}\n</div>'

            content = content.replace(match.group(0), mermaid_html)

        return content
