import re

import mistune

from course_forge.application.renders import MarkdownRenderer


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = text.strip("-")
    return text


def strip_heading_number(text: str) -> str:
    """Remove leading section numbers from heading text."""
    return re.sub(r"^[\d]+(?:\.[\d]+)*\s*", "", text).strip()


def to_roman(num: int) -> str:
    """Convert integer to Roman numeral."""
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    roman = ""
    for i, v in enumerate(val):
        while num >= v:
            roman += syms[i]
            num -= v
    return roman


class HeadingRenderer(mistune.HTMLRenderer):
    """Custom renderer that adds section numbers to headings."""

    def __init__(self, chapter: int | None = None):
        super().__init__(escape=False)
        self.chapter = chapter
        self.h2_counter = 0
        self.h3_counter = 0

    def heading(self, text: str, level: int, **attrs) -> str:
        clean_text = strip_heading_number(text)
        slug = slugify(clean_text)

        if level == 2:
            self.h2_counter += 1
            self.h3_counter = 0

            if self.chapter is not None:
                arabic = f"{self.chapter}.{self.h2_counter}"
            else:
                arabic = str(self.h2_counter)

            return (
                f'<h2 id="{slug}">'
                f'<span class="heading-text">{clean_text}</span>'
                f'<span class="heading-arabic">{arabic}</span>'
                f"</h2>\n"
            )

        if level == 3:
            self.h3_counter += 1

            if self.chapter is not None:
                arabic = f"{self.chapter}.{self.h2_counter}.{self.h3_counter}"
            else:
                arabic = f"{self.h2_counter}.{self.h3_counter}"

            return (
                f'<h3 id="{slug}">'
                f'<span class="heading-text">{clean_text}</span>'
                f'<span class="heading-arabic">{arabic}</span>'
                f"</h3>\n"
            )

        return f'<h{level} id="{slug}">{clean_text}</h{level}>\n'


class MistuneMarkdownRenderer(MarkdownRenderer):
    def render(self, text: str, chapter: int | None = None) -> str:
        text, placeholders = self._protect_latex(text)

        renderer = HeadingRenderer(chapter=chapter)
        markdown = mistune.create_markdown(
            renderer=renderer, plugins=["table", "strikethrough"]
        )
        html = str(markdown(text))

        html = self._restore_latex(html, placeholders)
        return html

    def _protect_latex(self, text: str) -> tuple[str, dict[str, str]]:
        """Replace LaTeX blocks with placeholders to prevent markdown processing."""
        placeholders: dict[str, str] = {}
        counter = 0

        def replace_block(match: re.Match) -> str:
            nonlocal counter
            placeholder = f"<!--LATEXBLOCK{counter}-->"
            placeholders[placeholder] = match.group(0)
            counter += 1
            return placeholder

        text = re.sub(r"\$\$[\s\S]+?\$\$", replace_block, text)
        text = re.sub(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", replace_block, text)

        return text, placeholders

    def _restore_latex(self, html: str, placeholders: dict[str, str]) -> str:
        """Restore LaTeX blocks from placeholders."""
        for placeholder, original in placeholders.items():
            html = html.replace(placeholder, original)
        return html
