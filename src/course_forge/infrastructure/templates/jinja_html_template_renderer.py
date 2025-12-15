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
    toc = []

    def clean(s):
        return s.strip()

    # For now, let's assume we will change the renderer to:
    # H2: <h2 id=".."><span class="heading-text">Title</span><span class="heading-arabic">1</span></h2>
    # H3: <h3 id=".."><span class="heading-text">Title</span><span class="heading-arabic">1.1</span></h3>

    heading_pattern = r'<h([23])[^>]*id="([^"]+)"[^>]*>.*?<span class="heading-text">([^<]+)</span>.*?<span class="heading-arabic">([^<]+)</span>'

    for match in re.finditer(heading_pattern, html_content, re.IGNORECASE | re.DOTALL):
        level, id_attr, text, number = match.groups()
        toc.append(
            {
                "id": id_attr,
                "text": f"{clean(number)}. {clean(text)}",
                "level": int(level),
            }
        )

    return toc


class JinjaHTMLTemplateRenderer(HTMLTemplateRenderer):
    def __init__(self, template_dir: str | None = None, config: dict | None = None):
        super().__init__(template_dir)
        self.config = config or {}

        loaders: list[BaseLoader] = []

        loaders.append(FileSystemLoader(self.template_dir))

        self.env = Environment(loader=ChoiceLoader(loaders))

    def render(
        self,
        content: str,
        node: ContentNode,
        metadata: dict | None = None,
        config: dict | None = None,
    ) -> str:
        template = self.env.get_template("base.html")
        metadata = metadata or {}
        config = config or self.config

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

        title = metadata.get("title") or strip_leading_number(node.name)
        date = metadata.get("date")
        if date and isinstance(date, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", date):
            # Convert YYYY-MM-DD to DD/MM/YYYY
            y, m, d = date.split("-")
            date = f"{d}/{m}/{y}"

        toc = extract_toc(content)

        return template.render(
            {
                "title": title,
                "date": date,
                "content": content,
                "course_name": config.get("name", course_name)
                if config
                else course_name,
                "siblings": siblings,
                "current_slug": node.name,
                "chapter_num": chapter_num,
                "prev_chapter": prev_chapter,
                "next_chapter": next_chapter,
                "toc": toc,
                "site_name": self.config.get("site_name", "Course Forge"),
                "author": self.config.get("author", "Course Forge"),
                "courses_title": self.config.get("courses_title", "Disciplinas"),
            }
        )

    def render_contents(
        self, course_node: ContentNode, config: dict | None = None
    ) -> str:
        """Render contents.html for a course directory."""
        template = self.env.get_template("contents.html")
        config = (
            config or self.config
        )  # Merge logic happened in build_site, but here we fallback to global

        course_name = config.get("name") if config else None
        if not course_name:
            course_name = strip_leading_number(course_node.name)

        chapters = [
            {"name": strip_leading_number(c.name), "slug": c.name}
            for c in course_node.children
            if c.is_file and c.file_extension == ".md"
        ]

        def sort_key(ch):
            match = re.search(r"^(\d+)", ch["slug"])
            return int(match.group(1)) if match else 9999

        chapters.sort(key=sort_key)

        parts = []
        config_parts = config.get("parts") or config.get("groups")
        
        if config_parts:
            for i, part_config in enumerate(config_parts):
                part_title = part_config.get("title") or part_config.get("name")
                
                part_items = part_config.get("items") or []
                
                part_chapters = []
                for item in part_items:
                    for ch in chapters:
                        if ch["slug"] == item or ch["slug"].startswith(item + "-"):
                             part_chapters.append(ch)
                             
                from course_forge.infrastructure.markdown.mistune_markdown_renderer import to_roman
                
                parts.append({
                    "title": part_title,
                    "roman": to_roman(i + 1),
                    "chapters": part_chapters
                })
                
        else:
            parts.append({
                "title": None,
                "roman": None,
                "chapters": chapters
            })

        # Sub-courses / Modules
        modules = []
        for c in course_node.children:
            if not c.is_file:
                has_md = any(
                    gc.is_file and gc.file_extension == ".md" for gc in c.children
                )
                if has_md:
                    modules.append(
                        {
                            "name": strip_leading_number(c.name),
                            "slug": f"{c.name}/contents",  # Link to its contents page
                        }
                    )

        return template.render(
            {
                "course_name": course_name,
                "parts": parts,
                "modules": modules,
                "site_name": self.config.get("site_name", "Course Forge"),
                "author": self.config.get("author", "Course Forge"),
                "year": config.get("year"),
                "courses_title": self.config.get("courses_title", "Disciplinas"),
            }
        )

    def render_index(self, courses: list[dict]) -> str:
        """Render index.html listing available courses."""
        template = self.env.get_template("index.html")

        return template.render(
            {
                "courses": courses,
                "site_name": self.config.get("site_name", "Course Forge"),
                "courses_title": self.config.get("courses_title", "Cursos Disponíveis"),
            }
        )
