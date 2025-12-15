import re

from course_forge.application.loaders import MarkdownLoader
from course_forge.application.processors import Processor
from course_forge.application.renders import HTMLTemplateRenderer, MarkdownRenderer
from course_forge.application.writers import OutputWriter
from course_forge.domain.entities import ContentNode
from course_forge.domain.repositories import ContentTreeRepository


class BuildSiteUseCase:
    def __init__(
        self,
        repository: ContentTreeRepository,
        loader: MarkdownLoader,
        markdown_renderer: MarkdownRenderer,
        html_renderer: HTMLTemplateRenderer,
        writer: OutputWriter,
    ) -> None:
        self.repository = repository
        self.loader = loader
        self.markdown_renderer = markdown_renderer
        self.html_renderer = html_renderer
        self.writer = writer

    def execute(
        self,
        root_path: str,
        pre_processors: list[Processor],
        post_processors: list[Processor],
        template_dir: str | None = None,
    ) -> None:
        # Load config from root_path
        from course_forge.infrastructure.config.config_loader import ConfigLoader
        import os

        config_path = os.path.join(root_path, "config.yaml")
        config = ConfigLoader().load(config_path)

        # Inject config into html_renderer if supported
        if hasattr(self.html_renderer, "config"):
            self.html_renderer.config = config

        tree = self.repository.load(root_path)
        self._process_node(
            tree.root, pre_processors, post_processors, global_config=config
        )

        # Only collect top-level courses for the main index
        courses = self._collect_top_level_courses(tree.root)

        if courses:
            index_html = self.html_renderer.render_index(courses)
            for processor in post_processors:
                index_html = processor.execute(tree.root, index_html)
            self.writer.write_index(index_html)

        self.writer.copy_assets(self.html_renderer.template_dir)

    def _collect_top_level_courses(self, node: ContentNode) -> list[dict]:
        courses = []
        # We only want direct children of root that are courses
        for child in node.children:
            if not child.is_file:
                # Check if it has markdown files directly or is a course container
                has_md = any(
                    c.is_file and c.file_extension == ".md" for c in child.children
                )

                # If it has MD files, it's a course. Add it.
                if has_md:
                    courses.append(
                        {
                            "name": self._clean_name(child.name),
                            "slug": child.relative_path
                            if hasattr(child, "relative_path")
                            else child.name,  # logic adjustment
                            "node": child,
                        }
                    )
                # If it doesn't have MD files but has children directories, maybe one of them is a course?
                # But for the root index, we typically want "Discipline" level.
                # If "sistemas-digitais" contains "logica-proposicional", "sistemas-digitais" IS the entry point.
                # Even if "sistemas-digitais" has NO md files itself (just sub-courses), it should act as the grouping.
                # Current logic requires MD files to be considered a course.
                # Let's stick to: if it has MD files or has children that are dirs with MD files.
                elif any(
                    not gc.is_file
                    and any(
                        ggc.is_file and ggc.file_extension == ".md"
                        for ggc in gc.children
                    )
                    for gc in child.children
                ):
                    courses.append(
                        {
                            "name": self._clean_name(child.name),
                            "slug": child.name,
                            "node": child,
                        }
                    )
        return courses

    def _clean_name(self, name: str) -> str:
        cleaned = re.sub(r"^[\d]+[-_.\s]*", "", name)
        return cleaned.replace("-", " ").replace("_", " ").title() if cleaned else name

    def _process_node(
        self,
        node: ContentNode,
        pre_processors: list[Processor],
        post_processors: list[Processor],
        global_config: dict | None = None,
        parent_course_config: dict | None = None,
    ) -> None:
        import os
        from course_forge.infrastructure.config.config_loader import ConfigLoader

        current_config = parent_course_config

        # Check for config.yaml in this directory if it's a directory
        if not node.is_file and node.src_path:
            local_config_path = os.path.join(node.src_path, "config.yaml")
            if os.path.exists(local_config_path):
                local_config = ConfigLoader().load(local_config_path)
                # Merge with parent config or override? Usually override for specific fields.
                # Let's assume local config takes precedence for course details.
                current_config = local_config

        if node.is_file:
            if node.file_extension == ".md":
                markdown = self.loader.load(node.src_path)
                content = markdown["content"]
                metadata = markdown.get("metadata", {})

                for processor in pre_processors:
                    content = processor.execute(node, content)

                chapter = None
                match = re.match(r"^(\d+)-", node.name)
                if match:
                    chapter = int(match.group(1))

                content = self.markdown_renderer.render(content, chapter=chapter)
                # Pass merged config (global + course) to renderer
                # Merging logic: global base, course override
                render_config = (global_config or {}).copy()
                if current_config:
                    render_config.update(current_config)

                html = self.html_renderer.render(
                    content, node, metadata=metadata, config=render_config
                )

                for processor in post_processors:
                    html = processor.execute(node, html)

                self.writer.write(node, html)
            else:
                self.writer.copy_file(node)
        else:
            has_md_files = any(
                c.is_file and c.file_extension == ".md" for c in node.children
            )
            # Or has sub-courses?
            has_subcourses = any(
                not c.is_file
                and any(gc.is_file and gc.file_extension == ".md" for gc in c.children)
                for c in node.children
            )

            if (has_md_files or has_subcourses) and node.parent is not None:
                render_config = (global_config or {}).copy()
                if current_config:
                    render_config.update(current_config)

                contents_html = self.html_renderer.render_contents(
                    node, config=render_config
                )
                for processor in post_processors:
                    contents_html = processor.execute(node, contents_html)
                self.writer.write_contents(node, contents_html)

        for child in node.children:
            self._process_node(
                child, pre_processors, post_processors, global_config, current_config
            )
