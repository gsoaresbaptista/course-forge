from jinja2 import Environment, FileSystemLoader

from course_forge.application.renders import HTMLTemplateRenderer
from course_forge.domain.entities import ContentNode


class JinjaHTMLTemplateRenderer(HTMLTemplateRenderer):
    def __init__(self, template_dir: str = "src/course_forge/templates"):
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def render(self, content: str, node: ContentNode) -> str:
        template = self.env.get_template("base.html")
        return template.render({"title": node.name, "content": content})
