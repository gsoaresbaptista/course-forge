import os

from livereload import Server  # type: ignore

from .build import build


def watch(content_path: str, output_path: str):
    build(content_path, output_path)

    server = Server()

    for root, _, files in os.walk(content_path):
        for file in files:
            if file.endswith(".md"):
                full_path = os.path.join(root, file)
                server.watch(full_path, lambda: build(content_path, output_path))  # type: ignore

    server.serve(  # type: ignore
        root=output_path,
        port=8001,
        host="localhost",
        open_url_delay=0,
        restart_delay=0,
        default_filename="index.html",
    )
