import re
from datetime import datetime

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

        # Define missing variables needed for template context
        courses_title = self.config.get("courses_title", "Disciplinas")

        # Default back link for chapters -> Course Contents
        # Since chapters and contents.html are in the same directory usually:
        back_link_url = "../index.html"
        back_link_text = f"Voltar para {config.get('name') or strip_leading_number(node.parent.name) if node.parent else 'Índice'}"

        course_name = ""
        if node.parent:
            course_name = strip_leading_number(node.parent.name)

        siblings = []
        for s in node.siblings:
            sibling_name = strip_leading_number(s.name)
            if s.metadata and s.metadata.get("title"):
                sibling_name = s.metadata["title"]
            elif s.src_path:
                title = self._read_title_from_file(s.src_path)
                if title:
                    sibling_name = title
            siblings.append({"name": sibling_name, "slug": s.slug})

        def sort_key(s):
            match = re.search(r"^(\d+)", s["slug"])
            return int(match.group(1)) if match else 9999

        siblings.sort(key=sort_key)

        current_index = next(
            (i for i, s in enumerate(siblings) if s["slug"] == node.slug), 0
        )
        chapter_num = current_index + 1

        prev_chapter = siblings[current_index - 1] if current_index > 0 else None
        next_chapter = (
            siblings[current_index + 1] if current_index < len(siblings) - 1 else None
        )

        if metadata.get("prev"):
            prev_slug = metadata["prev"]
            prev_chapter = next(
                (s for s in siblings if s["slug"] == prev_slug),
                {"name": strip_leading_number(prev_slug), "slug": prev_slug},
            )

        if metadata.get("next"):
            next_slug = metadata["next"]
            next_chapter = next(
                (s for s in siblings if s["slug"] == next_slug),
                {"name": strip_leading_number(next_slug), "slug": next_slug},
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
                "year": config.get("year", str(datetime.now().year)),
                "author": config.get("author", "Course Forge"),
                "courses_title": courses_title,
                "back_link_url": back_link_url,
                "back_link_text": back_link_text,
                "breadcrumbs": self._build_breadcrumbs(node, config, title),
            }
        )

    def _build_breadcrumbs(
        self, node: ContentNode, config: dict | None, current_title: str
    ) -> list[dict]:
        """Build breadcrumb trail from parent chain."""
        breadcrumbs = []
        parents = []

        current = node.parent
        while current is not None and current.parent is not None:
            parents.insert(0, strip_leading_number(current.name))
            current = current.parent

        for i, name in enumerate(parents):
            if i == len(parents) - 1:
                url = "contents.html"
            else:
                depth = len(parents) - i - 1
                url = "../" * depth + "contents.html"
            breadcrumbs.append({"name": name, "url": url})

        breadcrumbs.append({"name": current_title, "url": "#"})

        return breadcrumbs

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

        chapters = []
        for c in course_node.children:
            if c.is_file and c.file_extension == ".md":
                chapter_name = strip_leading_number(c.name)
                if c.metadata and c.metadata.get("title"):
                    chapter_name = c.metadata["title"]
                elif c.src_path:
                    title = self._read_title_from_file(c.src_path)
                    if title:
                        chapter_name = title
                chapters.append(
                    {
                        "name": chapter_name,
                        "slug": c.slug,
                        "original_name": c.name,
                    }
                )

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
                        if (
                            ch["slug"] == item
                            or ch["slug"].startswith(item + "-")
                            or ch["original_name"] == item
                            or ch["original_name"].startswith(item + " ")
                            or ch["original_name"].startswith(item + "-")
                        ):
                            part_chapters.append(ch)

                from course_forge.infrastructure.markdown.mistune_markdown_renderer import (
                    to_roman,
                )

                parts.append(
                    {
                        "title": part_title,
                        "roman": to_roman(i + 1),
                        "chapters": part_chapters,
                    }
                )

        else:
            parts.append({"title": None, "roman": None, "chapters": chapters})

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
                            "slug": f"{c.slug}/contents.html",
                        }
                    )

        # Smart Back Link Logic for Contents Page
        courses_title = self.config.get("courses_title", "Disciplinas")
        back_link_url = "../index.html"
        back_link_text = f"Voltar para {courses_title}"

        # If course_node has a parent that is NOT the root (root.parent is None),
        # then we are in a sub-course and should link to parent course.
        if course_node.parent and course_node.parent.parent is not None:
            back_link_url = "../contents.html"
            parent_name = strip_leading_number(course_node.parent.name)
            back_link_text = f"Voltar para {parent_name}"

        return template.render(
            {
                "course_name": course_name,
                "parts": parts,
                "modules": modules,
                "modules_title": config.get("modules_title"),
                "site_name": self.config.get("site_name", "Course Forge"),
                "author": self.config.get("author", "Course Forge"),
                "year": config.get("year"),
                "courses_title": courses_title,
                "back_link_url": back_link_url,
                "back_link_text": back_link_text,
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

    def _read_title_from_file(self, file_path: str) -> str | None:
        """Read title from markdown frontmatter."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            if content.startswith("---"):
                end = content.find("---", 3)
                if end != -1:
                    frontmatter = content[3:end]
                    for line in frontmatter.split("\n"):
                        if line.strip().startswith("title:"):
                            title = line.split(":", 1)[1].strip()
                            return title.strip("\"'")
        except Exception:
            pass
        return None
