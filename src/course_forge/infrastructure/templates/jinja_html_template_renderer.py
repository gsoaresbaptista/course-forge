from jinja2 import BaseLoader, ChoiceLoader, DictLoader, Environment, FileSystemLoader

from course_forge.application.renders import HTMLTemplateRenderer
from course_forge.domain.entities import ContentNode

DEFAULT_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{{ title or "Página" }}</title>
</head>
<body>
    <header><!-- Navegação ou logo --></header>
    <main>{{ content }}</main>
    <footer><!-- Rodapé --></footer>
</body>
</html>
""".strip()


class JinjaHTMLTemplateRenderer(HTMLTemplateRenderer):
    def __init__(self, template_dir: str | None = None):
        loaders: list[BaseLoader] = []

        if template_dir:
            loaders.append(FileSystemLoader(template_dir))

        loaders.append(DictLoader({"base.html": DEFAULT_TEMPLATE}))

        self.env = Environment(loader=ChoiceLoader(loaders))

    def render(self, content: str, node: ContentNode) -> str:
        template = self.env.get_template("base.html")
        return template.render({"title": node.name, "content": content})
