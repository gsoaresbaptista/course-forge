import re
from datetime import datetime

from jinja2 import BaseLoader, ChoiceLoader, Environment, FileSystemLoader

from course_forge.application.renders import HTMLTemplateRenderer
from course_forge.domain.entities import ContentNode
from course_forge.utils import strip_leading_number, to_roman


def extract_toc(html_content: str) -> list[dict]:
    """Extract table of contents from HTML headings (h2, h3)."""
    toc = []

    def clean(s):
        return s.strip()

    heading_pattern = r'<h([2-6])[^>]*id="([^"]+)"[^>]*>.*?<span class="heading-text">([^<]+)</span>.*?<span class="heading-arabic">([^<]+)</span>'

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

    def _get_config_allowed_slugs(self, config: dict | None) -> list[str] | None:
        """Get list of allowed item identifiers from config parts.
        
        Returns None if no parts are defined (meaning all chapters should be shown).
        Returns a list of item strings from config parts if defined.
        """
        if not config:
            return None
        
        config_parts = config.get("parts") or config.get("groups")
        if not config_parts:
            return None
        
        allowed = []
        for part_config in config_parts:
            items = part_config.get("items") or []
            allowed.extend(items)
        return allowed

    def _is_slug_in_config(self, slug: str, original_name: str, allowed_items: list[str]) -> bool:
        """Check if a slug matches any of the allowed config items."""
        for item in allowed_items:
            if (
                slug == item
                or slug.startswith(item + "-")
                or original_name == item
                or original_name.startswith(item + " ")
                or original_name.startswith(item + "-")
            ):
                return True
        return False

    def render(
        self,
        content: str,
        node: ContentNode,
        metadata: dict | None = None,
        config: dict | None = None,
    ) -> str:
        template = self.env.get_template("base.html.jinja")
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

        # Get allowed slugs from config if parts exist
        allowed_slugs = self._get_config_allowed_slugs(config)

        siblings = []
        for s in node.siblings:
            # If config defines parts, filter siblings to only include allowed slugs
            if allowed_slugs is not None and not self._is_slug_in_config(s.slug, s.name, allowed_slugs):
                continue

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
                None,
            )
            if prev_chapter is None:
                # Try to find the sibling node and read its title
                prev_name = strip_leading_number(prev_slug)
                for s in node.siblings:
                    if s.slug == prev_slug:
                        if s.metadata and s.metadata.get("title"):
                            prev_name = s.metadata["title"]
                        elif s.src_path:
                            title = self._read_title_from_file(s.src_path)
                            if title:
                                prev_name = title
                        break
                prev_chapter = {"name": prev_name, "slug": prev_slug}

        if metadata.get("next"):
            next_slug = metadata["next"]
            next_chapter = next(
                (s for s in siblings if s["slug"] == next_slug),
                None,
            )
            if next_chapter is None:
                # Try to find the sibling node and read its title
                next_name = strip_leading_number(next_slug)
                for s in node.siblings:
                    if s.slug == next_slug:
                        if s.metadata and s.metadata.get("title"):
                            next_name = s.metadata["title"]
                        elif s.src_path:
                            title = self._read_title_from_file(s.src_path)
                            if title:
                                next_name = title
                        break
                next_chapter = {"name": next_name, "slug": next_slug}

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
                "is_subcourse": bool(
                    len(node.slugs_path) > 1
                    or (config.get("hidden") if config else False)
                ),
                "course_slug": node.slugs_path[0] if node.slugs_path else None,
            }
        )

    def render_slide(
        self,
        content: str,
        node: ContentNode,
        metadata: dict | None = None,
        config: dict | None = None,
    ) -> str:
        """Render content using the Reveal.js slide template."""
        if metadata is None:
            metadata = {}
        if config is None:
            config = {}

        template_context = config.copy()
        template_context.update(metadata)

        template_context["content"] = content
        template_context["title"] = metadata.get("title", node.name)

        template = self.env.get_template("reveal.html.jinja")
        return template.render(**template_context)

    def _get_relative_node_url(
        self, from_node: ContentNode, to_node: ContentNode
    ) -> str:
        """Compute relative URL from from_node's output directory to to_node's output."""
        target = to_node.alias_to if to_node.alias_to else to_node

        # Canonical path for target
        target_slugs = target.slugs_path + [target.slug]

        # Current path for from_node (assumed to be a directory node for contents.html)
        current_slugs = from_node.slugs_path + [from_node.slug]

        # Find common prefix
        i = 0
        while (
            i < len(current_slugs)
            and i < len(target_slugs)
            and current_slugs[i] == target_slugs[i]
        ):
            i += 1

        # Steps up from current_node's directory
        up_steps = len(current_slugs) - i
        # Steps down to target
        down_steps = target_slugs[i:]

        path_parts = [".."] * up_steps + down_steps
        if not path_parts:
            return "contents.html"

        return "/".join(path_parts) + "/contents.html"

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

        # Check if the current node belongs to a "part" (logical grouping)
        part_info = self._find_part_title_for_node(node, config)
        if part_info:
            roman = part_info["roman"]
            title = part_info["title"]

            if breadcrumbs:
                last_crumb = breadcrumbs[-1]
                base_url = last_crumb["url"]
                if base_url:
                    part_url = f"{base_url}#part-{roman}"
                    breadcrumbs.append({"name": f"{roman} - {title}", "url": part_url})
                else:
                    breadcrumbs.append({"name": f"{roman} - {title}", "url": None})
            else:
                breadcrumbs.append({"name": f"{roman} - {title}", "url": None})

        breadcrumbs.append({"name": current_title, "url": "#"})

        return breadcrumbs

    def _find_part_title_for_node(
        self, node: ContentNode, config: dict | None
    ) -> dict | None:
        """Find the logical part info for a given node based on config."""
        if not config:
            return None

        parts = config.get("parts") or config.get("groups")
        if not parts:
            return None

        target_slug = node.slug
        target_name = node.name

        for i, part_config in enumerate(parts):
            items = part_config.get("items") or []
            for item in items:
                # Check for various match types as in render_contents
                if (
                    target_slug == item
                    or target_slug.startswith(item + "-")
                    or target_name == item
                    or target_name.startswith(item + " ")
                    or target_name.startswith(item + "-")
                ):
                    title = part_config.get("title") or part_config.get("name")
                    return {"title": title, "roman": to_roman(i + 1)}
        return None

    def render_contents(
        self, course_node: ContentNode, config: dict | None = None
    ) -> str:
        """Render contents.html for a course directory."""
        template = self.env.get_template("contents.html.jinja")
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

                parts.append(
                    {
                        "title": part_title,
                        "roman": to_roman(i + 1),
                        "chapters": part_chapters,
                    }
                )

        else:
            parts.append({"title": None, "roman": None, "chapters": chapters})

        appendices = []
        for c in course_node.children:
            # Skip slides folder - it has its own dedicated link
            if not c.is_file and c.name.lower() == "slides":
                continue
                
            if not c.is_file:
                has_md = any(
                    gc.is_file and gc.file_extension == ".md" for gc in c.children
                )
                if has_md:
                    # Try to load the submodule's config.yaml for its name
                    module_name = strip_leading_number(c.name)
                    if c.src_path:
                        import os

                        from course_forge.infrastructure.config.config_loader import (
                            ConfigLoader,
                        )

                        module_config_path = os.path.join(c.src_path, "config.yaml")
                        if os.path.exists(module_config_path):
                            module_config = ConfigLoader().load(module_config_path)
                            if module_config.get("name"):
                                module_name = module_config["name"]

                    url = f"{c.slug}/contents.html"
                    if c.alias_to:
                        url = self._get_relative_node_url(course_node, c)

                    appendices.append(
                        {
                            "name": module_name,
                            "slug": url,
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

        # Check if there's a slides folder
        has_slides = False
        for child in course_node.children:
            if not child.is_file and child.name.lower() == "slides":
                # Check if it has markdown files
                has_md = any(
                    gc.is_file and gc.file_extension == ".md" for gc in child.children
                )
                if has_md:
                    has_slides = True
                    break

        return template.render(
            {
                "course_name": course_name,
                "parts": parts,
                "appendices": appendices,
                "appendices_title": config.get("appendices_title")
                or config.get("modules_title"),
                "site_name": self.config.get("site_name", "Course Forge"),
                "author": self.config.get("author", "Course Forge"),
                "year": config.get("year"),
                "courses_title": courses_title,
                "back_link_url": back_link_url,
                "back_link_text": back_link_text,
                "has_slides": has_slides,
                "is_subcourse": bool(
                    len(course_node.slugs_path) > 0
                    or (config.get("hidden") if config else False)
                ),
                "course_slug": course_node.slugs_path[0]
                if course_node.slugs_path
                else course_node.slug,
            }
        )

    def render_index(self, courses: list[dict]) -> str:
        """Render index.html listing available courses."""
        template = self.env.get_template("index.html.jinja")

        processed_courses = []
        for course in courses:
            node = course.get("node")
            slug = course["slug"]
            url = f"{slug}/contents.html"

            if node and node.alias_to:
                # For top-level redirections in index.html, we need to point to the canonical course
                # Since index.html is at root, relative path is just the canonical slug path
                target = node.alias_to
                url = "/".join(target.slugs_path + [target.slug]) + "/contents.html"

            processed_courses.append(
                {
                    "name": course["name"],
                    "slug": url,
                }
            )

        return template.render(
            {
                "courses": processed_courses,
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

    def render_slides(
        self, course_node: ContentNode, slides: list[dict], config: dict | None = None
    ) -> str:
        """Render slides.html for a course's slides directory."""
        template = self.env.get_template("slides.html.jinja")
        config = config or self.config

        course_name = config.get("name") if config else None
        if not course_name:
            course_name = strip_leading_number(course_node.name)

        return template.render(
            {
                "course_name": course_name,
                "slides": slides,
                "site_name": self.config.get("site_name", "Course Forge"),
                "author": self.config.get("author", "Course Forge"),
                "year": config.get("year") if config else None,
            }
        )
