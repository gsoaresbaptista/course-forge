import re
import html
from course_forge.domain.entities import ContentNode
from .svg_processor_base import SVGProcessorBase


class MermaidProcessor(SVGProcessorBase):
    """Processor for Mermaid diagrams.
    
    Converts ```mermaid.plot blocks into <div class="mermaid"> tags
    that are rendered by mermaid.js in the browser.
    
    Syntax:
    ```mermaid.plot [width=N] [height=N] [centered]
    graph TD
        A --> B
    ```
    """
    
    pattern = SVGProcessorBase.create_pattern("mermaid.plot", "")
    
    def execute(self, node: ContentNode, content: str) -> str:
        def replace_mermaid(match: re.Match) -> str:
            indent = match.group("indent")
            
            # Extract content and remove leading/trailing whitespace
            # Also remove empty lines that might cause issues in some Mermaid versions
            diagram_lines = match.group("content").splitlines()
            diagram_content = "\n".join(line for line in diagram_lines if line.strip())
            
            attrs = self.parse_svg_attributes(match)
            
            # Use <pre> tag to protect newlines from being stripped by HTML minifiers.
            # Mermaid.js works fine with <pre class="mermaid">.
            # We must escape the content because characters like < and > 
            # might otherwise be interpreted as HTML tags by the browser.
            escaped_content = html.escape(diagram_content)
            # The source code block uses mermaid class for potential highlighting
            # Apply wrapping and centering to the internal display div instead
            display_class = "mermaid-display"
            if attrs["centered"]:
                display_class += " centered"
            
            display_style_parts = []
            if attrs["width"]:
                display_style_parts.append(f"width: {attrs['width']}px")
            if attrs["height"]:
                display_style_parts.append(f"height: {attrs['height']}px")
            display_style_attr = f' style="{"; ".join(display_style_parts)}"' if display_style_parts else ""

            mermaid_html = (
                f'<div class="mermaid-outer-container">'
                f'  <div class="mermaid-switcher">'
                f'    <div class="switcher-track">'
                f'      <button class="switcher-btn active" onclick="CourseForgeUI.switchMermaidView(this, \'diagram\')"><i data-lucide="eye"></i> Diagrama</button>'
                f'      <button class="switcher-btn" onclick="CourseForgeUI.switchMermaidView(this, \'code\')"><i data-lucide="code"></i> Código</button>'
                f'      <div class="switcher-slider"></div>'
                f'    </div>'
                f'  </div>'
                f'  <div class="mermaid-content">'
                f'    <div class="{display_class}"{display_style_attr}>'
                f'      <pre class="mermaid">{escaped_content}</pre>'
                f'    </div>'
                f'    <div class="mermaid-source" style="display: none;">'
                f'      <pre class="language-mermaid"><code>{escaped_content}</code></pre>'
                f'    </div>'
                f'  </div>'
                f'</div>'
            )
            
            return f'\n{indent}{mermaid_html}\n'

        return self.pattern.sub(replace_mermaid, content)
