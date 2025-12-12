from jinja2 import BaseLoader, ChoiceLoader, Environment, FileSystemLoader

from course_forge.application.renders import HTMLTemplateRenderer
from course_forge.domain.entities import ContentNode


class JinjaHTMLTemplateRenderer(HTMLTemplateRenderer):
    def __init__(self, template_dir: str | None = None):
        super().__init__(template_dir)

        loaders: list[BaseLoader] = []

        loaders.append(FileSystemLoader(self.template_dir))

        self.env = Environment(loader=ChoiceLoader(loaders))

    def render(self, content: str, node: ContentNode) -> str:
        template = self.env.get_template("base.html")
        return template.render({"title": node.name, "content": content})
