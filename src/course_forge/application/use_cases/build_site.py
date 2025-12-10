from course_forge.application.loaders import MarkdownLoader
from course_forge.application.processors import Processor
from course_forge.application.renders import MarkdownRenderer
from course_forge.application.writers import OutputWriter
from course_forge.domain.entities import ContentNode
from course_forge.domain.repositories import ContentTreeRepository


class BuildSiteUseCase:
    def __init__(
        self,
        repository: ContentTreeRepository,
        loader: MarkdownLoader,
        renderer: MarkdownRenderer,
        writer: OutputWriter,
    ) -> None:
        self.repository = repository
        self.loader = loader
        self.renderer = renderer
        self.writer = writer

    def execute(
        self,
        root_path: str,
        pre_processors: list[Processor],
        post_processors: list[Processor],
    ) -> None:
        tree = self.repository.load(root_path)
        self._process_node(tree.root, pre_processors, post_processors)

    def _process_node(
        self,
        node: ContentNode,
        pre_processors: list[Processor],
        post_processors: list[Processor],
    ) -> None:
        if node.is_file:
            markdown = self.loader.load(node.path)

            for processor in pre_processors:
                markdown = processor.execute(node, markdown)

            html = self.renderer.render(markdown["content"])

            for processor in post_processors:
                markdown = processor.execute(node, markdown)

            self.writer.write(node, html)

        for child in node.children:
            self._process_node(child, pre_processors, post_processors)
