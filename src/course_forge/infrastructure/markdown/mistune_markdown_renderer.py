from typing import Any

import mistune
from mistune import HTMLRenderer

from course_forge.application.renders import MarkdownRenderer


class SlideRenderer(HTMLRenderer):
    def __init__(self, escape: bool = True):
        super().__init__(escape=escape)
        self.in_slide = True

    def heading(self, text: str, level: int, **attrs: Any) -> str:
        html = ""

        if level == 1:
            if self.in_slide:
                html += "</div>\n"
                self.in_slide = False
            html += (
                f'<div class="cover-slide"><h1 class="cover-title">{text}</h1></div>'
            )
            return html

        if level == 2:
            if self.in_slide:
                html += "</div>\n"
            self.in_slide = True
            html += f'<div class="slide"><h2 class="slide-title">{text}</h2>\n'
            return html

        return super().heading(text, level)

    def finalize(self):
        if self.in_slide:
            return "</div>"
        return ""


class MistuneMarkdownRenderer(MarkdownRenderer):
    def render(self, text: str) -> str:
        markdown = mistune.create_markdown(
            renderer=SlideRenderer(escape=False), plugins=["table"]
        )
        return str(markdown(text))
