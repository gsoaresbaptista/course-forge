from course_forge.application.processors import (
    ASTProcessor,
    DigitalCircuitProcessor,
    HTMLMinifyProcessor,
    Processor,
)
from course_forge.application.use_cases.build_site import BuildSiteUseCase
from course_forge.infrastructure.filesystem import (
    FileSystemContentTreeRepository,
    FileSystemMarkdownLoader,
    FileSystemOutputWriter,
)
from course_forge.infrastructure.markdown import MistuneMarkdownRenderer
from course_forge.infrastructure.templates import JinjaHTMLTemplateRenderer


class DependencyContainer:
    def __init__(self, output_path: str, template_dir: str | None = None):
        self._repo = FileSystemContentTreeRepository()
        self._loader = FileSystemMarkdownLoader()
        self._markdown_renderer = MistuneMarkdownRenderer()
        self._html_renderer = JinjaHTMLTemplateRenderer(template_dir=template_dir)
        self._writer = FileSystemOutputWriter(output_path)

        self._pre_processors: list[Processor] = [
            DigitalCircuitProcessor(),
            ASTProcessor(),
        ]
        self._post_processors: list[Processor] = [HTMLMinifyProcessor()]

        self._build_use_case = BuildSiteUseCase(
            self._repo,
            self._loader,
            self._markdown_renderer,
            self._html_renderer,
            self._writer,
        )

    @property
    def build_use_case(self) -> BuildSiteUseCase:
        return self._build_use_case

    @property
    def pre_processors(self) -> list[Processor]:
        return self._pre_processors

    @property
    def post_processors(self) -> list[Processor]:
        return self._post_processors


def build(content_path: str, output_path: str, template_dir: str | None = None) -> None:
    print(f'Starting site build from content: "{content_path}"...')
    container = DependencyContainer(output_path, template_dir=template_dir)

    print("Processing content and applying pre-processors...")
    container.build_use_case.execute(
        content_path,
        pre_processors=container.pre_processors,
        post_processors=container.post_processors,
        template_dir=template_dir,
    )
    print(f'Success! Site generated at: "{output_path}"')
