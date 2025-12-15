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
        self._process_node(tree.root, pre_processors, post_processors)

        courses = self._collect_courses(tree.root)

        if courses:
            index_html = self.html_renderer.render_index(courses)
            for processor in post_processors:
                index_html = processor.execute(tree.root, index_html)
            self.writer.write_index(index_html)

        self.writer.copy_assets(self.html_renderer.template_dir)

    def _collect_courses(self, node: ContentNode) -> list[dict]:
        courses = []
        if not node.is_file:
            # Check if this directory has any markdown files directly inside it
            has_md = any(c.is_file and c.file_extension == ".md" for c in node.children)
            if has_md and node.parent is not None:  # Exclude root itself
                slug = "/".join(node.slugs_path + [node.name])
                courses.append(
                    {
                        "name": self._clean_name(node.name),
                        "slug": slug,
                    }
                )

            for child in node.children:
                courses.extend(self._collect_courses(child))
        return courses

    def _clean_name(self, name: str) -> str:
        cleaned = re.sub(r"^[\d]+[-_.\s]*", "", name)
        return cleaned.replace("-", " ").replace("_", " ").title() if cleaned else name

    def _process_node(
        self,
        node: ContentNode,
        pre_processors: list[Processor],
        post_processors: list[Processor],
    ) -> None:
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
                html = self.html_renderer.render(content, node, metadata=metadata)

                for processor in post_processors:
                    html = processor.execute(node, html)

                self.writer.write(node, html)
            else:
                self.writer.copy_file(node)
        else:
            has_md_files = any(
                c.is_file and c.file_extension == ".md" for c in node.children
            )
            if has_md_files and node.parent is not None:
                contents_html = self.html_renderer.render_contents(node)
                for processor in post_processors:
                    contents_html = processor.execute(node, contents_html)
                self.writer.write_contents(node, contents_html)

        for child in node.children:
            self._process_node(child, pre_processors, post_processors)
