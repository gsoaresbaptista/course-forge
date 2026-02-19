import re
import os
from course_forge.domain.entities import ContentNode
from .base import Processor
from course_forge.config import Config


class AppletProcessor(Processor):
    """Processor for embedding interactive applets.
    
    Syntax:
    ::: applet
    name: tokenizer
    height: 600px
    sketch: true
    :::
    """
    
    pattern = re.compile(
        r":::\s*applet\s*\n(?P<attributes>.*?)\n:::",
        re.DOTALL
    )
    
    def execute(self, node: ContentNode, content: str) -> str:
        matches = list(self.pattern.finditer(content))
        
        for match in matches:
            attributes_raw = match.group("attributes")
            attrs = self._parse_attributes(attributes_raw)
            
            applet_name = attrs.get("name")
            if not applet_name:
                content = content.replace(match.group(0), '<div class="error">Applet error: "name" attribute is required.</div>')
                continue
                
            height = attrs.get("height", "500px")
            sketch = attrs.get("sketch", "false").lower() == "true"
            centered = attrs.get("centered", "true").lower() == "true"
            scrolling = "yes" if attrs.get("scrolling", "false").lower() == "true" else "no"
            
            depth = max(0, len(node.slugs_path) - 1)
            rel_base = "../" * depth
            applet_url = f"{rel_base}applets/{applet_name}/index.html"
            
            container_classes = ["applet-container"]

            if centered:
                container_classes.append("centered")
            if sketch:
                container_classes.append("sketch-border")
                
            iframe_html = f"""
<div class="{' '.join(container_classes)}">
    <iframe src="{applet_url}" width="100%" height="{height}" frameborder="0" style="border: none;" scrolling="{scrolling}"></iframe>
</div>
"""
            content = content.replace(match.group(0), iframe_html)
            
        return content

    def _parse_attributes(self, raw_attributes: str) -> dict:
        attrs = {}
        for line in raw_attributes.strip().splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                attrs[key.strip()] = value.strip()
        return attrs
