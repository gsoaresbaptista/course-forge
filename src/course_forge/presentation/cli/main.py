from course_forge.application.processors import DigitalCircuitProcessor, Processor
from course_forge.application.use_cases.build_site import BuildSiteUseCase
from course_forge.infrastructure.filesystem import (
    FileSystemContentTreeRepository,
    FileSystemMarkdownLoader,
    FileSystemOutputWriter,
)
from course_forge.infrastructure.markdown import MistuneMarkdownRenderer


def main() -> None:
    print("Hello from course-forge CLI!")
    output_path = "/home/gabriel/Documents/faesa/content"

    repo = FileSystemContentTreeRepository()
    loader = FileSystemMarkdownLoader()
    renderer = MistuneMarkdownRenderer()
    writer = FileSystemOutputWriter("/home/gabriel/Documents/site")

    pre_processors: list[Processor] = [DigitalCircuitProcessor()]
    post_processors: list[Processor] = []

    use_case = BuildSiteUseCase(repo, loader, renderer, writer)
    use_case.execute(
        output_path, pre_processors=pre_processors, post_processors=post_processors
    )
