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

            roman = to_roman(self.h2_counter)

            if self.chapter is not None:
                arabic = f"{self.chapter}.{self.h2_counter}"
            else:
                arabic = str(self.h2_counter)

            return (
                f'<h2 id="{slug}">'
                f'<span class="heading-roman">{roman}</span>'
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
        renderer = HeadingRenderer(chapter=chapter)
        markdown = mistune.create_markdown(renderer=renderer, plugins=["table"])
        return str(markdown(text))
