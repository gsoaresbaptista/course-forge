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
        tree = self.repository.load(root_path)
        self._process_node(tree.root, pre_processors, post_processors)
        if template_dir:
            self.writer.copy_assets(template_dir)

    def _process_node(
        self,
        node: ContentNode,
        pre_processors: list[Processor],
        post_processors: list[Processor],
    ) -> None:
        if node.is_file:
            markdown = self.loader.load(node.src_path)
            content = markdown["content"]

            for processor in pre_processors:
                content = processor.execute(node, content)

            content = self.markdown_renderer.render(content)
            html = self.html_renderer.render(content, node)

            for processor in post_processors:
                markdown = processor.execute(node, html)

            self.writer.write(node, html)

        for child in node.children:
            self._process_node(child, pre_processors, post_processors)
