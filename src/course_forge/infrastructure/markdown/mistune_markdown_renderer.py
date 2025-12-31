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


class HeadingRenderer(mistune.HTMLRenderer):
    """Custom renderer that adds section numbers to headings."""

    MAX_LEVELS = 6

    def __init__(self, chapter: int | None = None):
        super().__init__(escape=False)
        self.chapter = chapter
        self.counters = [0] * self.MAX_LEVELS

    def heading(self, text: str, level: int, **attrs) -> str:
        clean_text = strip_heading_number(text)
        slug = slugify(clean_text)

        if 1 <= level <= self.MAX_LEVELS:
            self.counters[level - 1] += 1
            for i in range(level, self.MAX_LEVELS):
                self.counters[i] = 0

            parts = []
            if self.chapter is not None:
                parts.append(str(self.chapter))
            for i in range(level):
                parts.append(str(self.counters[i]))

            arabic = ".".join(parts)
            html_level = level + 1

            return (
                f'<h{html_level} id="{slug}">'
                f'<span class="heading-text">{clean_text}</span>'
                f'<span class="heading-arabic">{arabic}</span>'
                f"</h{html_level}>\n"
            )

    def block_code(self, code: str, info: str | None = None) -> str:
        lang = ""
        if info:
            lang = info.strip().split(None, 1)[0]

        classes = ["line-numbers"]
        if lang:
            classes.append(f"language-{lang}")

        class_str = " ".join(classes)
        data_lang = f' data-lang="{lang.upper()}"' if lang else ""
        return (
            f'<pre class="{class_str}"{data_lang}><code class="language-{lang or "none"}">'
            f"{mistune.escape(code)}"
            f"</code></pre>\n"
        )


class SlideRenderer(mistune.HTMLRenderer):
    """Renderer for Reveal.js slides."""

    def thematic_break(self) -> str:
        """Use horizontal rules as slide separators."""
        return "</section>\n<section>"


class MistuneMarkdownRenderer(MarkdownRenderer):
    COMMENT_PATTERN = re.compile(r"%%[\s\S]*?%%", re.MULTILINE)

    def render(self, text: str, chapter: int | None = None) -> str:
        text = self._strip_comments(text)
        text, placeholders = self._protect_latex(text)

        renderer = HeadingRenderer(chapter=chapter)
        markdown = mistune.create_markdown(
            renderer=renderer, plugins=["table", "strikethrough"]
        )
        html = str(markdown(text))

        html = self._restore_latex(html, placeholders)
        return html

    def render_slide(self, text: str) -> str:
        """Render markdown content as Reveal.js slides."""
        text = self._strip_comments(text)
        text, placeholders = self._protect_latex(text)

        renderer = SlideRenderer(escape=False)
        markdown = mistune.create_markdown(
            renderer=renderer, plugins=["table", "strikethrough"]
        )
        html = str(markdown(text))

        # Wrap in initial section tags
        html = f"<section>{html}</section>"

        html = self._restore_latex(html, placeholders)
        return html

    def _strip_comments(self, text: str) -> str:
        """Remove Obsidian-style comments (%% ... %%)."""
        return self.COMMENT_PATTERN.sub("", text)

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
