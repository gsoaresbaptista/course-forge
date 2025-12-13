import mistune

from course_forge.application.renders import MarkdownRenderer


class MistuneMarkdownRenderer(MarkdownRenderer):
    def render(self, text: str) -> str:
        markdown = mistune.create_markdown(escape=False, plugins=["table"])
        return str(markdown(text))
