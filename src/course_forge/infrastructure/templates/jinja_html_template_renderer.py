import re

from jinja2 import BaseLoader, ChoiceLoader, Environment, FileSystemLoader

from course_forge.application.renders import HTMLTemplateRenderer
from course_forge.domain.entities import ContentNode


def strip_leading_number(name: str) -> str:
    """Remove leading numbers and separators from name (e.g., '1-intro' -> 'intro')."""
    cleaned = re.sub(r"^[\d]+[-_.\s]*", "", name)
    return cleaned.replace("-", " ").replace("_", " ").title() if cleaned else name


def extract_toc(html_content: str) -> list[dict]:
    """Extract table of contents from HTML headings (h2, h3)."""
    h2_pattern = r'<h2[^>]*id="([^"]+)"[^>]*><span class="heading-roman">([^<]+)</span><span class="heading-text">([^<]+)</span>'
    h3_pattern = r'<h3[^>]*id="([^"]+)"[^>]*><span class="heading-text">([^<]+)</span><span class="heading-arabic">([^<]+)</span>'

    toc = []

    for match in re.finditer(h2_pattern, html_content, re.IGNORECASE):
        id_attr, roman, text = match.groups()
        toc.append({"id": id_attr, "text": f"{roman}. {text.strip()}", "level": 2})

    for match in re.finditer(h3_pattern, html_content, re.IGNORECASE):
        id_attr, text, arabic = match.groups()
        toc.append({"id": id_attr, "text": f"{arabic} {text.strip()}", "level": 3})

    all_headings = re.findall(r'<h[23][^>]*id="([^"]+)"', html_content)
    toc.sort(
        key=lambda x: all_headings.index(x["id"]) if x["id"] in all_headings else 0
    )

    return toc


class JinjaHTMLTemplateRenderer(HTMLTemplateRenderer):
    def __init__(self, template_dir: str | None = None):
        super().__init__(template_dir)

        loaders: list[BaseLoader] = []

        loaders.append(FileSystemLoader(self.template_dir))

        self.env = Environment(loader=ChoiceLoader(loaders))

    def render(self, content: str, node: ContentNode) -> str:
        template = self.env.get_template("base.html")

        course_name = ""
        if node.parent:
            course_name = strip_leading_number(node.parent.name)

        siblings = [
            {"name": strip_leading_number(s.name), "slug": s.name}
            for s in node.siblings
        ]

        current_index = next(
            (i for i, s in enumerate(siblings) if s["slug"] == node.name), 0
        )
        chapter_num = current_index + 1

        prev_chapter = siblings[current_index - 1] if current_index > 0 else None
        next_chapter = (
            siblings[current_index + 1] if current_index < len(siblings) - 1 else None
        )

        title = strip_leading_number(node.name)
        toc = extract_toc(content)

        return template.render(
            {
                "title": title,
                "content": content,
                "course_name": course_name,
                "siblings": siblings,
                "current_slug": node.name,
                "chapter_num": chapter_num,
                "prev_chapter": prev_chapter,
                "next_chapter": next_chapter,
                "toc": toc,
            }
        )

    def render_contents(self, course_node: ContentNode) -> str:
        """Render contents.html for a course directory."""
        template = self.env.get_template("contents.html")

        course_name = strip_leading_number(course_node.name)
        chapters = [
            {"name": strip_leading_number(c.name), "slug": c.name}
            for c in course_node.children
            if c.is_file and c.file_extension == ".md"
        ]

        return template.render(
            {
                "course_name": course_name,
                "chapters": chapters,
            }
        )

    def render_index(self, courses: list[ContentNode]) -> str:
        """Render index.html listing available courses."""
        template = self.env.get_template("index.html")

        course_list = [
            {"name": strip_leading_number(c.name), "slug": c.name} for c in courses
        ]

        return template.render({"courses": course_list})
