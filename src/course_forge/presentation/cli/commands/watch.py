import os

from livereload import Server  # type: ignore

from course_forge.config import Config

from .build import build


def watch(content_path: str, output_path: str, template_dir: str | None = None):
    build(content_path, output_path, template_dir=template_dir)

    server = Server()

    for root, _, files in os.walk(content_path):
        for file in files:
            if file.endswith(".md"):
                full_path = os.path.join(root, file)
                server.watch(  # type: ignore
                    full_path,
                    lambda: build(content_path, output_path, template_dir=template_dir),
                )

    server.serve(  # type: ignore
        root=output_path,
        port=Config.watch_port,
        host="localhost",
        default_filename="index.html",
    )
