from course_forge.application.processors import (
    ASTProcessor,
    # DigitalCircuitProcessor,
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


def build(content_path: str, output_path: str) -> None:
    print(f'Starting site build from content: "{content_path}"...')
    repo = FileSystemContentTreeRepository()
    loader = FileSystemMarkdownLoader()
    renderer = MistuneMarkdownRenderer()
    writer = FileSystemOutputWriter(output_path)

    # pre_processors: list[Processor] = [DigitalCircuitProcessor()]
    pre_processors: list[Processor] = [ASTProcessor()]
    post_processors: list[Processor] = [HTMLMinifyProcessor()]

    print("Processing content and applying pre-processors...")
    use_case = BuildSiteUseCase(repo, loader, renderer, writer)
    use_case.execute(
        content_path, pre_processors=pre_processors, post_processors=post_processors
    )
    print(f'Success! Site generated at: "{output_path}"')
